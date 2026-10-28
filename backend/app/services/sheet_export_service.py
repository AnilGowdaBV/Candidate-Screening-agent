"""Service to export screened candidates to Google Sheets in ascending order."""

import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import select, func
from app.database.session import get_sessionmaker_for_tech
from app.models.candidate import Candidate
from app.models.screening_result import ScreeningResult
from app.models.screening_run import ScreeningRun
from playwright.async_api import async_playwright
from app.core.logging import get_logger

logger = get_logger("sheet_export_service")

TECH_SHEET_MAP = {
    "javascript": "https://docs.google.com/spreadsheets/d/1dYA8imxWunBDnd05V1Sjuk2_B9tVgFXXSg0ff7yqiJI/edit?gid=0#gid=0",
    "golang": "https://docs.google.com/spreadsheets/d/14zM1ftrQp-L4ntK2YViWvf4AofG1PhfScKqcVYLcEoQ/edit?gid=0#gid=0",
    "java": "https://docs.google.com/spreadsheets/d/1WuolRAWx42Xhaw9kQWsmFJOH-ZlokiRC4t4Ha_Z1VUs/edit?gid=0#gid=0",
    "frontend": "https://docs.google.com/spreadsheets/d/1p4XpHbxkTxGzg25hOsFI5elqOeEE7RkNQIF4LIqKdHA/edit?gid=0#gid=0",
    "qa_automation": "https://docs.google.com/spreadsheets/d/1LqVNQb2yPVHytUkNsiiEFZ3wjjjHU_tTa6y3K2R93v0/edit?gid=0#gid=0",
    "qa": "https://docs.google.com/spreadsheets/d/1LqVNQb2yPVHytUkNsiiEFZ3wjjjHU_tTa6y3K2R93v0/edit?gid=0#gid=0",
    "python": "https://docs.google.com/spreadsheets/d/1UdJWZG1tcvuo_TAH61fVe58GeEf6eCjiVoZYXAmbkgI/edit?gid=0#gid=0",
    "typescript": "https://docs.google.com/spreadsheets/d/1dYA8imxWunBDnd05V1Sjuk2_B9tVgFXXSg0ff7yqiJI/edit?gid=0#gid=0",
}

DEFAULT_SHEET_URL = TECH_SHEET_MAP["golang"]

def parse_coding_profiles(coding_profiles_raw: Optional[str]) -> Dict[str, str]:
    res = {"leetcode": "—", "hackerrank": "—", "other": "—"}
    if not coding_profiles_raw:
        return res
    parts = coding_profiles_raw.split(" | ")
    other_list = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ": " in part:
            platform, url = part.split(": ", 1)
            plat_lower = platform.strip().lower()
            url = url.strip()
            if "leetcode" in plat_lower:
                res["leetcode"] = url
            elif "hackerrank" in plat_lower:
                res["hackerrank"] = url
            else:
                other_list.append(f"{platform}: {url}")
        else:
            plat_lower = part.lower()
            if "leetcode" in plat_lower:
                res["leetcode"] = "LeetCode"
            elif "hackerrank" in plat_lower:
                res["hackerrank"] = "HackerRank"
            else:
                other_list.append(part)
    if other_list:
        res["other"] = " | ".join(other_list)
    return res


def _build_tsv_for_rows(rows, tech_name: str) -> str:
    headers = [
        "Candidate Name",
        "Instahyre Profile URL",
        "Git URL",
        "Current Salary",
        "Location",
        "Experience",
        f"{tech_name.capitalize()} Status",
        "Languages Found",
        "GitScore",
        "LeetCode",
        "HackerRank",
        "Other Coding Profiles",
    ]
    lines = ["\t".join(headers)]
    for cand, res in rows:
        name = (cand.name or "").replace("\t", " ").strip()
        prof = (cand.instahyre_profile_url or "").replace("\t", " ").strip()
        gh = (cand.github_url or "").replace("\t", " ").strip()
        sal = (cand.current_salary or "").replace("\t", " ").strip()
        loc = (cand.location or "").replace("\t", " ").strip()
        exp = (cand.experience or "").replace("\t", " ").strip()
        status = (res.go_status if res else "DETECTED").replace("\t", " ").strip()

        langs_found = (getattr(cand, "languages_found", None) or (getattr(res, "languages_found", None) if res else "") or "").strip()
        if not langs_found:
            if not gh:
                langs_found = "No GitHub found"
            elif tech_name.lower() in ("qa_automation", "qa"):
                if res and "NOT_DETECTED" in res.go_status:
                    langs_found = "QA_Automation not found"
                elif res and "DETECTED" in res.go_status:
                    langs_found = "Playwright, TypeScript, JavaScript"
                else:
                    langs_found = "QA_Automation not found"
            elif res and "DETECTED" in res.go_status:
                langs_found = tech_name.capitalize()
            else:
                langs_found = f"{tech_name.capitalize()} not found"

        langs_found = langs_found.replace("\t", " ").strip()
        git_score_str = f"{cand.gitroll_rating:.2f}" if cand.gitroll_rating else ""
        cp = parse_coding_profiles(cand.coding_profiles)
        lines.append(
            f"{name}\t{prof}\t{gh}\t{sal}\t{loc}\t{exp}\t{status}\t{langs_found}\t{git_score_str}\t{cp['leetcode']}\t{cp['hackerrank']}\t{cp['other']}"
        )
    return "\n".join(lines)


def resolve_one_url_one_sheet_target(db) -> Tuple[str, List[int], str]:
    """
    Enforces the "One URL = One Sheet" ideology across all technologies:
    1. Collects all historical runs in chronological order.
    2. Groups runs by normalized search URL:
       - 1st unique URL -> Sheet1
       - 2nd unique URL -> Sheet2
       - N-th unique URL -> SheetN
    3. If a run on the same URL failed or is re-triggered, it reuses the SAME sheet tab!
    4. Returns: (target_tab_name, associated_run_ids, search_url)
    """
    runs = db.execute(select(ScreeningRun).order_by(ScreeningRun.id.asc())).scalars().all()

    distinct_urls: List[str] = []
    run_url_map: Dict[int, str] = {}

    for r in runs:
        url = ""
        if r.configuration_snapshot:
            try:
                cfg = json.loads(r.configuration_snapshot)
                url = (cfg.get("instahyre_search_url") or "").strip()
            except Exception:
                pass
        run_url_map[r.id] = url
        if url and url not in distinct_urls:
            distinct_urls.append(url)

    # Map each distinct URL to Sheet1, Sheet2, etc.
    tab_by_url: Dict[str, str] = {url: f"Sheet{i+1}" for i, url in enumerate(distinct_urls)}

    # Identify latest run that has screened candidates
    latest_run_with_results = db.execute(select(func.max(ScreeningResult.run_id))).scalar()
    target_run_id = latest_run_with_results if latest_run_with_results else (runs[-1].id if runs else 1)

    target_url = run_url_map.get(target_run_id, "")
    target_tab = tab_by_url.get(target_url, "Sheet1")

    # Associated runs are all runs that share this exact search URL
    associated_run_ids = [r_id for r_id, u in run_url_map.items() if u == target_url]
    if not associated_run_ids:
        associated_run_ids = [target_run_id]

    logger.info(
        "Resolved One-URL-One-Sheet: target_tab='%s', run_ids=%s, url='%s'",
        target_tab, associated_run_ids, target_url[:80] if target_url else "None"
    )
    return target_tab, associated_run_ids, target_url


async def _paste_to_tab(page, tab_name: str, tsv_content: str):
    """Selects or creates tab_name in Google Sheets and pastes TSV cleanly while preserving other tabs."""
    # Dismiss any Google docs dialogs or keyboard modals if present
    cancel_btn = page.locator("button:has-text('Cancel')").first
    if await cancel_btn.count() > 0 and await cancel_btn.is_visible():
        await cancel_btn.click()
        await asyncio.sleep(0.5)
    await page.keyboard.press("Escape")
    await asyncio.sleep(0.5)

    tab = page.locator(f".docs-sheet-tab:has-text('{tab_name}')").first
    if await tab.count() == 0:
        add_btn = page.locator("[aria-label='Add Sheet'], [data-tooltip='Add Sheet'], .docs-sheet-add, div.docs-sheet-add").first
        if await add_btn.count() > 0:
            await add_btn.click()
            await asyncio.sleep(3)
        else:
            await page.click("div.docs-sheet-add, [aria-label*='Add sheet'], [aria-label*='Add Sheet']")
            await asyncio.sleep(3)
    else:
        await tab.click(force=True)
        await asyncio.sleep(2)

    # Double check active tab is not an older preserved tab if tab_name != Sheet1
    if tab_name != "Sheet1":
        active_tab_text = await page.evaluate('''() => {
            const active = document.querySelector('.docs-sheet-active-tab');
            return active ? active.innerText.trim() : '';
        }''')
        if "Sheet1" in active_tab_text and tab_name not in active_tab_text:
            last_tab = page.locator(".docs-sheet-tab").last
            await last_tab.click(force=True)
            await asyncio.sleep(2)

    await page.evaluate("""async (tsv) => {
        await navigator.clipboard.writeText(tsv);
    }""", tsv_content)
    await asyncio.sleep(0.5)

    await page.keyboard.press("Control+a")
    await asyncio.sleep(0.5)
    await page.keyboard.press("Delete")
    await asyncio.sleep(1)

    await page.keyboard.press("Control+Home")
    await asyncio.sleep(0.5)
    await page.keyboard.press("Control+v")
    await asyncio.sleep(5.0)


async def export_candidates_to_google_sheet(
    technology: str = "golang",
    sheet_url: Optional[str] = None
) -> Dict[str, Any]:
    """Export screened candidates to Google Sheet enforcing 'One URL = One Sheet' across all domains."""
    tech = technology.lower() if technology else "golang"
    target_sheet = sheet_url.strip() if sheet_url and sheet_url.strip() else TECH_SHEET_MAP.get(tech, DEFAULT_SHEET_URL)
    
    SessionLocal = get_sessionmaker_for_tech(tech)
    db = SessionLocal()

    try:
        # Resolve target tab and associated runs using the "One URL = One Sheet" ideology
        target_tab, associated_run_ids, search_url = resolve_one_url_one_sheet_target(db)

        # Deduplicate candidate results if same candidate was seen across retries of this URL
        res_subquery = (
            select(func.max(ScreeningResult.id))
            .where(ScreeningResult.run_id.in_(associated_run_ids))
            .group_by(ScreeningResult.candidate_id)
        )
        stmt = (
            select(Candidate, ScreeningResult)
            .join(ScreeningResult, ScreeningResult.candidate_id == Candidate.id)
            .where(
                ScreeningResult.id.in_(res_subquery),
                ScreeningResult.go_status.like('%_DETECTED'),
                ~ScreeningResult.go_status.like('%NOT_DETECTED%')
            )
            .order_by(Candidate.id.asc())
        )
        rows = db.execute(stmt).all()
        total_exported = len(rows)
        logger.info(
            "Exporting %d candidates for %s to '%s' (Search URL: %s)",
            total_exported, tech.capitalize(), target_tab, search_url[:80] if search_url else "Default"
        )

        tsv_data = _build_tsv_for_rows(rows, tech)

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir='data/browser_profile',
                headless=True,
                permissions=["clipboard-read", "clipboard-write"],
                viewport={"width": 1600, "height": 950},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()
            await page.goto(target_sheet, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(5)

            # Paste cleanly into the dedicated tab for this search URL
            await _paste_to_tab(page, target_tab, tsv_data)

            screenshot_path = f"backend/scratch/gsheet_exported_{tech}.png"
            await page.screenshot(path=screenshot_path)
            await browser.close()

        return {
            "success": True,
            "count": total_exported,
            "target_tab": target_tab,
            "sheet_url": target_sheet,
            "screenshot": screenshot_path,
            "message": f"Successfully exported {total_exported} {tech.capitalize()} candidates to {target_tab}. All other sheets preserved.",
        }
    except Exception as e:
        logger.error("Failed to export to Google Sheet: %s", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Export failed: {str(e)}",
        }
    finally:
        db.close()


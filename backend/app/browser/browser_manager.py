"""Playwright browser automation module for Instahyre session and profile inspection."""

import asyncio
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from app.core.config import get_settings
from app.core.logging import get_logger
from app.browser.selectors import (
    INSTAHYRE_BASE_URL,
    INSTAHYRE_LOGIN_URL,
    AUTH_SELECTORS,
    SEARCH_SELECTORS,
    PROFILE_SELECTORS,
)

logger = get_logger("browser_manager")

INVALID_GH_HANDLES = {
    "your-github-handle", "your_github_handle", "your-handle", "your_handle",
    "your-github", "your_github", "yourusername", "your-username",
    "username", "user-name", "yourname", "your-name", "example", "none",
    "null", "undefined", "about", "features", "pricing", "contact", "security",
    "site", "blog", "portfolio", "settings", "notifications", "explore",
    "topics", "trending", "collections", "events", "stars", "sponsors",
    "pulls", "issues", "marketplace", "login", "join", "enterprise", "orgs",
    "search", "readme", "gist", "dashboard"
}

TRAILING_PUNCTUATION = ".,:;/)]}>'\"`\\"

def clean_and_validate_github(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9][a-zA-Z0-9_\-\.]*)", url, re.IGNORECASE)
    if not match:
        git_match = re.search(r"git@github\.com:([a-zA-Z0-9][a-zA-Z0-9_\-\.]*)", url, re.IGNORECASE)
        if git_match:
            match = git_match
        else:
            return None
    raw_handle = match.group(1).strip()
    handle = raw_handle.rstrip(TRAILING_PUNCTUATION)
    if "?" in handle:
        handle = handle.split("?")[0].rstrip(TRAILING_PUNCTUATION)
    if "/" in handle:
        handle = handle.split("/")[0].rstrip(TRAILING_PUNCTUATION)
    handle_lower = handle.lower()
    if handle_lower in INVALID_GH_HANDLES or len(handle) < 2:
        return None
    return f"https://github.com/{handle}"



class PlaywrightBrowserManager:
    """Manages persistent browser session, Instahyre authentication, and profile extraction."""

    _rate_limit_until: Optional[datetime] = datetime.now(timezone.utc) + timedelta(seconds=49800)

    def __init__(self, user_data_dir: Optional[str] = None, headless: Optional[bool] = None):
        settings = get_settings()
        self.settings = settings
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.user_data_dir = user_data_dir or str(base_dir / "data" / "browser_profile")
        self.headless = headless if headless is not None else settings.HEADLESS_BROWSER
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def initialize(self) -> None:
        """Launch persistent browser context preserving cookies and session state."""
        if self.context:
            return

        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Initializing Playwright with persistent profile at: %s", self.user_data_dir)

        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def close(self) -> None:
        """Safely close context and Playwright instance."""
        if self.context:
            await self.context.close()
            self.context = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        self.page = None
        logger.info("Browser session closed cleanly")

    async def check_authenticated(self) -> bool:
        """Check whether the active session is currently logged into Instahyre."""
        if not self.page:
            await self.initialize()

        assert self.page is not None
        try:
            await self.page.goto(f"{INSTAHYRE_BASE_URL}/employer/", wait_until="domcontentloaded", timeout=20000)
        except Exception:
            pass

        # Give Cloudflare verification up to 6 seconds to complete if encountered
        for _ in range(6):
            title = (await self.page.title()).lower()
            if "just a moment" not in title and "security verification" not in title:
                break
            await asyncio.sleep(1)

        # Check for login redirection
        current_url = self.page.url.lower()
        if "/login" in current_url:
            return False

        # If we are on employer path, we are authenticated
        if "/employer" in current_url:
            return True

        # Check for logged-in indicators
        try:
            indicator = await self.page.query_selector(AUTH_SELECTORS["logged_in_indicator"])
            return indicator is not None
        except Exception:
            return "/employer" in current_url

    async def attempt_login(self) -> Tuple[bool, str]:
        """
        Attempt automated login using .env credentials.
        Returns (success: bool, status_message: str).
        """
        if not self.page:
            await self.initialize()

        assert self.page is not None
        if not self.settings.is_instahyre_configured:
            return False, "Instahyre credentials not configured in .env; manual login required."

        email = self.settings.INSTAHYRE_EMAIL
        password = self.settings.INSTAHYRE_PASSWORD.get_secret_value() if self.settings.INSTAHYRE_PASSWORD else ""

        logger.info("Navigating to Instahyre login page...")
        await self.page.goto(INSTAHYRE_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1.5)

        # Check for CAPTCHA/bot protection before touching inputs
        captcha = await self.page.query_selector(AUTH_SELECTORS["captcha_indicator"])
        if captcha:
            logger.warning("Bot protection / CAPTCHA detected on login page")
            return False, "CAPTCHA detected on login page. Manual intervention required."

        # Fill credentials
        try:
            email_field = await self.page.wait_for_selector(AUTH_SELECTORS["email_input"], timeout=5000)
            if email_field:
                await email_field.fill(email or "")

            pwd_field = await self.page.wait_for_selector(AUTH_SELECTORS["password_input"], timeout=5000)
            if pwd_field:
                await pwd_field.fill(password)

            submit_btn = await self.page.query_selector(AUTH_SELECTORS["submit_button"])
            if submit_btn:
                await submit_btn.click()
            else:
                await self.page.keyboard.press("Enter")

            # Wait for navigation away from login
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            await asyncio.sleep(2)

            if "/login" not in self.page.url.lower():
                logger.info("Automated login succeeded and session saved to profile")
                return True, "Login successful"
            else:
                return False, "Login failed: Credentials submitted but remained on login page"

        except Exception as exc:
            logger.error("Automated login encountered error: %s", exc)
            return False, f"Login error: {str(exc)}"

    async def open_search_url(self, search_url: str) -> Tuple[bool, str]:
        """Navigate to configured search URL and verify search results page."""
        if not self.page:
            await self.initialize()

        assert self.page is not None
        logger.info("Navigating to search URL: %s", search_url)
        try:
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
        except Exception:
            pass

        # Give Cloudflare verification up to 6 seconds to complete if encountered
        for _ in range(6):
            title = (await self.page.title()).lower()
            if "just a moment" not in title and "security verification" not in title:
                break
            await asyncio.sleep(1)

        # Verify not bounced back to login
        if "/login" in self.page.url.lower():
            return False, "Redirected to login page. Authentication required."

        await self.ensure_search_job_selected()

        return True, "Search page loaded successfully"

    async def ensure_search_job_selected(self) -> bool:
        """Ensure an active job URI string is selected on search page so note addition never aborts."""
        if not self.page:
            return False
        try:
            job_uri = await self.page.evaluate("""() => {
                const sel = document.querySelector('.job-selection selectize, .job-selection .selectized, [ng-model*="job.activeJob"]');
                let uri = null;
                if (sel && sel.selectize) {
                    const opts = Object.keys(sel.selectize.options);
                    uri = opts.find(k => k && k.startsWith('/api/v1/job_form/employer_job/'));
                    if (uri) {
                        sel.selectize.setValue(uri);
                    }
                }
                const s = window.angular ? angular.element(document.querySelector('#notes-tab, .search-page, .candidate-profile, [ng-controller]') || document.body).scope() : null;
                if (s) {
                    if (!uri) {
                        const choices = s.ALLOWED_JOB_CHOICES || s.JOB_CHOICE_OPTIONS || [];
                        const match = choices.find(j => j && (j.uri || j.resource_uri));
                        if (match) uri = match.uri || match.resource_uri;
                    }
                    if (!uri) uri = '/api/v1/job_form/employer_job/17001';
                    if (!s.job) s.job = {};
                    s.job.activeJob = uri;
                    try { s.$apply(); } catch(e) {}
                }
                return uri;
            }""")
            if job_uri:
                logger.info("Search job URI selected: %s", job_uri)
                return True
            return False
        except Exception as exc:
            logger.warning("Could not pre-select search job: %s", exc)
            return False

    async def extract_candidate_cards(self) -> List[Dict[str, Any]]:
        """
        Extract candidate links and names visible in current search results.
        Returns list of {'url': str, 'name': str, 'external_id': Optional[str], 'row_index': int}.
        """
        assert self.page is not None
        candidates = []

        # Wait for candidate rows to render
        try:
            await self.page.wait_for_selector(SEARCH_SELECTORS["candidate_cards"], timeout=10000)
        except Exception:
            await asyncio.sleep(3)

        rows = await self.page.query_selector_all(SEARCH_SELECTORS["candidate_cards"])
        seen_ids = set()

        for idx, row in enumerate(rows):
            cand_id = await row.get_attribute("id")
            if cand_id and cand_id in seen_ids:
                continue
            if cand_id:
                seen_ids.add(cand_id)

            # Extract name
            name = f"Candidate #{idx+1}"
            name_el = await row.query_selector(SEARCH_SELECTORS["candidate_name"])
            if name_el:
                name_text = (await name_el.inner_text()).strip()
                if name_text:
                    name = name_text

            full_url = f"{INSTAHYRE_BASE_URL}/candidate/{cand_id}/" if cand_id else f"{self.page.url}#candidate-{idx+1}"

            # Extract current salary from card (e.g. "₹ Current salary: 6.0 lpa")
            current_salary = None
            location = None
            experience = None
            try:
                row_text = await row.inner_text()
                sal_match = re.search(r"(?:Current\s*salary|Salary|CTC)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([\d\.]+\s*(?:lpa|LPA|L|lakhs?))", row_text, re.IGNORECASE)
                if sal_match:
                    val = sal_match.group(1).strip().upper()
                    if not val.startswith("₹"):
                        val = f"₹ {val}"
                    current_salary = val

                loc_el = await row.query_selector(".location-info-field [ng-hide*='editing_location'], .location-info-field span:not(.info-label)")
                if loc_el:
                    loc_txt = (await loc_el.inner_text()).replace("Location:", "").strip()
                    if loc_txt:
                        location = loc_txt
                if not location:
                    loc_match = re.search(r"Location\s*:\s*([^\n\r\t]+?)(?:\s{2,}|Experience:|Notice\s*period:|Current\s*salary:|Skills:|$)", row_text, re.IGNORECASE)
                    if loc_match:
                        location = loc_match.group(1).strip()

                exp_el = await row.query_selector("[ng-hide*='editing_experience']")
                if exp_el:
                    exp_txt = (await exp_el.inner_text()).replace("Experience:", "").strip()
                    if exp_txt:
                        experience = exp_txt
                if not experience:
                    exp_match = re.search(r"Experience\s*:\s*([0-9.]+\s*(?:years?|yrs?|months?)?)", row_text, re.IGNORECASE)
                    if exp_match:
                        experience = re.sub(r"\s+", " ", exp_match.group(1)).strip()
            except Exception:
                pass

            # Check if GitHub link or social links are visible directly on candidate card
            card_gh = None
            try:
                gh_el = await row.query_selector('a[href*="github.com"], a[ng-href*="github.com"], a[title*="github" i], a[data-original-title*="github" i]')
                if gh_el:
                    h = (await gh_el.get_attribute("ng-href")) or (await gh_el.get_attribute("href")) or (await gh_el.get_attribute("title"))
                    card_gh = clean_and_validate_github(h)
                if not card_gh:
                    row_scope_gh = await self.page.evaluate("""(el) => {
                        try {
                            if (window.angular) {
                                const sc = angular.element(el).scope();
                                const cand = sc ? (sc.cand || sc.candidate || sc.c) : null;
                                if (cand && cand.social_accounts) {
                                    return cand.social_accounts.github || cand.social_accounts.fc_github_url || null;
                                }
                                if (cand && cand.fc_github_url) return cand.fc_github_url;
                                if (cand && cand.github_url) return cand.github_url;
                            }
                        } catch(e) {}
                        return null;
                    }""", row)
                    if row_scope_gh:
                        card_gh = clean_and_validate_github(row_scope_gh)
            except Exception:
                pass

            candidates.append({
                "url": full_url,
                "name": name,
                "external_id": cand_id,
                "row_index": idx,
                "github_url": card_gh,
                "current_salary": current_salary,
                "location": location,
                "experience": experience,
            })

        logger.info("Discovered %d candidate profiles on search page", len(candidates))
        return candidates

    async def get_current_page_number(self) -> int:
        """Return the current active page number from pagination."""
        if not self.page:
            return 1
        try:
            active_text = await self.page.evaluate("""() => {
                const active = document.querySelector('ul.pagination li.active, .pagination li.active');
                return active ? active.innerText.trim() : '1';
            }""")
            return int(active_text) if active_text.isdigit() else 1
        except Exception:
            return 1

    async def go_to_next_page(self) -> bool:
        """Click Next button or call nextPage in pagination to load the next set of 30 candidates."""
        if not self.page:
            return False
        try:
            prev_page = await self.get_current_page_number()
            called_ng = await self.page.evaluate("""() => {
                const pEls = document.querySelectorAll('.pagination, ul.pagination');
                for (const el of pEls) {
                    const s = window.angular ? angular.element(el).scope() : null;
                    if (s && typeof s.nextPage === 'function') {
                        s.nextPage();
                        try { s.$apply(); } catch(e) {}
                        return true;
                    }
                }
                return false;
            }""")
            if not called_ng:
                next_btn = self.page.locator('li[ng-click*="nextPage"], li:has-text("Next")').first
                if await next_btn.count() > 0:
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click(force=True)

            await asyncio.sleep(4)
            await self.ensure_search_job_selected()
            new_page = await self.get_current_page_number()
            logger.info("Paginated from search page %d to page %d", prev_page, new_page)
            if new_page > prev_page:
                return True

            # URL offset fallback if Angular/DOM button click didn't advance
            curr_url = self.page.url
            if "offset=" in curr_url:
                curr_offset_match = re.search(r'offset=(\d+)', curr_url)
                curr_offset = int(curr_offset_match.group(1)) if curr_offset_match else 0
                next_offset = curr_offset + 30
                next_url = re.sub(r'offset=\d+', f'offset={next_offset}', curr_url)
            else:
                sep = '&' if '?' in curr_url else '?'
                next_url = f"{curr_url}{sep}offset={prev_page * 30}"
                
            logger.info("Advancing pagination via URL offset: %s", next_url)
            await self.page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)
            await self.ensure_search_job_selected()
            return True
        except Exception as exc:
            logger.warning("Error navigating to next page: %s", exc)
            return False

    async def go_to_page(self, target_page: int) -> bool:
        """Navigate directly or iteratively to a specific pagination page number."""
        if not self.page or target_page < 1:
            return False
        try:
            curr = await self.get_current_page_number()
            if curr == target_page:
                return True
            logger.info("Advancing from page %d to target page %d", curr, target_page)
            # Try direct angular nthPage first
            try:
                await self.page.evaluate(f"""(pg) => {{
                    const pEls = document.querySelectorAll('.pagination, ul.pagination');
                    for (const el of pEls) {{
                        const s = window.angular ? angular.element(el).scope() : null;
                        if (s && typeof s.nthPage === 'function') {{
                            s.nthPage(pg);
                            try {{ s.$apply(); }} catch(e) {{}}
                            return true;
                        }}
                    }}
                    return false;
                }}""", target_page)
                await asyncio.sleep(4)
                await self.ensure_search_job_selected()
                curr = await self.get_current_page_number()
                if curr == target_page:
                    logger.info("Successfully jumped directly to page %d via Angular nthPage", target_page)
                    return True
            except Exception as e_nth:
                logger.warning("Direct nthPage attempt note: %s", e_nth)

            while curr < target_page:
                ok = await self.go_to_next_page()
                if not ok:
                    break
                curr = await self.get_current_page_number()
            return curr == target_page
        except Exception as exc:
            logger.warning("Error navigating to page %d: %s", target_page, exc)
            return False


    async def inspect_candidate_profile(self, profile_url: str, card_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Open a candidate profile drawer and locate their GitHub profile URL, coding profiles, and metadata.
        Thoroughly searches Angular scopes, top social icons, rendered resume HTML, iframes, and fallback rows.
        """
        assert self.page is not None
        row_idx = card_info.get("row_index") if card_info else None
        ext_id = card_info.get("external_id") if card_info else None
        cand_name = card_info.get("name") if card_info else "Candidate"
        card_cached_gh = card_info.get("github_url") if card_info else None

        logger.info("Inspecting candidate profile: %s (%s)", cand_name, profile_url)

        # Locate candidate row on current search page
        row = None
        if ext_id:
            row = await self.page.query_selector(f"[id='{ext_id}']")
        if not row and row_idx is not None:
            rows = await self.page.query_selector_all(SEARCH_SELECTORS["candidate_cards"])
            if row_idx < len(rows):
                row = rows[row_idx]

        # Click View profile button to open drawer if row found
        modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first
        if row:
            view_btn = await row.query_selector('.button-download-resume, a:has-text("View profile"), button:has-text("View profile"), [ng-click*="viewResume"], [ng-click*="showResume"], [ng-click*="openResume"], .view-profile')
            if view_btn:
                await view_btn.scroll_into_view_if_needed()
                await view_btn.click(force=True)
                await asyncio.sleep(1.5)
            # Fallback to candidate name click if modal not open
            if await modal.count() == 0 or not await modal.is_visible():
                name_link = await row.query_selector(SEARCH_SELECTORS["candidate_name"])
                if name_link:
                    await name_link.click(force=True)
                    await asyncio.sleep(1.5)
        elif profile_url and profile_url != self.page.url:
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

        # Wait up to 4.5s for modal and resume content or Angular scope to populate
        for _ in range(9):
            loaded = await self.page.evaluate("""() => {
                const m = document.querySelector('#resume-modal-block, .application-modal-wrap');
                if (!m) return false;
                if (window.angular) {
                    try {
                        const sc = angular.element(m).scope();
                        if (sc && (sc.candidate || sc.resumeCandidate || sc.resume_candidate)) return true;
                    } catch(e) {}
                }
                const r = document.querySelector('#resume-html-container, #resume-tab, .resume-container, .candidate-links');
                if (r && (r.innerText.trim().length > 30 || r.querySelectorAll('a').length > 0)) return true;
                return m.innerText.trim().length > 80;
            }""")
            if loaded:
                break
            await asyncio.sleep(0.5)

        # Extract candidate real name if available in drawer / Angular scope
        name = cand_name
        modal = await self.page.query_selector("#resume-modal-block, .application-modal-wrap")
        try:
            extracted_name = await self.page.evaluate("""() => {
                try {
                    const m = document.querySelector('#resume-modal-block, .application-modal-wrap');
                    if (m && window.angular) {
                        const sc = angular.element(m).scope();
                        const cand = sc.candidate || sc.resumeCandidate || sc.resume_candidate || sc.resumecandidate;
                        if (cand && cand.user && cand.user.full_name) {
                            return cand.user.full_name.trim();
                        }
                        if (cand && cand.display_name) return cand.display_name.trim();
                    }
                } catch(e) {}
                const el = document.querySelector('#resume-modal-block .candidate-name .readonly-field, #resume-modal-block .name-row .readonly-field, #resume-modal-block #name, #resume-modal-block .candidate-name');
                return el ? el.innerText.trim() : null;
            }""")
            if extracted_name and extracted_name not in ("Software Tester", "Automation QA", "Candidate") and len(extracted_name) > 2:
                name = extracted_name
        except Exception:
            pass

        if (not name or name in ("Software Tester", "Automation QA", "Candidate")) and modal:
            name_el = await modal.query_selector(PROFILE_SELECTORS["name"])
            if name_el:
                name_text = (await name_el.inner_text()).strip()
                if name_text and name_text not in ("Software Tester", "Automation QA", "Candidate"):
                    name = name_text

        # Search for GitHub link across all possible sources
        github_url = None

        # 1. Deep search in Angular Scope (candidate models, social accounts, nested properties)
        try:
            scope_gh = await self.page.evaluate("""() => {
                try {
                    function findGh(obj, depth = 0) {
                        if (!obj || depth > 5) return null;
                        if (typeof obj === 'string') {
                            const lower = obj.toLowerCase();
                            if (lower.includes('github.com')) return obj;
                            return null;
                        }
                        if (Array.isArray(obj)) {
                            for (const item of obj) {
                                const res = findGh(item, depth + 1);
                                if (res) return res;
                            }
                        } else if (typeof obj === 'object') {
                            for (const [k, v] of Object.entries(obj)) {
                                if (k.startsWith('$') || k === 'parent' || k === 'scope' || k === 'element' || k === 'window') continue;
                                const res = findGh(v, depth + 1);
                                if (res) return res;
                            }
                        }
                        return null;
                    }

                    const selectors = ['#resume-modal-block', '.application-modal-wrap', '.candidate-profile', '.candidate-links', '.modal-dialog', 'body'];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && window.angular) {
                            const sc = angular.element(el).scope();
                            if (sc) {
                                const cand = sc.candidate || sc.resumeCandidate || sc.resume_candidate || sc.resumecandidate || sc.cand || sc.candidateData;
                                if (cand) {
                                    if (cand.social_accounts) {
                                        const soc = cand.social_accounts;
                                        if (typeof soc === 'object' && !Array.isArray(soc)) {
                                            if (soc.github) return soc.github;
                                            if (soc.fc_github_url) return soc.fc_github_url;
                                        } else if (Array.isArray(soc)) {
                                            for (const s of soc) {
                                                const u = s.url || s.link || s.profile_url || s.github || '';
                                                if (u && u.toLowerCase().includes('github.com')) return u;
                                            }
                                        }
                                    }
                                    if (cand.fc_github_url) return cand.fc_github_url;
                                    if (cand.github_url) return cand.github_url;
                                    if (cand.github) return cand.github;
                                    if (cand.social_links) {
                                        for (const sl of Object.values(cand.social_links)) {
                                            if (typeof sl === 'string' && sl.toLowerCase().includes('github.com')) return sl;
                                        }
                                    }
                                    const deepFound = findGh(cand);
                                    if (deepFound) return deepFound;
                                }
                            }
                        }
                    }
                } catch(e) {}
                return null;
            }""")
            if scope_gh:
                github_url = clean_and_validate_github(scope_gh)
        except Exception:
            pass

        # 2. Check top social icons and modal DOM elements
        if not github_url:
            try:
                dom_gh = await self.page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll(
                        '.candidate-links a, a[ng-href*="github"], a[href*="github.com"], ' +
                        'a[title*="github" i], a[data-original-title*="github" i], a[aria-label*="github" i], ' +
                        '.candidate-social-links a, .icons-row a, .social-icons a, .social-links a, ' +
                        '#resume-modal-block a, .application-modal-wrap a'
                    ));
                    for (const a of links) {
                        const h = a.getAttribute('ng-href') || a.href || a.getAttribute('href') || a.getAttribute('data-url') || a.getAttribute('data-link') || a.getAttribute('title') || a.innerText || '';
                        if (h && h.toLowerCase().includes('github.com')) return h;
                    }
                    return null;
                }""")
                if dom_gh:
                    github_url = clean_and_validate_github(dom_gh)
            except Exception:
                pass

        # 3. Check rendered resume container and text (#resume-html-container, #resume-tab, etc.)
        if not github_url:
            try:
                resume_data = await self.page.evaluate("""() => {
                    const rContainer = document.querySelector(
                        '#resume-html-container, #resume-tab, .resume-container, .resume-body, .resume-view, .resume-viewer, ' +
                        '[ng-bind-html*="resume"], .pdf-viewer, .text-layer, #resume-modal-block, .application-modal-wrap'
                    );
                    if (!rContainer) return { text: '', links: [] };
                    const links = Array.from(rContainer.querySelectorAll('a'))
                        .map(a => a.href || a.getAttribute('href') || a.getAttribute('ng-href') || a.innerText || '')
                        .filter(h => h && h.toLowerCase().includes('github.com'));
                    return { text: rContainer.innerText || '', links: links };
                }""")
                for l in resume_data.get("links", []):
                    valid_url = clean_and_validate_github(l)
                    if valid_url:
                        github_url = valid_url
                        break
                if not github_url and resume_data.get("text"):
                    gh_matches = re.findall(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_\-\.\/]+", resume_data["text"], re.IGNORECASE)
                    for m in gh_matches:
                        valid_url = clean_and_validate_github(m)
                        if valid_url:
                            github_url = valid_url
                            break
            except Exception:
                pass

        # 4. Check Playwright frames / iframes (resumes embedded inside iframe or document viewer)
        if not github_url:
            try:
                for frame in self.page.frames:
                    if frame == self.page.main_frame:
                        continue
                    try:
                        frame_data = await frame.evaluate("""() => {
                            const links = Array.from(document.querySelectorAll('a'))
                                .map(a => a.href || a.getAttribute('href') || a.getAttribute('ng-href') || a.innerText || '')
                                .filter(h => h && h.toLowerCase().includes('github.com'));
                            return {
                                links: links,
                                text: document.body ? document.body.innerText : ''
                            };
                        }""")
                        for l in frame_data.get("links", []):
                            val = clean_and_validate_github(l)
                            if val:
                                github_url = val
                                break
                        if not github_url and frame_data.get("text") and "github.com" in frame_data["text"].lower():
                            gh_matches = re.findall(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_\-\.\/]+", frame_data["text"], re.IGNORECASE)
                            for m in gh_matches:
                                val = clean_and_validate_github(m)
                                if val:
                                    github_url = val
                                    break
                        if github_url:
                            break
                    except Exception:
                        pass
            except Exception:
                pass

        # 5. Check entire modal innerText fallback
        if not github_url:
            try:
                modal_text = await self.page.evaluate("""() => {
                    const m = document.querySelector('#resume-modal-block, .application-modal-wrap');
                    return m ? m.innerText : (document.body ? document.body.innerText : '');
                }""")
                gh_matches = re.findall(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_\-\.\/]+", modal_text, re.IGNORECASE)
                for m in gh_matches:
                    valid_url = clean_and_validate_github(m)
                    if valid_url:
                        github_url = valid_url
                        break
            except Exception:
                pass

        # 6. Fallback to row on search page or card cache
        if not github_url and card_cached_gh:
            github_url = clean_and_validate_github(card_cached_gh)

        if not github_url and row:
            row_gh_links = await row.query_selector_all('a[href*="github.com"], a[ng-href*="github.com"], a[title*="github" i], a[data-original-title*="github" i]')
            for rgl in row_gh_links:
                href = (await rgl.get_attribute("ng-href")) or (await rgl.get_attribute("href")) or (await rgl.get_attribute("title"))
                valid_url = clean_and_validate_github(href)
                if valid_url:
                    github_url = valid_url
                    break

        # Extract current salary
        current_salary = card_info.get("current_salary") if card_info else None
        if not current_salary and modal:
            try:
                m_text = await modal.inner_text()
                sal_match = re.search(r"(?:Current\s*salary|Salary|CTC)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([\d\.]+\s*(?:lpa|LPA|L|lakhs?))", m_text, re.IGNORECASE)
                if sal_match:
                    val = sal_match.group(1).strip().upper()
                    if not val.startswith("₹"):
                        val = f"₹ {val}"
                    current_salary = val
            except Exception:
                pass

        # Extract location
        location = card_info.get("location") if card_info else None
        if not location and modal:
            try:
                loc_el = await modal.query_selector(".location-info-field [ng-hide*='editing_location'], .location-info-field span:not(.info-label)")
                if loc_el:
                    loc_txt = (await loc_el.inner_text()).replace("Location:", "").strip()
                    if loc_txt:
                        location = loc_txt
                if not location:
                    m_text = await modal.inner_text()
                    loc_match = re.search(r"Location\s*:\s*([^\n\r\t<]+?)(?:\s{2,}|Experience:|Notice|Current|<|$)", m_text, re.IGNORECASE)
                    if loc_match:
                        location = loc_match.group(1).strip()
            except Exception:
                pass

        experience = card_info.get("experience") if card_info else None
        if not experience and modal:
            try:
                exp_el = await modal.query_selector("[ng-hide*='editing_experience']")
                if exp_el:
                    exp_txt = (await exp_el.inner_text()).replace("Experience:", "").strip()
                    if exp_txt:
                        experience = exp_txt
                if not experience:
                    m_text = await modal.inner_text()
                    exp_match = re.search(r"Experience\s*:\s*([0-9.]+\s*(?:years?|yrs?|months?)?)", m_text, re.IGNORECASE)
                    if exp_match:
                        experience = re.sub(r"\s+", " ", exp_match.group(1)).strip()
            except Exception:
                pass

        # Check for Coding Platforms across all domains (LeetCode, HackerRank, CodeChef, Codeforces, GeeksforGeeks, ICPC)
        coding_parts = []
        if modal:
            try:
                m_links = await modal.query_selector_all("a")
                hrefs = []
                for l in m_links:
                    h = await l.get_attribute("href")
                    if h:
                        hrefs.append(h.strip())

                modal_text = await modal.inner_text()

                # LeetCode
                lc_link = next((h for h in hrefs if "leetcode.com" in h.lower()), None)
                if not lc_link:
                    m = re.search(r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?([a-zA-Z0-9_\-]+)", modal_text, re.IGNORECASE)
                    if m:
                        lc_link = f"https://leetcode.com/u/{m.group(1).rstrip(TRAILING_PUNCTUATION)}"
                if lc_link:
                    coding_parts.append(f"LeetCode: {lc_link}")
                elif re.search(r"\bleetcode\b", modal_text, re.IGNORECASE):
                    coding_parts.append("LeetCode")

                # HackerRank
                hr_link = next((h for h in hrefs if "hackerrank.com" in h.lower()), None)
                if not hr_link:
                    m = re.search(r"(?:https?://)?(?:www\.)?hackerrank\.com/(?:profile/)?([a-zA-Z0-9_\-]+)", modal_text, re.IGNORECASE)
                    if m:
                        hr_link = f"https://hackerrank.com/{m.group(1).rstrip(TRAILING_PUNCTUATION)}"
                if hr_link:
                    coding_parts.append(f"HackerRank: {hr_link}")
                elif re.search(r"\bhackerrank\b", modal_text, re.IGNORECASE):
                    coding_parts.append("HackerRank")

                # CodeChef
                cc_link = next((h for h in hrefs if "codechef.com" in h.lower()), None)
                if not cc_link:
                    m = re.search(r"(?:https?://)?(?:www\.)?codechef\.com/(?:users/)?([a-zA-Z0-9_\-]+)", modal_text, re.IGNORECASE)
                    if m:
                        cc_link = f"https://codechef.com/users/{m.group(1).rstrip(TRAILING_PUNCTUATION)}"
                if cc_link:
                    coding_parts.append(f"CodeChef: {cc_link}")
                elif re.search(r"\bcodechef\b", modal_text, re.IGNORECASE):
                    coding_parts.append("CodeChef")

                # Codeforces
                cf_link = next((h for h in hrefs if "codeforces.com" in h.lower()), None)
                if not cf_link:
                    m = re.search(r"(?:https?://)?(?:www\.)?codeforces\.com/(?:profile/)?([a-zA-Z0-9_\-]+)", modal_text, re.IGNORECASE)
                    if m:
                        cf_link = f"https://codeforces.com/profile/{m.group(1).rstrip(TRAILING_PUNCTUATION)}"
                if cf_link:
                    coding_parts.append(f"Codeforces: {cf_link}")

                # GeeksforGeeks
                gfg_link = next((h for h in hrefs if "geeksforgeeks.org" in h.lower()), None)
                if not gfg_link:
                    m = re.search(r"(?:https?://)?(?:www\.)?geeksforgeeks\.org/user/([a-zA-Z0-9_\-]+)", modal_text, re.IGNORECASE)
                    if m:
                        gfg_link = f"https://geeksforgeeks.org/user/{m.group(1).rstrip(TRAILING_PUNCTUATION)}"
                if gfg_link:
                    coding_parts.append(f"GeeksforGeeks: {gfg_link}")

                # ICPC
                if re.search(r"\b(?:icpc|acm[\s\-]icpc)\b", modal_text, re.IGNORECASE):
                    coding_parts.append("ICPC")
            except Exception as e:
                logger.warning("Error detecting coding platforms: %s", e)

        coding_profiles = " | ".join(coding_parts) if coding_parts else None

        safe_salary = str(current_salary or "N/A").replace("₹", "Rs.")
        logger.info(
            "Candidate '%s' GitHub discovery: %s (Salary: %s, Location: %s, Exp: %s, Coding: %s)",
            name, github_url or "None", safe_salary, location or "N/A", experience or "N/A", coding_profiles or "None"
        )
        return {
            "name": name,
            "profile_url": profile_url,
            "github_url": github_url,
            "current_salary": current_salary,
            "location": location,
            "experience": experience,
            "coding_profiles": coding_profiles,
        }

    async def get_existing_notes(self) -> List[str]:
        """
        Read all existing note texts for the currently opened candidate profile.
        Strictly read-only; never alters, deletes, or overrides existing recruiter notes.
        """
        if not self.page:
            return []
        notes = []

        try:
            modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first
            if await modal.count() == 0:
                modal = self.page.locator("body").first

            notes_tab = modal.locator('a:has-text("Notes"), [ng-click*="notifyNotes"]').first
            if await notes_tab.count() > 0:
                try:
                    await notes_tab.click(force=True, timeout=3000)
                    await asyncio.sleep(1.2)
                except Exception:
                    pass

            # 1. First read all existing note messages via evaluate from DOM
            try:
                dom_notes = await self.page.evaluate("""() => {
                    const els = document.querySelectorAll('#notes-tab .note-message, #notes-tab .single-note, #notes-tab .message-body, #notes-tab [class*="note-text"], #notes-tab .note-content, #notes-tab .candidate-note');
                    return Array.from(els).map(e => e.innerText.trim()).filter(t => t.length > 0);
                }""")
                if dom_notes and len(dom_notes) > 0:
                    return dom_notes
            except Exception:
                pass

            # 2. Fallback using locators
            note_items = modal.locator(PROFILE_SELECTORS["single_note"])
            count = await note_items.count()
            for i in range(count):
                try:
                    text = (await note_items.nth(i).inner_text()).strip()
                    if text:
                        notes.append(text)
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Error reading existing notes: %s", e)

        return notes

    async def write_note(self, note_text: str, dry_run: bool = True) -> Tuple[str, Optional[str]]:
        """
        Check for duplicate notes and add the screening note to the current candidate's profile.
        GUARANTEE: Strictly preserves all existing recruiter notes!
        Only creates a new note. Never edits, overwrites, or removes any preexisting notes.
        Returns (action_status: str, error_message: Optional[str]).
        Statuses: NOTE_ADDED, NOTE_ALREADY_EXISTS, NOTE_FAILED, SKIPPED.
        """
        # 1. Duplicate check: If our screening note is already in existing notes, skip write.
        existing_notes = await self.get_existing_notes()
        for existing in existing_notes:
            if note_text.strip().lower() in existing.lower():
                logger.info("Exact note '%s' already exists on candidate profile. Skipping write to avoid duplicate.", note_text)
                return "NOTE_ALREADY_EXISTS", None

        # 2. Dry run check
        if dry_run:
            logger.info("[DRY RUN] Would append note: '%s'. Skipped external write.", note_text)
            return "SKIPPED", "Dry run enabled; note write skipped"

        if not self.page:
            return "NOTE_FAILED", "Browser page is not initialized"

        # Check if Instahyre daily note quota is currently active
        now = datetime.now(timezone.utc)
        if PlaywrightBrowserManager._rate_limit_until and now < PlaywrightBrowserManager._rate_limit_until:
            rem = int((PlaywrightBrowserManager._rate_limit_until - now).total_seconds())
            logger.info("Instahyre daily note quota active (%ds remaining). Queuing note '%s'.", rem, note_text)
            return "RATE_LIMITED", f"Instahyre daily note limit active ({rem}s remaining). Note queued."

        rate_limited_info = {"hit": False, "retry_after": None}
        def check_rate_limit(resp):
            if resp.status == 429 and ("note" in resp.url.lower() or "resume_modal" in resp.url.lower()):
                rate_limited_info["hit"] = True
                rate_limited_info["retry_after"] = resp.headers.get("retry-after")
        
        try:
            self.page.on("response", check_rate_limit)
        except Exception:
            pass

        # 3. Scope to active modal or direct candidate page and activate Notes tab
        try:
            modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first
            if await modal.count() == 0:
                if "/candidate/" in self.page.url:
                    modal = self.page.locator("body").first
                else:
                    return "NOTE_FAILED", "Candidate profile modal is not open"

            # Switch to Notes tab inside modal
            notes_tab = modal.locator('a:has-text("Notes"), [ng-click*="notifyNotes"]').first
            if await notes_tab.count() > 0:
                try:
                    await notes_tab.click(force=True, timeout=4000)
                    await asyncio.sleep(1.2)
                except Exception as tab_err:
                    logger.warning("Error clicking notes tab: %s", tab_err)

            # Ensure an active job is selected so Angular's addNote function does not abort
            await self.ensure_search_job_selected()

            # Locate Quill editor inside modal
            editor = modal.locator(PROFILE_SELECTORS["note_editor"]).first
            if await editor.count() == 0:
                add_note_link = modal.locator('a:has-text("add a note"), button:has-text("add a note"), [class*="add-note"]').first
                if await add_note_link.count() > 0:
                    await add_note_link.click(force=True)
                    await asyncio.sleep(1)
                editor = modal.locator(PROFILE_SELECTORS["note_editor"]).first

            if await editor.count() == 0:
                try:
                    await self.page.wait_for_selector(PROFILE_SELECTORS["note_editor"], timeout=3000)
                    editor = modal.locator(PROFILE_SELECTORS["note_editor"]).first
                except Exception:
                    pass

            try:
                if await editor.count() > 0:
                    await editor.click(force=True, timeout=2000)
                    await asyncio.sleep(0.3)
                    await editor.fill(note_text)
            except Exception as e_ed:
                logger.debug("Direct editor fill note: %s", e_ed)

            await asyncio.sleep(0.5)

            # Force Angular model sync and execute note save directly in scope
            try:
                await self.page.evaluate(f"""() => {{
                    const el = document.querySelector('button.add-note-btn') || document.querySelector('#notes-tab button.add-note-btn') || document.querySelector('#notes-tab');
                    if (el && window.angular) {{
                        const s = angular.element(el).scope();
                        if (s) {{
                            let jobUri = null;
                            const sel = document.querySelector('.job-selection selectize, .job-selection .selectized, [ng-model*="job.activeJob"]');
                            if (sel && sel.selectize) {{
                                const currentVal = sel.selectize.getValue();
                                if (currentVal && currentVal.startsWith('/api/v1/job_form/employer_job/')) {{
                                    jobUri = currentVal;
                                }} else {{
                                    const opts = Object.keys(sel.selectize.options);
                                    jobUri = opts.find(k => k && k.startsWith('/api/v1/job_form/employer_job/'));
                                    if (jobUri) sel.selectize.setValue(jobUri);
                                }}
                            }}
                            if (!jobUri) {{
                                const validJobs = (s.ALLOWED_JOB_CHOICES || s.JOB_CHOICE_OPTIONS || []).filter(j => j && (j.uri || j.resource_uri || j.id));
                                if (validJobs.length > 0) {{
                                    jobUri = validJobs[0].uri || validJobs[0].resource_uri || `/api/v1/job_form/employer_job/${{validJobs[0].id}}`;
                                }}
                            }}
                            if (!jobUri) jobUri = '/api/v1/job_form/employer_job/17001';
                            if (!s.job) s.job = {{}};
                            s.job.activeJob = jobUri;
                            if (s.candidate) {{
                                s.candidate.searchSelectJobModal = false;
                                s.candidate.addingNoteFromSearchPage = false;
                            }}
                            if (!s.newNote || typeof s.newNote !== 'object') s.newNote = {{}};
                            s.newNote.note = `<p>{note_text}</p>`;
                            const ql = document.querySelector('.ql-editor');
                            if (ql) ql.innerHTML = `<p>{note_text}</p>`;
                            try {{
                                if (typeof s.addNote === 'function') {{
                                    s.addNote(s.candidate, s.candidateIdx);
                                }}
                            }} catch(e) {{}}
                            try {{ s.$apply(); }} catch(e) {{}}
                        }}
                    }}
                }}""")
            except Exception:
                pass

            # Also click save button if available
            try:
                save_btn = modal.locator(PROFILE_SELECTORS["note_save_button"]).first
                if await save_btn.count() > 0:
                    await save_btn.click(force=True)
                    logger.info("Clicked Add note button for '%s'.", note_text)
            except Exception as e_btn:
                logger.debug("Save button click note: %s", e_btn)
            await asyncio.sleep(3.5)

            # 4. Verification: confirm note actually appears in notes list or Instahyre API
            updated_notes = await self.get_existing_notes()
            confirmed = any(note_text.strip().lower() in n.lower() for n in updated_notes)
            if not confirmed:
                # Check Angular scope notes array and live Instahyre API
                await asyncio.sleep(1.5)
                try:
                    verified = await self.page.evaluate(f"""async () => {{
                        const btn = document.querySelector('#notes-tab button.add-note-btn') || document.querySelector('#notes-tab button');
                        if (btn && window.angular) {{
                            const s = angular.element(btn).scope();
                            if (s && s.notes && Array.isArray(s.notes)) {{
                                if (s.notes.some(n => ((n.note || '') + (n.note_text || '')).toLowerCase().includes('{note_text.strip().lower()}'))) return true;
                            }}
                            const candId = s && s.candidate ? s.candidate.id : null;
                            if (candId) {{
                                try {{
                                    const resp = await fetch(`/api/v1/resume_modal/notes/search_candidate_note?candidate_id=${{candId}}`);
                                    const data = await resp.json();
                                    if ((data.objects || []).some(o => (o.note || '').toLowerCase().includes('{note_text.strip().lower()}'))) return true;
                                }} catch(e) {{}}
                                try {{
                                    const resp2 = await fetch(`/api/v1/resume_modal/notes/limited_candidate_note?candidate_id=${{candId}}`);
                                    const data2 = await resp2.json();
                                    if ((data2.objects || []).some(o => (o.note || '').toLowerCase().includes('{note_text.strip().lower()}'))) return true;
                                }} catch(e) {{}}
                            }}
                        }}
                        return false;
                    }}""")
                    if verified:
                        confirmed = True
                except Exception:
                    pass

            if not confirmed:
                # Final check after brief delay
                await asyncio.sleep(1.5)
                updated_notes = await self.get_existing_notes()
                confirmed = any(note_text.strip().lower() in n.lower() for n in updated_notes)

            # Clean up response listener
            try:
                self.page.remove_listener("response", check_rate_limit)
            except Exception:
                pass

            if confirmed:
                logger.info("Note '%s' successfully saved and verified! All other notes remain intact.", note_text)
                return "NOTE_ADDED", None
            elif rate_limited_info["hit"]:
                logger.warning(
                    "Instahyre daily note quota reached (HTTP 429, retry-after: %s). Marking note as RATE_LIMITED.",
                    rate_limited_info["retry_after"],
                )
                return "RATE_LIMITED", f"Instahyre daily note limit reached (HTTP 429, retry-after: {rate_limited_info['retry_after']}s). Note queued."
            else:
                logger.error("Note write unconfirmed: '%s' not found in Instahyre notes list after clicking Add note.", note_text)
                return "NOTE_FAILED", f"Note not saved on Instahyre: '{note_text}' was not detected in notes list after clicking Add note"

        except Exception as exc:
            try:
                self.page.remove_listener("response", check_rate_limit)
            except Exception:
                pass
            logger.error("Failed to write note: %s", exc)
            return "NOTE_FAILED", str(exc)

    async def close_candidate_modal(self) -> None:
        """Close candidate profile drawer/modal to restore search view for next candidate."""
        if not self.page:
            return
        try:
            modal = self.page.locator(".application-modal-wrap, #resume-modal-block").first
            if await modal.count() > 0 and await modal.is_visible():
                close_btn = modal.locator(".application-modal-close, .modal-header .close, button.close, [ng-click*='closeModal'], [ng-click*='close'], .fa-times, .fa-close").first
                if await close_btn.count() > 0:
                    try:
                        await close_btn.click(force=True, timeout=2000)
                    except Exception:
                        pass

                await self.page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

                # Angular scope closeModal
                await self.page.evaluate("""() => {
                    const modal = document.querySelector('.application-modal-wrap, #resume-modal-block');
                    if (modal && window.angular) {
                        try {
                            const scope = angular.element(modal).scope();
                            if (scope) {
                                if (typeof scope.closeModal === 'function') scope.closeModal();
                                else if (typeof scope.$dismiss === 'function') scope.$dismiss();
                                else if (typeof scope.$close === 'function') scope.$close();
                                scope.$apply();
                            }
                        } catch (e) {}
                    }
                }""")
                await asyncio.sleep(0.5)

                # Dismiss abuse limit modal or backdrop if visible
                try:
                    await self.page.evaluate("""() => {
                        const abuse = document.querySelector('.abuse-limit-activated-container, .abuse-limit-container');
                        if (abuse) {
                            const btn = abuse.querySelector('.close, button, .modal-close');
                            if (btn) btn.click();
                        }
                    }""")
                    await self.page.keyboard.press("Escape")
                except Exception:
                    pass

                if await modal.is_visible():
                    backdrop = self.page.locator(".application-modal-backdrop, .modal-backdrop").first
                    if await backdrop.count() > 0:
                        try:
                            await backdrop.click(force=True, timeout=2000)
                        except Exception:
                            pass

            await asyncio.sleep(0.5)
        except Exception as exc:
            logger.warning("Error closing candidate modal: %s", exc)

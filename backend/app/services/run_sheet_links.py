"""Resolve Google Sheet tab + short Instahyre label for each screening run."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse, unquote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.screening_run import ScreeningRun
from app.services.sheet_export_service import TECH_SHEET_MAP

_GID_FILE = Path(__file__).resolve().parents[1] / "data" / "sheet_tab_gids.json"

# Manual overrides when export used a non–one-url-one-sheet tab (run_id, technology)
RUN_SHEET_TAB_OVERRIDES: Dict[tuple[int, str], str] = {
    (16, "java"): "Sheet7",
}


def _load_tab_gids() -> Dict[str, Dict[str, str]]:
    if not _GID_FILE.exists():
        return {}
    try:
        return json.loads(_GID_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _technology_from_run(run: ScreeningRun) -> str:
    try:
        cfg = json.loads(run.configuration_snapshot or "{}")
        tech = (cfg.get("technology") or run.technology or "golang").lower()
    except Exception:
        tech = (run.technology or "golang").lower()
    if tech == "qa":
        tech = "qa_automation"
    return tech


def _config_from_run(run: ScreeningRun) -> Dict[str, Any]:
    try:
        return json.loads(run.configuration_snapshot or "{}")
    except Exception:
        return {}


def _diff_exclude_run_id(run: ScreeningRun) -> Optional[int]:
    raw = _config_from_run(run).get("diff_exclude_run_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _search_url_from_run(run: ScreeningRun) -> str:
    if not run.configuration_snapshot:
        return ""
    try:
        cfg = json.loads(run.configuration_snapshot)
        return (cfg.get("instahyre_search_url") or "").strip()
    except Exception:
        return ""


def search_url_fingerprint(url: str) -> str:
    """Same Instahyre search even if URL encoding or extra params differ between runs."""
    if not url:
        return ""
    q = parse_qs(urlparse(url).query, keep_blank_values=True)
    saved = (q.get("saved_search") or [""])[0]
    work = (q.get("workex_min") or [""])[0], (q.get("workex_max") or [""])[0]
    if saved:
        parts = [f"saved:{saved}"]
        if work[0] or work[1]:
            parts.append(f"exp:{work[0]}-{work[1]}")
        return "|".join(parts)
    parts: List[str] = []
    if q.get("filter_date"):
        parts.append("filter_date")
    flat_q = unquote(url).lower()
    if "lld" in flat_q or "system+design" in flat_q or "system design" in flat_q:
        parts.append("lld")
    if work[0] or work[1]:
        parts.append(f"exp:{work[0]}-{work[1]}")
    bq = (q.get("boolean_query") or [""])[0]
    if bq:
        parts.append(f"bq:{re.sub(r'\\s+', ' ', unquote(bq)).lower()[:120]}")
    return "|".join(parts) or url.strip()


def find_run_for_exact_url(db: Session, url: str) -> Optional[ScreeningRun]:
    """Latest run whose stored Instahyre URL matches exactly (ignoring trailing slashes)."""
    target = (url or "").strip().rstrip("/")
    if not target:
        return None
    runs = db.execute(select(ScreeningRun).order_by(ScreeningRun.id.desc())).scalars().all()
    for run in runs:
        u = _search_url_from_run(run).rstrip("/")
        if u == target:
            return run
    return None


def find_baseline_run_for_url(db: Session, url: str) -> Optional[ScreeningRun]:
    """
    Run to diff against: exact URL first, else same saved-search fingerprint.
    Prefers a completed baseline run (no diff_exclude_run_id), then newest id.
    """
    exact = find_run_for_exact_url(db, url)
    if exact:
        return exact
    fp = search_url_fingerprint(url)
    if not fp:
        return None
    runs = db.execute(select(ScreeningRun).order_by(ScreeningRun.id.desc())).scalars().all()
    matches = [
        r
        for r in runs
        if search_url_fingerprint(_search_url_from_run(r)) == fp
    ]
    if not matches:
        return None
    baselines = [r for r in matches if _diff_exclude_run_id(r) is None]
    pool = baselines or matches
    preferred = [r for r in pool if r.status == "COMPLETED"]
    if preferred:
        return max(preferred, key=lambda r: r.id)
    return max(pool, key=lambda r: r.id)


def plan_multi_comparison(db: Session, urls: List[str]) -> Dict[str, Any]:
    """
    urls[0..-2] = reference searches (must be in DB to compare using stored walks).
    urls[-1] = target to screen; skip if candidate appeared in any reference run.
    """
    cleaned = [u.strip() for u in urls if u and str(u).strip().startswith("http")]
    if len(cleaned) < 2:
        return {
            "ready": False,
            "message": "Add at least 2 links (older lists first, newest list last).",
            "url_slots": [],
            "exclude_run_ids": [],
        }
    refs = cleaned[:-1]
    target = cleaned[-1]
    slots: List[Dict[str, Any]] = []
    exclude_ids: List[int] = []
    missing_refs: List[int] = []
    for i, u in enumerate(cleaned):
        run = find_baseline_run_for_url(db, u)
        is_target = i == len(cleaned) - 1
        slots.append(
            {
                "index": i + 1,
                "url": u,
                "run_id": run.id if run else None,
                "status": run.status if run else None,
                "in_db": run is not None,
                "role": "target" if is_target else "reference",
            }
        )
        if not is_target:
            if run:
                if run.id not in exclude_ids:
                    exclude_ids.append(run.id)
            else:
                missing_refs.append(i + 1)
    if missing_refs:
        return {
            "ready": False,
            "message": (
                f"Link(s) {missing_refs} are not in the database yet. "
                "Run each missing link as a Unique search first, then compare again."
            ),
            "url_slots": slots,
            "exclude_run_ids": exclude_ids,
            "target_url_index": len(cleaned),
        }
    target_run = find_run_for_exact_url(db, target)
    ref_label = ", ".join(f"#{r}" for r in exclude_ids)
    if target_run:
        msg = (
            f"Target link already screened as run #{target_run.id}. "
            f"You can re-diff vs reference run(s) {ref_label} using DB data (no re-walk of references)."
        )
    else:
        msg = (
            f"Ready: walk the last link only; skip candidates already in reference run(s) {ref_label}."
        )
    return {
        "ready": True,
        "message": msg,
        "url_slots": slots,
        "exclude_run_ids": exclude_ids,
        "target_url_index": len(cleaned),
        "target_existing_run_id": target_run.id if target_run else None,
        "baseline_run_id": exclude_ids[0] if exclude_ids else None,
    }


def find_newest_diff_run_for_urls(db: Session, baseline_url: str, new_url: str) -> Optional[ScreeningRun]:
    """Newest comparison run for this pair (new URL run with diff_exclude = baseline run)."""
    baseline = find_baseline_run_for_url(db, baseline_url)
    if not baseline:
        return None
    runs = db.execute(select(ScreeningRun).order_by(ScreeningRun.id.desc())).scalars().all()
    new_fp = search_url_fingerprint(new_url)
    for run in runs:
        if _diff_exclude_run_id(run) != baseline.id:
            continue
        u = _search_url_from_run(run)
        if u.rstrip("/") == new_url.strip().rstrip("/") or (
            new_fp and search_url_fingerprint(u) == new_fp
        ):
            return run
    return None


def shorten_instahyre_url(url: str) -> str:
    if not url:
        return "—"
    try:
        q = parse_qs(urlparse(url).query)
        bits: List[str] = []
        if q.get("saved_search"):
            bits.append(f"saved #{q['saved_search'][0]}")
        if q.get("filter_date"):
            bits.append("filter_date")
        if "LLD" in url or "System+Design" in url or "System%20Design" in url:
            bits.append("LLD")
        if q.get("workex_min") or q.get("workex_max"):
            wmin = q.get("workex_min", [""])[0]
            wmax = q.get("workex_max", [""])[0]
            if wmin or wmax:
                bits.append(f"exp {wmin}-{wmax}y")
        if bits:
            return " · ".join(bits)
    except Exception:
        pass
    return url[:56] + "…" if len(url) > 56 else url


def _tab_for_url(db: Session, run_id: int, search_url: str) -> str:
    if not search_url:
        return "Sheet1"
    runs = db.execute(select(ScreeningRun).order_by(ScreeningRun.id.asc())).scalars().all()
    distinct: List[str] = []
    for r in runs:
        u = _search_url_from_run(r)
        if u and u not in distinct:
            distinct.append(u)
    if search_url not in distinct:
        distinct.append(search_url)
    idx = distinct.index(search_url)
    return f"Sheet{idx + 1}"


def sheet_tab_for_run(db: Session, run: ScreeningRun) -> str:
    tech = _technology_from_run(run)
    override = RUN_SHEET_TAB_OVERRIDES.get((run.id, tech))
    if override:
        return override
    try:
        cfg = json.loads(run.configuration_snapshot or "{}")
        if cfg.get("diff_exclude_run_id"):
            return "Sheet7"
    except Exception:
        pass
    return _tab_for_url(db, run.id, _search_url_from_run(run))


def build_sheet_link(technology: str, tab: str) -> str:
    tech = technology.lower()
    if tech == "qa":
        tech = "qa_automation"
    base = TECH_SHEET_MAP.get(tech, TECH_SHEET_MAP["golang"])
    m = re.search(r"/d/([^/]+)", base)
    if not m:
        return base
    doc_id = m.group(1)
    gids = _load_tab_gids().get(tech, {})
    gid = gids.get(tab)
    if gid:
        return f"https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={gid}"
    return f"https://docs.google.com/spreadsheets/d/{doc_id}/edit"


def run_search_summaries(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Last N distinct Instahyre search URLs (newest run wins if same URL was retried)."""
    runs = db.execute(
        select(ScreeningRun).order_by(ScreeningRun.started_at.desc()).limit(80)
    ).scalars().all()
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for run in runs:
        url = _search_url_from_run(run)
        fp = search_url_fingerprint(url) or f"__run_{run.id}"
        if fp in seen:
            continue
        seen.add(fp)
        tech = _technology_from_run(run)
        tab = sheet_tab_for_run(db, run)
        short = shorten_instahyre_url(url)
        entry: Dict[str, Any] = {
            "run_id": run.id,
            "technology": tech,
            "status": run.status,
            "started_at": run.started_at,
            "instahyre_search_short": short,
            "instahyre_search_url": url or None,
            "google_sheet_tab": tab,
            "google_sheet_url": build_sheet_link(tech, tab),
            "is_comparison": False,
            "comparison": None,
        }
        diff_id = _diff_exclude_run_id(run)
        if diff_id:
            base = db.get(ScreeningRun, diff_id)
            if base:
                base_url = _search_url_from_run(base)
                base_tab = sheet_tab_for_run(db, base)
                entry["is_comparison"] = True
                entry["instahyre_search_short"] = (
                    f"Compare run #{diff_id} → #{run.id} (new only)"
                )
                entry["comparison"] = {
                    "baseline_run_id": diff_id,
                    "baseline_search_short": shorten_instahyre_url(base_url),
                    "baseline_search_url": base_url or None,
                    "baseline_sheet_tab": base_tab,
                    "baseline_sheet_url": build_sheet_link(tech, base_tab),
                    "new_run_id": run.id,
                    "new_search_short": short,
                    "new_search_url": url or None,
                    "new_only_sheet_tab": tab,
                    "new_only_sheet_url": build_sheet_link(tech, tab),
                }
        out.append(entry)
        if len(out) >= limit:
            break
    return out
"""API endpoints for screening runs and dashboard metrics."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.screening_repo import ScreeningRepository
from app.schemas.screening import ScreeningRunRead, DashboardMetrics, RecentSearchSummary

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs", response_model=List[ScreeningRunRead])
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    technology: str = Query("golang"),
    db: Session = Depends(get_db),
):
    """Retrieve history of screening runs."""
    repo = ScreeningRepository(db)
    runs = repo.list_runs(limit=limit)
    return [ScreeningRunRead.model_validate(r) for r in runs]


@router.get("/recent-searches", response_model=List[RecentSearchSummary])
def recent_searches(
    limit: int = Query(5, ge=1, le=20),
    technology: str = Query("golang"),
    db: Session = Depends(get_db),
):
    """Last N runs with tech, short Instahyre label, and Google Sheet tab link."""
    from app.services.run_sheet_links import run_search_summaries

    return run_search_summaries(db, limit=limit)


@router.get("/technology-counts")
def get_technology_counts():
    """Return candidate totals for every technology in one database connection."""
    from sqlalchemy import text
    from app.core.cache import cache_get, cache_put
    from app.database.session import TECHNOLOGY_DB_MAP, _uses_postgres, get_engine_for_tech

    cached = cache_get("technology-counts")
    if cached is not None:
        return cached

    counts = {}
    techs = [tech for tech in TECHNOLOGY_DB_MAP if tech != "qa"]
    if _uses_postgres():
        from app.database.session import postgres_lock

        engine = get_engine_for_tech("golang")
        with postgres_lock, engine.connect() as conn:
            for tech in techs:
                counts[tech] = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{tech}".candidates')
                ).scalar() or 0
        cache_put("technology-counts", counts)
        return counts

    for tech in techs:
        engine = get_engine_for_tech(tech)
        with engine.connect() as conn:
            counts[tech] = conn.execute(text("SELECT COUNT(*) FROM candidates")).scalar() or 0
    cache_put("technology-counts", counts)
    return counts


@router.get("/metrics", response_model=DashboardMetrics)
def get_metrics(run_id: Optional[int] = Query(None), technology: str = Query("golang")):
    """Retrieve real-time metrics computed directly from database records."""
    from app.core.cache import cache_get, cache_put
    from app.database.session import _canonical_tech

    tech = _canonical_tech(technology)
    cache_key = ("metrics", tech, run_id)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    db_gen = get_db(technology=tech)
    db = next(db_gen)
    try:
        metrics_data = ScreeningRepository(db).get_dashboard_metrics(run_id=run_id)
        result = DashboardMetrics.model_validate(metrics_data)
    finally:
        db_gen.close()
    cache_put(cache_key, result)
    return result


# Lifecycle Actions
from app.core.state import state_manager, RunState
from pydantic import BaseModel


class ActionResponse(BaseModel):
    success: bool
    message: str
    run_state: RunState
    run_id: Optional[int] = None


from app.services.screening_service import orchestrator
from app.core.config import get_settings


from app.database.session import get_sessionmaker_for_tech


class StartRunRequest(BaseModel):
    technology: Optional[str] = "golang"
    search_url: Optional[str] = None
    limit: Optional[int] = None
    diff_exclude_run_id: Optional[int] = None
    diff_exclude_run_ids: Optional[List[int]] = None
    baseline_url: Optional[str] = None
    comparison_urls: Optional[List[str]] = None


class ComparisonUrlSlot(BaseModel):
    index: int
    url: str
    run_id: Optional[int] = None
    status: Optional[str] = None
    in_db: bool = False
    role: str = "reference"


class ComparisonResolveRequest(BaseModel):
    technology: Optional[str] = "golang"
    urls: Optional[List[str]] = None
    baseline_url: Optional[str] = None
    new_url: Optional[str] = None


class ComparisonResolveResponse(BaseModel):
    ready: bool
    message: str
    baseline_run_id: Optional[int] = None
    baseline_status: Optional[str] = None
    new_existing_run_id: Optional[int] = None
    baseline_sheet_tab: Optional[str] = None
    baseline_sheet_url: Optional[str] = None
    exclude_run_ids: Optional[List[int]] = None
    url_slots: Optional[List[ComparisonUrlSlot]] = None
    target_url_index: Optional[int] = None
    target_existing_run_id: Optional[int] = None


def _comparison_url_list(payload: ComparisonResolveRequest) -> List[str]:
    if payload.urls:
        return [u.strip() for u in payload.urls if u and u.strip().startswith("http")]
    if payload.baseline_url and payload.new_url:
        return [payload.baseline_url.strip(), payload.new_url.strip()]
    return []


@router.post("/resolve-comparison", response_model=ComparisonResolveResponse)
@router.post("/runs/resolve-comparison", response_model=ComparisonResolveResponse)
def resolve_comparison(payload: ComparisonResolveRequest):
    """Check which comparison URLs are in DB and whether target can diff."""
    from app.services.run_sheet_links import plan_multi_comparison

    tech = (payload.technology or "golang").lower()
    urls = _comparison_url_list(payload)
    if len(urls) < 2:
        return ComparisonResolveResponse(
            ready=False,
            message="Add at least 2 links (references first, target last).",
        )
    db = get_sessionmaker_for_tech(tech)()
    try:
        plan = plan_multi_comparison(db, urls)
        slots = [ComparisonUrlSlot.model_validate(s) for s in plan.get("url_slots") or []]
        return ComparisonResolveResponse(
            ready=bool(plan.get("ready")),
            message=str(plan.get("message") or ""),
            baseline_run_id=plan.get("baseline_run_id"),
            new_existing_run_id=plan.get("target_existing_run_id"),
            exclude_run_ids=plan.get("exclude_run_ids"),
            url_slots=slots or None,
            target_url_index=plan.get("target_url_index"),
            target_existing_run_id=plan.get("target_existing_run_id"),
        )
    finally:
        db.close()


@router.post("/runs/start", response_model=ActionResponse)
async def start_screening(payload: Optional[StartRunRequest] = None):
    """Initiate a new screening run for the selected technology and search URL."""
    settings = get_settings()
    tech = payload.technology.lower() if payload and payload.technology else "golang"
    custom_search_url = payload.search_url if payload and payload.search_url else None
    run_limit = payload.limit if payload and payload.limit else None

    if not custom_search_url or not custom_search_url.strip().startswith("http"):
        return ActionResponse(
            success=False,
            message="Instahyre Search URL is required. Please paste your filtered Instahyre search URL in the search box before starting.",
            run_state=state_manager.state,
            run_id=None,
        )

    if state_manager.state in (RunState.RUNNING, RunState.VALIDATING, RunState.PAUSE_REQUESTED):
        return ActionResponse(
            success=False,
            message=f"Cannot start run while in {state_manager.state} state",
            run_state=state_manager.state,
            run_id=state_manager.active_run_id,
        )

    sm = get_sessionmaker_for_tech(tech)
    db = sm()
    diff_exclude_run_id = payload.diff_exclude_run_id if payload else None
    diff_exclude_run_ids: List[int] = list(payload.diff_exclude_run_ids or []) if payload else []
    try:
        if payload and payload.comparison_urls:
            from app.services.run_sheet_links import plan_multi_comparison

            plan = plan_multi_comparison(db, payload.comparison_urls)
            if not plan.get("ready"):
                return ActionResponse(
                    success=False,
                    message=str(plan.get("message") or "Comparison not ready."),
                    run_state=state_manager.state,
                    run_id=None,
                )
            diff_exclude_run_ids = list(plan.get("exclude_run_ids") or [])
            custom_search_url = payload.comparison_urls[-1].strip()
        elif payload and payload.baseline_url and payload.baseline_url.strip().startswith("http"):
            from app.services.run_sheet_links import find_baseline_run_for_url

            baseline = find_baseline_run_for_url(db, payload.baseline_url.strip())
            if not baseline:
                return ActionResponse(
                    success=False,
                    message="Comparison baseline URL not found in DB. Run the first URL with Start, then try again.",
                    run_state=state_manager.state,
                    run_id=None,
                )
            diff_exclude_run_id = baseline.id
            if baseline.id not in diff_exclude_run_ids:
                diff_exclude_run_ids.append(baseline.id)
        if diff_exclude_run_id and diff_exclude_run_id not in diff_exclude_run_ids:
            diff_exclude_run_ids.append(diff_exclude_run_id)
        repo = ScreeningRepository(db)
        config_snapshot = settings.get_safe_status()
        config_snapshot["technology"] = tech
        if custom_search_url:
            config_snapshot["instahyre_search_url"] = custom_search_url
        if diff_exclude_run_ids:
            config_snapshot["diff_exclude_run_ids"] = diff_exclude_run_ids
            config_snapshot["diff_exclude_run_id"] = diff_exclude_run_ids[0]
        elif diff_exclude_run_id:
            config_snapshot["diff_exclude_run_id"] = diff_exclude_run_id
        if payload and payload.comparison_urls:
            config_snapshot["comparison_urls"] = payload.comparison_urls
            config_snapshot["comparison_mode"] = True
        elif payload and payload.baseline_url:
            config_snapshot["comparison_baseline_url"] = payload.baseline_url.strip()
            config_snapshot["comparison_mode"] = True
        run = repo.create_run(configuration_snapshot=json.dumps(config_snapshot))
        run_id = run.id
        state_manager.start_run(run_id=run_id, technology=tech)
        msg = f"Screening Run #{run_id} started for {tech.upper()}"
        if diff_exclude_run_ids:
            msg += f" (diff vs runs {', '.join(f'#{r}' for r in diff_exclude_run_ids)})"
        elif diff_exclude_run_id:
            msg += f" (diff vs run #{diff_exclude_run_id})"
        repo.record_activity_event(
            run_id=run_id,
            event_type="RUN_STARTED",
            message=msg,
        )
    finally:
        db.close()

    # Launch background screening task
    await orchestrator.start(
        run_id=run_id,
        dry_run=settings.DRY_RUN,
        technology=tech,
        search_url=custom_search_url,
        max_candidates=run_limit,
    )

    return ActionResponse(
        success=True,
        message=f"Run #{run_id} ({tech.upper()}) started successfully",
        run_state=state_manager.state,
        run_id=run_id,
    )


@router.post("/runs/pause", response_model=ActionResponse)
def pause_screening(db: Session = Depends(get_db)):
    """Request a safe pause."""
    repo = ScreeningRepository(db)
    ok = state_manager.request_pause()
    if ok and state_manager.active_run_id:
        repo.record_activity_event(
            run_id=state_manager.active_run_id,
            event_type="PAUSE_REQUESTED",
            message="Pause requested. Agent will halt before next candidate.",
        )
        return ActionResponse(
            success=True,
            message="Pause requested successfully",
            run_state=state_manager.state,
            run_id=state_manager.active_run_id,
        )
    return ActionResponse(
        success=False,
        message=f"Cannot pause from {state_manager.state} state",
        run_state=state_manager.state,
        run_id=state_manager.active_run_id,
    )


@router.post("/runs/resume", response_model=ActionResponse)
def resume_screening(db: Session = Depends(get_db)):
    """Resume a paused screening run."""
    repo = ScreeningRepository(db)
    ok = state_manager.resume()
    if ok and state_manager.active_run_id:
        repo.record_activity_event(
            run_id=state_manager.active_run_id,
            event_type="RUN_RESUMED",
            message="Screening resumed from safe checkpoint.",
        )
        return ActionResponse(
            success=True,
            message="Run resumed successfully",
            run_state=state_manager.state,
            run_id=state_manager.active_run_id,
        )
    return ActionResponse(
        success=False,
        message=f"Cannot resume from {state_manager.state} state",
        run_state=state_manager.state,
        run_id=state_manager.active_run_id,
    )


@router.post("/runs/stop", response_model=ActionResponse)
def stop_screening(db: Session = Depends(get_db)):
    """Request a safe stop."""
    repo = ScreeningRepository(db)
    run_id = state_manager.active_run_id
    ok = state_manager.request_stop()
    if ok:
        state_manager.confirm_stop()
        if run_id:
            repo.update_run_status(run_id=run_id, status="STOPPED", finished=True)
            repo.record_activity_event(
                run_id=run_id,
                event_type="RUN_STOPPED",
                message="Run stopped safely by user.",
            )
        return ActionResponse(
            success=True,
            message="Run stopped safely",
            run_state=state_manager.state,
            run_id=None,
        )
    return ActionResponse(
        success=False,
        message=f"Cannot stop from {state_manager.state} state",
        run_state=state_manager.state,
        run_id=state_manager.active_run_id,
    )


@router.get("/runs/{run_id}", response_model=ScreeningRunRead)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Fetch run details by ID."""
    repo = ScreeningRepository(db)
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return ScreeningRunRead.model_validate(run)

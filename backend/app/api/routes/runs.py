"""API endpoints for screening runs and dashboard metrics."""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.screening_repo import ScreeningRepository
from app.schemas.screening import ScreeningRunRead, DashboardMetrics

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs", response_model=List[ScreeningRunRead])
def list_runs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Retrieve history of screening runs."""
    repo = ScreeningRepository(db)
    runs = repo.list_runs(limit=limit)
    return [ScreeningRunRead.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=ScreeningRunRead)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Fetch run details by ID."""
    repo = ScreeningRepository(db)
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return ScreeningRunRead.model_validate(run)


@router.get("/metrics", response_model=DashboardMetrics)
def get_metrics(run_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Retrieve real-time metrics computed directly from database records."""
    repo = ScreeningRepository(db)
    metrics_data = repo.get_dashboard_metrics(run_id=run_id)
    return DashboardMetrics.model_validate(metrics_data)


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
    try:
        repo = ScreeningRepository(db)
        config_snapshot = settings.get_safe_status()
        config_snapshot["technology"] = tech
        if custom_search_url:
            config_snapshot["instahyre_search_url"] = custom_search_url
        run = repo.create_run(configuration_snapshot=json.dumps(config_snapshot))
        run_id = run.id
        state_manager.start_run(run_id=run_id)
        repo.record_activity_event(
            run_id=run_id,
            event_type="RUN_STARTED",
            message=f"Screening Run #{run_id} started for {tech.upper()}",
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

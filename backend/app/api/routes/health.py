"""Health and system status routes."""

import os
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from app import __version__
from app.core.config import get_settings
from app.core.state import state_manager, RunState, CurrentOperation

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class SystemStatusResponse(BaseModel):
    status: str
    version: str
    run_state: RunState
    active_run_id: int | None
    active_technology: str = "golang"
    current_operation: CurrentOperation
    is_github_configured: bool
    is_instahyre_configured: bool
    dry_run: bool
    instahyre_search_url: str
    database_ready: bool


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Liveness check."""
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=__version__,
        environment=settings.ENVIRONMENT,
    )


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status():
    """Comprehensive system status with safe credential flags (zero secrets exposed)."""
    settings = get_settings()
    
    # Check if database file directory exists/writable
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_ready = True
    try:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        db_ready = False

    return SystemStatusResponse(
        status="operational",
        version=__version__,
        run_state=state_manager.state,
        active_run_id=state_manager.active_run_id,
        active_technology=state_manager.active_technology,
        current_operation=state_manager.current_operation,
        is_github_configured=settings.is_github_token_configured,
        is_instahyre_configured=settings.is_instahyre_configured,
        dry_run=settings.DRY_RUN,
        instahyre_search_url=settings.INSTAHYRE_SEARCH_URL,
        database_ready=db_ready,
    )


@router.get("/config")
def get_safe_config():
    """Retrieve safe configuration metadata (passwords and tokens are strictly excluded)."""
    settings = get_settings()
    return settings.get_safe_status()

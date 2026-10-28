"""API endpoints for activity events and audit history."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.screening_repo import ScreeningRepository
from app.schemas.screening import ActivityEventRead

from fastapi.responses import StreamingResponse
from app.services.event_service import event_generator

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=List[ActivityEventRead])
def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
    run_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve chronologically ordered activity events."""
    repo = ScreeningRepository(db)
    events = repo.get_recent_events(limit=limit, run_id=run_id)
    return [ActivityEventRead.model_validate(e) for e in events]


@router.get("/stream")
async def stream_events():
    """Real-time Server-Sent Events (SSE) feed of activity logs."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

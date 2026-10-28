"""Screening run model tracking operational sessions and checkpoints."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

if TYPE_CHECKING:
    from app.models.screening_result import ScreeningResult
    from app.models.note_action import NoteAction
    from app.models.activity_event import ActivityEvent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScreeningRun(Base):
    """Screening run record."""

    __tablename__ = "screening_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(50), default="IDLE", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_checkpoint: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    configuration_snapshot: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    screening_results: Mapped[List["ScreeningResult"]] = relationship(
        "ScreeningResult", back_populates="run", cascade="all, delete-orphan"
    )
    note_actions: Mapped[List["NoteAction"]] = relationship(
        "NoteAction", back_populates="run", cascade="all, delete-orphan"
    )
    activity_events: Mapped[List["ActivityEvent"]] = relationship(
        "ActivityEvent", back_populates="run"
    )

    def __repr__(self) -> str:
        return f"<ScreeningRun id={self.id} status='{self.status}' processed={self.processed_count}>"

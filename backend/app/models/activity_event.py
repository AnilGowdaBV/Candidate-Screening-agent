"""Activity event persistence model for timeline and audit history."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.screening_run import ScreeningRun


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ActivityEvent(Base):
    """Audit and timeline event logged during screening execution."""

    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("screening_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    candidate: Mapped[Optional["Candidate"]] = relationship("Candidate", back_populates="activity_events")
    run: Mapped[Optional["ScreeningRun"]] = relationship("ScreeningRun", back_populates="activity_events")

    __table_args__ = (
        Index("idx_events_run_created", "run_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ActivityEvent id={self.id} type='{self.event_type}' created_at={self.created_at}>"

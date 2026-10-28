"""Note action model tracking notes written to Instahyre with confirmation timestamps."""

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


class NoteAction(Base):
    """Note recorded or attempted on an Instahyre candidate profile."""

    __tablename__ = "note_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("screening_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_text: Mapped[str] = mapped_column(String(255), nullable=False)
    action_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # NOTE_ADDED, NOTE_ALREADY_EXISTS, NOTE_FAILED, NOTE_OUTCOME_UNKNOWN, SKIPPED
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="note_actions")
    run: Mapped["ScreeningRun"] = relationship("ScreeningRun", back_populates="note_actions")

    __table_args__ = (
        Index("idx_note_candidate_status", "candidate_id", "action_status"),
    )

    def __repr__(self) -> str:
        return f"<NoteAction id={self.id} candidate_id={self.candidate_id} note='{self.note_text}' status='{self.action_status}'>"

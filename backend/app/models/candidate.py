"""Candidate identity model with strict deduplication constraints."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

if TYPE_CHECKING:
    from app.models.screening_result import ScreeningResult
    from app.models.note_action import NoteAction
    from app.models.activity_event import ActivityEvent


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Candidate(Base):
    """Candidate representation stored locally in SQLite."""

    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("technology", "instahyre_profile_url", name="uq_candidate_tech_url"),
        UniqueConstraint("technology", "instahyre_external_id", name="uq_candidate_tech_ext"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    technology: Mapped[str] = mapped_column(String(50), default="golang", nullable=False, index=True)
    instahyre_profile_url: Mapped[str] = mapped_column(
        String(700), index=True, nullable=False
    )
    instahyre_external_id: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_url: Mapped[Optional[str]] = mapped_column(
        String(500), index=True, nullable=True
    )
    # GitRoll Assessment Fields
    gitroll_rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    actual_gitroll_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    gitroll_grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gitroll_profile_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    gitroll_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gitroll_note_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Instahyre Compensation & Location Fields
    current_salary: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    experience: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    coding_profiles: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    languages_found: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    screening_results: Mapped[List["ScreeningResult"]] = relationship(
        "ScreeningResult", back_populates="candidate", cascade="all, delete-orphan"
    )
    note_actions: Mapped[List["NoteAction"]] = relationship(
        "NoteAction", back_populates="candidate", cascade="all, delete-orphan"
    )
    activity_events: Mapped[List["ActivityEvent"]] = relationship(
        "ActivityEvent", back_populates="candidate"
    )

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} name='{self.name}' github='{self.github_url}'>"

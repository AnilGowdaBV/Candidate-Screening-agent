"""Screening result model for storing candidate GitHub verification findings."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.screening_run import ScreeningRun


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScreeningResult(Base):
    """Result of examining a candidate's GitHub profile for Go/Golang evidence."""

    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("screening_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    github_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # GITHUB_FOUND, GITHUB_NOT_FOUND, GITHUB_INVALID
    go_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # GO_DETECTED, GO_NOT_DETECTED, GITHUB_NOT_FOUND, CHECK_INCOMPLETE, API_RATE_LIMITED, API_ERROR
    evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repositories_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    languages_found: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="screening_results")
    run: Mapped["ScreeningRun"] = relationship("ScreeningRun", back_populates="screening_results")

    def __repr__(self) -> str:
        return f"<ScreeningResult id={self.id} candidate_id={self.candidate_id} go_status='{self.go_status}'>"

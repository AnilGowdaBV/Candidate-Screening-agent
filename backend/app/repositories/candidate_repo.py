"""Candidate repository handling safe lookup, deduplication, and updates."""

from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import Session
from app.models.candidate import Candidate
from app.models.screening_result import ScreeningResult
from app.models.note_action import NoteAction


class CandidateRepository:
    """Repository for candidate identity and data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, candidate_id: int) -> Optional[Candidate]:
        """Fetch candidate by primary key."""
        return self.db.get(Candidate, candidate_id)

    def find_by_identifier(
        self, instahyre_profile_url: str, instahyre_external_id: Optional[str] = None
    ) -> Optional[Candidate]:
        """Safely locate candidate by profile URL or external ID to prevent duplicates."""
        conditions = [Candidate.instahyre_profile_url == instahyre_profile_url]
        if instahyre_external_id:
            conditions.append(Candidate.instahyre_external_id == instahyre_external_id)

        stmt = select(Candidate).where(or_(*conditions))
        return self.db.execute(stmt).scalars().first()

    def get_or_create(
        self,
        instahyre_profile_url: str,
        name: str,
        instahyre_external_id: Optional[str] = None,
        github_url: Optional[str] = None,
        current_salary: Optional[str] = None,
        location: Optional[str] = None,
        experience: Optional[str] = None,
        coding_profiles: Optional[str] = None,
    ) -> Tuple[Candidate, bool]:
        """
        Locate existing candidate or create a new candidate record.
        Returns (candidate, created: bool).
        """
        existing = self.find_by_identifier(instahyre_profile_url, instahyre_external_id)
        if existing:
            # Update last seen and any missing fields safely
            existing.last_seen_at = datetime.now(timezone.utc)
            if not existing.github_url and github_url:
                existing.github_url = github_url
            if not existing.instahyre_external_id and instahyre_external_id:
                existing.instahyre_external_id = instahyre_external_id
            if not existing.current_salary and current_salary:
                existing.current_salary = current_salary
            if not existing.location and location:
                existing.location = location
            if not existing.experience and experience:
                existing.experience = experience
            if not existing.coding_profiles and coding_profiles:
                existing.coding_profiles = coding_profiles
            self.db.commit()
            self.db.refresh(existing)
            return existing, False

        candidate = Candidate(
            instahyre_profile_url=instahyre_profile_url,
            instahyre_external_id=instahyre_external_id,
            name=name,
            github_url=github_url,
            current_salary=current_salary,
            location=location,
            experience=experience,
            coding_profiles=coding_profiles,
        )
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate, True

    def update_current_salary(self, candidate_id: int, current_salary: str) -> Optional[Candidate]:
        """Update candidate current salary."""
        candidate = self.get_by_id(candidate_id)
        if candidate and current_salary:
            candidate.current_salary = current_salary
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def update_experience(self, candidate_id: int, experience: str) -> Optional[Candidate]:
        """Update candidate total experience from Instahyre."""
        candidate = self.get_by_id(candidate_id)
        if candidate and experience:
            candidate.experience = experience
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def update_location(self, candidate_id: int, location: str) -> Optional[Candidate]:
        """Update candidate location."""
        candidate = self.get_by_id(candidate_id)
        if candidate and location:
            candidate.location = location
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def update_coding_profiles(self, candidate_id: int, coding_profiles: str) -> Optional[Candidate]:
        """Update candidate coding profiles (LeetCode, HackerRank, CodeChef, ICPC)."""
        candidate = self.get_by_id(candidate_id)
        if candidate and coding_profiles:
            candidate.coding_profiles = coding_profiles
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def update_github_url(self, candidate_id: int, github_url: str) -> Optional[Candidate]:
        """Update candidate GitHub URL."""
        candidate = self.get_by_id(candidate_id)
        if candidate:
            candidate.github_url = github_url
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def update_languages_found(self, candidate_id: int, languages_found: str) -> Optional[Candidate]:
        """Update candidate languages found."""
        candidate = self.get_by_id(candidate_id)
        if candidate:
            candidate.languages_found = languages_found
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def update_gitroll_score(self, candidate_id: int, score: float) -> Optional[Candidate]:
        """Update candidate GitScore / gitroll_rating."""
        candidate = self.get_by_id(candidate_id)
        if candidate:
            candidate.gitroll_rating = score
            candidate.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    def list_candidates(
        self,
        filter_status: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Candidate], int]:
        """List candidates with optional filtering and pagination."""
        stmt = select(Candidate)

        if search_query:
            pattern = f"%{search_query}%"
            stmt = stmt.where(
                or_(
                    Candidate.name.ilike(pattern),
                    Candidate.instahyre_profile_url.ilike(pattern),
                    Candidate.github_url.ilike(pattern),
                )
            )

        if filter_status:
            status_upper = filter_status.strip().upper()
            if status_upper == "GITHUB_FOUND":
                stmt = stmt.where(and_(Candidate.github_url.isnot(None), Candidate.github_url != ""))
            elif status_upper == "GITHUB_NOT_FOUND":
                stmt = stmt.where(or_(Candidate.github_url.is_(None), Candidate.github_url == ""))
            elif "DETECTED" in status_upper or status_upper == "NEEDS_REVIEW":
                latest_res_ids = select(func.max(ScreeningResult.id)).group_by(ScreeningResult.candidate_id)
                if "NOT" not in status_upper and status_upper != "NEEDS_REVIEW":
                    subq = select(ScreeningResult.candidate_id).where(
                        ScreeningResult.id.in_(latest_res_ids),
                        ScreeningResult.go_status.like("%_DETECTED"),
                        ~ScreeningResult.go_status.like("%NOT_DETECTED%"),
                    )
                elif "NOT" in status_upper:
                    subq = select(ScreeningResult.candidate_id).where(
                        ScreeningResult.id.in_(latest_res_ids),
                        ScreeningResult.go_status.like("%NOT_DETECTED%"),
                    )
                else:
                    subq = select(ScreeningResult.candidate_id).where(
                        ScreeningResult.id.in_(latest_res_ids),
                        ScreeningResult.go_status.in_(["CHECK_INCOMPLETE", "API_RATE_LIMITED", "API_ERROR", "GITHUB_NOT_FOUND"]),
                    )
                stmt = stmt.where(Candidate.id.in_(subq))
            elif status_upper == "GITROLL_SCORED":
                stmt = stmt.where(Candidate.gitroll_rating.isnot(None))
            elif status_upper in ("NOTE_ADDED", "NOTE_ALREADY_EXISTS", "NOTE_EXISTED", "NOTES_EXISTED"):
                latest_note_ids = select(func.max(NoteAction.id)).group_by(NoteAction.candidate_id)
                if status_upper == "NOTE_ADDED":
                    subq = select(NoteAction.candidate_id).where(
                        NoteAction.id.in_(latest_note_ids),
                        NoteAction.action_status == "NOTE_ADDED",
                    )
                else:
                    subq = select(NoteAction.candidate_id).where(
                        NoteAction.id.in_(latest_note_ids),
                        NoteAction.action_status == "NOTE_ALREADY_EXISTS",
                    )
                stmt = stmt.where(Candidate.id.in_(subq))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        # Order and paginate
        stmt = stmt.order_by(Candidate.updated_at.desc()).limit(limit).offset(offset)
        candidates = list(self.db.execute(stmt).scalars().all())

        return candidates, total

    def get_total_count(self) -> int:
        """Return total number of candidates in database."""
        return self.db.execute(select(func.count(Candidate.id))).scalar() or 0

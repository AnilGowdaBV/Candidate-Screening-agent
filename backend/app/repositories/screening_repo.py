"""Screening repository managing runs, screening results, note actions, and events."""

from datetime import datetime, timezone
import json
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_, distinct
from sqlalchemy.orm import Session
from app.models.candidate import Candidate
from app.models.screening_run import ScreeningRun
from app.models.screening_result import ScreeningResult
from app.models.note_action import NoteAction
from app.models.activity_event import ActivityEvent


class ScreeningRepository:
    """Data access layer for runs, classifications, note actions, and activity logs."""

    def __init__(self, db: Session):
        self.db = db

    # --- Screening Runs ---
    def create_run(self, configuration_snapshot: Optional[str] = None) -> ScreeningRun:
        """Create a new screening run."""
        run = ScreeningRun(
            status="VALIDATING",
            configuration_snapshot=configuration_snapshot,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: int) -> Optional[ScreeningRun]:
        """Fetch run by ID."""
        return self.db.get(ScreeningRun, run_id)

    def list_runs(self, limit: int = 20) -> List[ScreeningRun]:
        """List past runs ordered by start time."""
        stmt = select(ScreeningRun).order_by(ScreeningRun.started_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def update_run_status(
        self,
        run_id: int,
        status: str,
        last_checkpoint: Optional[str] = None,
        processed_increment: int = 0,
        error_increment: int = 0,
        finished: bool = False,
    ) -> Optional[ScreeningRun]:
        """Update run lifecycle status, counters, and checkpoints."""
        run = self.get_run(run_id)
        if not run:
            return None

        run.status = status
        if last_checkpoint is not None:
            run.last_checkpoint = last_checkpoint
        if processed_increment > 0:
            run.processed_count += processed_increment
        if error_increment > 0:
            run.error_count += error_increment
        if finished:
            run.finished_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(run)
        return run

    # --- Screening Results ---
    def record_screening_result(
        self,
        candidate_id: int,
        run_id: int,
        github_status: str,
        go_status: str,
        evidence_summary: Optional[str] = None,
        repositories_checked: int = 0,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        languages_found: Optional[str] = None,
        search_order: Optional[int] = None,
    ) -> ScreeningResult:
        """Store the technical outcome of examining a candidate."""
        result = ScreeningResult(
            candidate_id=candidate_id,
            run_id=run_id,
            github_status=github_status,
            go_status=go_status,
            evidence_summary=evidence_summary,
            repositories_checked=repositories_checked,
            error_code=error_code,
            error_message=error_message,
            languages_found=languages_found,
            search_order=search_order,
            checked_at=datetime.now(timezone.utc),
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def find_latest_screening_result(self, candidate_id: int) -> Optional[ScreeningResult]:
        """Fetch the most recent technical classification for this candidate."""
        stmt = select(ScreeningResult).where(ScreeningResult.candidate_id == candidate_id).order_by(ScreeningResult.id.desc())
        return self.db.execute(stmt).scalars().first()

    # --- Note Actions ---
    def find_existing_successful_note(
        self, candidate_id: int, note_text: Optional[str] = None
    ) -> Optional[NoteAction]:
        """Locate any prior confirmed note action for this candidate (any note or specific note).
        Only counts as confirmed if action_status is NOTE_ADDED (no error) or NOTE_ALREADY_EXISTS.
        Unconfirmed NOTE_ADDED records (with error_message) are NOT treated as confirmed.
        """
        conditions = [
            NoteAction.candidate_id == candidate_id,
            # NOTE_ALREADY_EXISTS is always reliable (DOM check confirmed)
            # NOTE_ADDED is only reliable when error_message is NULL (DOM re-read confirmed it)
            (
                (NoteAction.action_status == "NOTE_ALREADY_EXISTS") |
                (
                    (NoteAction.action_status == "NOTE_ADDED") &
                    NoteAction.error_message.is_(None)
                )
            ),
        ]
        if note_text is not None:
            conditions.append(NoteAction.note_text == note_text)
        stmt = select(NoteAction).where(and_(*conditions))
        return self.db.execute(stmt).scalars().first()

    def record_note_action(
        self,
        candidate_id: int,
        run_id: int,
        note_text: str,
        action_status: str,
        confirmed: bool = False,
        error_message: Optional[str] = None,
    ) -> NoteAction:
        """Persist a note action attempt or confirmed write."""
        now = datetime.now(timezone.utc)
        note = NoteAction(
            candidate_id=candidate_id,
            run_id=run_id,
            note_text=note_text,
            action_status=action_status,
            attempted_at=now,
            confirmed_at=now if confirmed else None,
            error_message=error_message,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    # --- Activity Events ---
    def record_activity_event(
        self,
        event_type: str,
        message: str,
        run_id: Optional[int] = None,
        candidate_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActivityEvent:
        """Record an activity event for real-time streaming and audit persistence."""
        event = ActivityEvent(
            run_id=run_id,
            candidate_id=candidate_id,
            event_type=event_type,
            message=message,
            created_at=datetime.now(timezone.utc),
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_recent_events(
        self, limit: int = 50, run_id: Optional[int] = None
    ) -> List[ActivityEvent]:
        """Fetch latest activity events."""
        stmt = select(ActivityEvent)
        if run_id:
            stmt = stmt.where(ActivityEvent.run_id == run_id)
        stmt = stmt.order_by(ActivityEvent.created_at.desc()).limit(limit)
        events = list(self.db.execute(stmt).scalars().all())
        # Return in chronological order for UI display
        events.reverse()
        return events

    # --- Metrics Computation ---
    def get_dashboard_metrics(self, run_id: Optional[int] = None) -> Dict[str, int]:
        """
        Calculate metrics directly from database records.
        When run_id is specified: calculates metrics for that run.
        When run_id is None: calculates metrics across all unique persisted candidates.
        """
        if run_id:
            # Metrics for specific run
            cand_stmt = select(func.count(distinct(ScreeningResult.candidate_id))).where(ScreeningResult.run_id == run_id)
            candidates_discovered = self.db.execute(cand_stmt).scalar() or 0

            res_stmt = select(ScreeningResult).where(ScreeningResult.run_id == run_id)
            results = list(self.db.execute(res_stmt).scalars().all())
            processed = len(results)

            github_found = sum(1 for r in results if r.github_status == "GITHUB_FOUND")
            github_missing = sum(1 for r in results if r.github_status != "GITHUB_FOUND")

            go_detected = sum(1 for r in results if r.go_status and r.go_status.endswith("_DETECTED") and "NOT" not in r.go_status)
            go_not_detected = sum(1 for r in results if r.go_status and "NOT_DETECTED" in r.go_status)
            needing_review = sum(
                1 for r in results if r.go_status in ["CHECK_INCOMPLETE", "API_RATE_LIMITED", "API_ERROR"]
            )

            note_stmt = select(NoteAction).where(NoteAction.run_id == run_id)
            notes = list(self.db.execute(note_stmt).scalars().all())

            notes_added = sum(1 for n in notes if n.action_status == "NOTE_ADDED")
            notes_already_present = sum(1 for n in notes if n.action_status == "NOTE_ALREADY_EXISTS")
            errors = sum(1 for n in notes if n.action_status == "NOTE_FAILED") + sum(
                1 for r in results if r.error_message is not None
            )

            return {
                "candidates_discovered": candidates_discovered,
                "candidates_processed": processed,
                "candidates_remaining": 0,
                "github_profiles_found": github_found,
                "github_profiles_missing": github_missing,
                "go_detected": go_detected,
                "go_not_detected": go_not_detected,
                "notes_added": notes_added,
                "notes_already_present": notes_already_present,
                "candidates_needing_review": needing_review,
                "errors": errors,
            }

        total_candidates = self.db.scalar(select(func.count()).select_from(Candidate)) or 0
        github_found = self.db.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.github_url.is_not(None),
                Candidate.github_url != "",
            )
        ) or 0
        github_missing = max(0, total_candidates - github_found)
        processed = self.db.scalar(
            select(func.count(distinct(ScreeningResult.candidate_id)))
        ) or 0
        go_detected = self.db.scalar(
            select(func.count()).select_from(ScreeningResult).where(
                ScreeningResult.go_status.like("%_DETECTED"),
                ScreeningResult.go_status.not_like("%NOT_DETECTED"),
            )
        ) or 0
        go_not_detected = self.db.scalar(
            select(func.count()).select_from(ScreeningResult).where(
                ScreeningResult.go_status.like("%NOT_DETECTED")
            )
        ) or 0
        needing_review = self.db.scalar(
            select(func.count()).select_from(ScreeningResult).where(
                ScreeningResult.go_status.in_(["CHECK_INCOMPLETE", "API_RATE_LIMITED", "API_ERROR"])
            )
        ) or 0
        notes_added = self.db.scalar(
            select(func.count()).select_from(NoteAction).where(NoteAction.action_status == "NOTE_ADDED")
        ) or 0
        notes_already_present = self.db.scalar(
            select(func.count()).select_from(NoteAction).where(NoteAction.action_status == "NOTE_ALREADY_EXISTS")
        ) or 0
        errors = self.db.scalar(
            select(func.count()).select_from(NoteAction).where(NoteAction.action_status == "NOTE_FAILED")
        ) or 0

        return {
            "candidates_discovered": total_candidates,
            "candidates_processed": processed,
            "candidates_remaining": max(0, total_candidates - processed),
            "github_profiles_found": github_found,
            "github_profiles_missing": github_missing,
            "go_detected": go_detected,
            "go_not_detected": go_not_detected,
            "notes_added": notes_added,
            "notes_already_present": notes_already_present,
            "candidates_needing_review": needing_review,
            "errors": errors,
        }

"""Note decision service enforcing exact candidate note rules and duplicate safety guardrails."""

import asyncio
from typing import Optional, Tuple, List
from pydantic import BaseModel
from app.core.logging import get_logger
from app.repositories.screening_repo import ScreeningRepository
from app.browser.browser_manager import PlaywrightBrowserManager

logger = get_logger("notes_service")

NOTE_RULE_A = "No GitHub found"
NOTE_RULE_B = "Go lang not found"
NOTE_RULE_C = "Go lang found"

TECHNOLOGY_NOTE_MAP = {
    "golang": {
        "found": "Go lang found",
        "not_found": "Go lang not found",
        "status_detected": "GO_DETECTED",
        "status_not_detected": "GO_NOT_DETECTED",
    },
    "python": {
        "found": "Python found",
        "not_found": "Python not found",
        "status_detected": "PYTHON_DETECTED",
        "status_not_detected": "PYTHON_NOT_DETECTED",
    },
    "java": {
        "found": "Java found",
        "not_found": "Java not found",
        "status_detected": "JAVA_DETECTED",
        "status_not_detected": "JAVA_NOT_DETECTED",
    },
    "javascript": {
        "found": "JavaScript found",
        "not_found": "JavaScript not found",
        "status_detected": "JAVASCRIPT_DETECTED",
        "status_not_detected": "JAVASCRIPT_NOT_DETECTED",
    },
    "typescript": {
        "found": "TypeScript found",
        "not_found": "TypeScript not found",
        "status_detected": "TYPESCRIPT_DETECTED",
        "status_not_detected": "TYPESCRIPT_NOT_DETECTED",
    },
    "frontend": {
        "found": "Frontend Development found",
        "not_found": "Frontend Development not found",
        "status_detected": "FRONTEND_DETECTED",
        "status_not_detected": "FRONTEND_NOT_DETECTED",
    },
    "qa_automation": {
        "found": "QA Automation found",
        "not_found": "QA Automation not found",
        "status_detected": "QA_AUTOMATION_DETECTED",
        "status_not_detected": "QA_AUTOMATION_NOT_DETECTED",
    },
    "qa": {
        "found": "QA Automation found",
        "not_found": "QA Automation not found",
        "status_detected": "QA_AUTOMATION_DETECTED",
        "status_not_detected": "QA_AUTOMATION_NOT_DETECTED",
    },
}


class NoteActionOutcome(BaseModel):
    """Result of evaluating and executing a note action."""
    note_text: Optional[str] = None
    action_status: str  # NOTE_ADDED, NOTE_ALREADY_EXISTS, NOTE_FAILED, NOTE_OUTCOME_UNKNOWN, SKIPPED, NO_ACTION
    confirmed: bool = False
    reason: str
    error_message: Optional[str] = None


class NotesService:
    """Evaluates screening outcome and safely enforces duplicate prevention and save confirmation."""

    @staticmethod
    def evaluate_note_rule(
        github_status: str,
        tech_status: Optional[str] = None,
        technology: str = "golang",
        go_status: Optional[str] = None,
    ) -> Tuple[Optional[str], str]:
        """
        Determine exact note rule to apply based on screening verification:
        - Rule A: No GitHub profile -> 'No GitHub found'
        - Rule B: GitHub found, target language not detected -> '<Tech> not found'
        - Rule C: Target language detected -> '<Tech> found'
        - Rule D: Incomplete or uncertain check -> No note added. Mark for manual review.

        Returns (note_text: Optional[str], decision_reason: str).
        """
        effective_tech_status = tech_status or go_status or ""
        tech = technology.lower() if technology else "golang"
        t_spec = TECHNOLOGY_NOTE_MAP.get(tech, TECHNOLOGY_NOTE_MAP["golang"])
        note_found = t_spec["found"]
        note_not_found = t_spec["not_found"]
        status_det = t_spec["status_detected"]
        status_not_det = t_spec["status_not_detected"]

        # Rule D: Incomplete or uncertain checks
        if effective_tech_status in ("CHECK_INCOMPLETE", "API_RATE_LIMITED", "API_ERROR"):
            return None, f"Check incomplete or error ({effective_tech_status}); marked for manual review, no note added"

        # Rule A: No GitHub profile
        if github_status == "GITHUB_NOT_FOUND" or effective_tech_status == "GITHUB_NOT_FOUND":
            return NOTE_RULE_A, "Rule A: No identifiable GitHub profile URL found"

        # Rule C: Target language detected
        if effective_tech_status == status_det:
            return note_found, f"Rule C: Reliable {tech} evidence detected; note '{note_found}' applied"

        # Rule B: GitHub found, target language not detected
        if effective_tech_status == status_not_det:
            return note_not_found, f"Rule B: GitHub profile checked but no {tech} evidence detected"

        # Fallback default
        return None, f"Uncertain status ({effective_tech_status}); routed to manual review"

    @classmethod
    async def process_candidate_note(
        cls,
        candidate_id: int,
        run_id: int,
        github_status: str,
        go_status: str,
        dry_run: bool,
        screen_repo: ScreeningRepository,
        browser_manager: Optional[PlaywrightBrowserManager] = None,
        technology: str = "golang",
    ) -> NoteActionOutcome:
        """
        Full guardrail flow:
        1. Determine exact note string based on Rules A, B, C, D for selected technology.
        2. If no note required, return NO_ACTION.
        3. Pre-write check against SQLite database for existing notes.
        4. If dry_run=True, persist SKIPPED and return.
        5. Pre-write check against Instahyre profile DOM.
        6. Live write with post-write confirmation.
        7. If write outcome is ambiguous, re-verify existing notes before returning.
        """
        # 1. Evaluate Rule
        note_text, rule_reason = cls.evaluate_note_rule(github_status, go_status, technology=technology)
        if not note_text:
            return NoteActionOutcome(
                note_text=None,
                action_status="NO_ACTION",
                confirmed=False,
                reason=rule_reason,
            )

        # 2. Pre-write Check: SQLite Database (Candidate must never receive more than one note)
        prior_note = screen_repo.find_existing_successful_note(candidate_id)
        if prior_note:
            logger.info("Candidate #%d already has note '%s' in SQLite. Will not touch candidate.", candidate_id, prior_note.note_text)
            screen_repo.record_note_action(
                candidate_id=candidate_id,
                run_id=run_id,
                note_text=prior_note.note_text,
                action_status="NOTE_ALREADY_EXISTS",
                confirmed=True,
            )
            return NoteActionOutcome(
                note_text=prior_note.note_text,
                action_status="NOTE_ALREADY_EXISTS",
                confirmed=True,
                reason=f"Candidate already has screening note '{prior_note.note_text}' recorded in SQLite database. Never adding a second note.",
            )

        # 3. Dry-Run Handling
        if dry_run or not browser_manager:
            logger.info("[DRY RUN] Proposing note '%s' for candidate #%d. Skipped external write.", note_text, candidate_id)
            screen_repo.record_note_action(
                candidate_id=candidate_id,
                run_id=run_id,
                note_text=note_text,
                action_status="SKIPPED",
                confirmed=False,
                error_message="Dry run mode enabled; live write prevented",
            )
            return NoteActionOutcome(
                note_text=note_text,
                action_status="SKIPPED",
                confirmed=False,
                reason="Dry run mode active; proposed note recorded without modifying Instahyre",
            )

        # 4. Pre-write Check: Profile DOM Notes (Check if ANY screening note already exists on Instahyre)
        SCREENING_PHRASES = ["no github found", "go lang not found", "go lang found"]
        try:
            existing_dom_notes = await browser_manager.get_existing_notes()
            for dom_n in existing_dom_notes:
                dom_n_lower = dom_n.lower()
                for phrase in SCREENING_PHRASES:
                    if phrase in dom_n_lower:
                        logger.info("Candidate already has screening note '%s' on Instahyre profile. Skipping write.", phrase)
                        screen_repo.record_note_action(
                            candidate_id=candidate_id,
                            run_id=run_id,
                            note_text=note_text,
                            action_status="NOTE_ALREADY_EXISTS",
                            confirmed=True,
                        )
                        return NoteActionOutcome(
                            note_text=note_text,
                            action_status="NOTE_ALREADY_EXISTS",
                            confirmed=True,
                            reason=f"Screening note '{phrase}' already exists on candidate's Instahyre profile. Never adding another note.",
                        )
        except Exception as dom_err:
            logger.warning("Could not read DOM notes prior to write: %s", dom_err)

        # 5. Live Note Write & Confirmation. One retry covers Instahyre timeouts
        # where the note click succeeds but the notes list has not refreshed yet.
        write_status, err = await browser_manager.write_note(note_text, dry_run=False)
        if write_status == "RATE_LIMITED":
            logger.warning(
                "Instahyre note quota limit reached for candidate #%d ('%s'): %s. Note queued.",
                candidate_id,
                note_text,
                err,
            )
        elif write_status == "NOTE_FAILED":
            logger.warning(
                "Note write failed for candidate #%d ('%s'). Retrying once.",
                candidate_id,
                note_text,
            )
            await asyncio.sleep(2)
            write_status, err = await browser_manager.write_note(note_text, dry_run=False)

        # 6. Ambiguous Outcome Recovery: NOTE_OUTCOME_UNKNOWN → recheck DOM one more time
        if write_status == "NOTE_OUTCOME_UNKNOWN":
            logger.warning("Note write outcome uncertain. Rechecking Instahyre profile notes...")
            try:
                recheck_notes = await browser_manager.get_existing_notes()
                if any(note_text.strip().lower() in n.lower() for n in recheck_notes):
                    write_status = "NOTE_ADDED"
                    err = None
                    logger.info("Recheck confirmed note '%s' was indeed saved!", note_text)
                else:
                    write_status = "NOTE_FAILED"
                    err = err or "Note not detected on Instahyre profile after ambiguous write"
            except Exception:
                write_status = "NOTE_FAILED"

        # 7. NOTE_FAILED = note was NOT saved. Record it so next run can retry.
        confirmed = write_status == "NOTE_ADDED"

        screen_repo.record_note_action(
            candidate_id=candidate_id,
            run_id=run_id,
            note_text=note_text,
            action_status=write_status,
            confirmed=confirmed,
            error_message=err,
        )

        return NoteActionOutcome(
            note_text=note_text,
            action_status=write_status,
            confirmed=confirmed,
            reason=f"External write completed with status: {write_status}",
            error_message=err,
        )


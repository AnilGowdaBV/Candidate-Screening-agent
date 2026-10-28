import asyncio
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.candidate import Candidate
from app.models.note_action import NoteAction
from app.services.gitroll_service import GitRollService
from app.browser.browser_manager import PlaywrightBrowserManager

logger = get_logger("gitroll_scan_manager")


class GitRollScanManager:
    """Coordinates GitRoll score fetching and exact Instahyre note additions."""

    def __init__(self, browser_manager: Optional[PlaywrightBrowserManager] = None):
        self.browser_manager = browser_manager

    async def scan_candidate(
        self,
        candidate_id: int,
        db: Session,
        add_instahyre_note: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Scan a candidate's GitHub repositories on GitRoll and optionally add the rating note to Instahyre.

        Exact Note Rule:
        Format: 'Overall Rating: <Grade> <Score>' (e.g. 'Overall Rating: C 4.20' or 'Overall Rating: B 5.18')
        Strict safety: Never duplicates or overwrites existing notes ('Go lang found', recruiter notes, etc.).
        """
        cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not cand:
            return {"success": False, "error": f"Candidate #{candidate_id} not found in database"}

        if not cand.github_url:
            return {"success": False, "error": f"Candidate {cand.name} (#{candidate_id}) has no GitHub profile URL recorded"}

        logger.info("Initiating GitRoll rating scan for candidate %s (#%d): %s", cand.name, cand.id, cand.github_url)

        # 1. Fetch rating from GitRoll
        gitroll_res = await GitRollService.fetch_rating(cand.github_url)
        if not gitroll_res["success"]:
            logger.warning("GitRoll scan in progress / pending for %s: %s", cand.name, gitroll_res.get("error"))
            err = str(gitroll_res.get("error", "")).lower()
            if "404" in err or "user not found" in err:
                cand.gitroll_grade = "N/A"
                cand.gitroll_note_status = "NO_RATING_AVAILABLE"
            else:
                cand.gitroll_grade = "Pending Scan"
                cand.gitroll_note_status = "PENDING_SCAN"
            cand.gitroll_profile_url = gitroll_res.get("profile_url")
            cand.gitroll_scanned_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "success": False,
                "candidate_id": cand.id,
                "candidate_name": cand.name,
                "github_url": cand.github_url,
                "profile_url": gitroll_res.get("profile_url"),
                "gitroll_grade": cand.gitroll_grade,
                "note_status": cand.gitroll_note_status,
                "error": gitroll_res.get("error") or "GitRoll scan in progress",
            }

        # 2. Update Candidate record in SQLite
        cand.gitroll_rating = gitroll_res["score"]
        cand.gitroll_grade = gitroll_res["grade"]
        cand.gitroll_profile_url = gitroll_res["profile_url"]
        cand.gitroll_scanned_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cand)

        logger.info(
            "Candidate %s (#%d) GitRoll assessment stored: Grade=%s, Score=%.2f, Profile=%s",
            cand.name, cand.id, cand.gitroll_grade, cand.gitroll_rating, cand.gitroll_profile_url
        )

        note_text = gitroll_res["note_text"]
        result_payload = {
            "success": True,
            "candidate_id": cand.id,
            "candidate_name": cand.name,
            "github_url": cand.github_url,
            "gitroll_rating": cand.gitroll_rating,
            "gitroll_grade": cand.gitroll_grade,
            "gitroll_profile_url": cand.gitroll_profile_url,
            "note_text": note_text,
            "note_status": cand.gitroll_note_status or "NOT_REQUESTED",
            "error": None,
        }

        # If user did not request adding Instahyre note, return early
        if not add_instahyre_note:
            return result_payload

        # 3. Add Instahyre Note with 100% duplicate protection
        logger.info("Preparing to add Instahyre note for %s: '%s'", cand.name, note_text)

        # Pre-check SQLite: candidate already has this exact note
        existing_action = (
            db.query(NoteAction)
            .filter(
                NoteAction.candidate_id == cand.id,
                NoteAction.note_text.like("Overall Rating:%"),
                NoteAction.action_status == "NOTE_ADDED",
            )
            .first()
        )
        if existing_action or cand.gitroll_note_status == "NOTE_ADDED":
            logger.info("Candidate %s already has GitRoll note recorded in database. Skipping duplicate note write.", cand.name)
            result_payload["note_status"] = "NOTE_ALREADY_EXISTS"
            return result_payload

        # Pre-check Dry-Run
        if dry_run:
            logger.info("[DRY RUN] Would write note '%s' to Instahyre for %s. Skipping.", note_text, cand.name)
            cand.gitroll_note_status = "SKIPPED_DRY_RUN"
            db.commit()
            result_payload["note_status"] = "SKIPPED_DRY_RUN"
            return result_payload

        # Browser Automation Write
        if not self.browser_manager:
            self.browser_manager = PlaywrightBrowserManager()
            await self.browser_manager.initialize()

        assert self.browser_manager.page is not None
        try:
            # Navigate to candidate's Instahyre profile
            logger.info("Navigating to candidate Instahyre profile: %s", cand.instahyre_profile_url)
            await self.browser_manager.page.goto(cand.instahyre_profile_url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2)

            # Extract and persist candidate current salary if available on profile
            if not cand.current_salary:
                try:
                    content = await self.browser_manager.page.content()
                    sal_match = re.search(r"(?:Current\s*salary|Salary|CTC)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([\d\.]+\s*(?:lpa|LPA|L|lakhs?))", content, re.IGNORECASE)
                    if sal_match:
                        val = sal_match.group(1).strip().upper()
                        if not val.startswith("₹"):
                            val = f"₹ {val}"
                        cand.current_salary = val
                        db.commit()
                        logger.info("Discovered and saved current salary for %s: %s", cand.name, val)
                except Exception as sal_err:
                    logger.debug("Salary extraction note: %s", sal_err)

            # Check existing notes on DOM before writing
            existing_notes = await self.browser_manager.get_existing_notes()
            for ext in existing_notes:
                if "overall rating:" in ext.lower():
                    logger.info("Candidate profile already contains an 'Overall Rating:' note in DOM. Aborting write to prevent duplicate.")
                    cand.gitroll_note_status = "NOTE_ALREADY_EXISTS"
                    db.commit()
                    result_payload["note_status"] = "NOTE_ALREADY_EXISTS"
                    return result_payload

            # Write note
            write_status, err = await self.browser_manager.write_note(note_text, dry_run=False)
            logger.info("Instahyre note write completed for %s with status: %s (err: %s)", cand.name, write_status, err)

            cand.gitroll_note_status = write_status
            db.commit()

            # Record in NoteAction table for auditing
            active_run_id = cand.screening_results[0].run_id if cand.screening_results else 11
            note_action = NoteAction(
                candidate_id=cand.id,
                run_id=active_run_id,
                note_text=note_text,
                action_status=write_status,
                confirmed_at=datetime.now(timezone.utc) if write_status == "NOTE_ADDED" else None,
                error_message=err,
            )
            db.add(note_action)
            db.commit()

            result_payload["note_status"] = write_status
            if write_status != "NOTE_ADDED":
                result_payload["error"] = err or f"Note write finished with status: {write_status}"

            return result_payload

        except Exception as exc:
            logger.error("Exception during Instahyre note write for %s: %s", cand.name, exc, exc_info=True)
            cand.gitroll_note_status = "NOTE_FAILED"
            db.commit()
            result_payload["note_status"] = "NOTE_FAILED"
            result_payload["error"] = str(exc)
            return result_payload
        finally:
            if self.browser_manager:
                try:
                    await self.browser_manager.close()
                except Exception:
                    pass
                self.browser_manager = None

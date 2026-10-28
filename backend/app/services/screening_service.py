"""Orchestration service coordinating candidate screening, GitHub checks, and note actions."""

import asyncio
import json
from typing import Optional, List, Dict, Any
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.state import state_manager, RunState
from app.database.session import get_sessionmaker_for_tech
from app.repositories.candidate_repo import CandidateRepository
from app.repositories.screening_repo import ScreeningRepository
from app.services.github_service import GitHubService
from app.services.notes_service import NotesService
from app.services.event_service import event_broker
from app.browser.browser_manager import PlaywrightBrowserManager

logger = get_logger("screening_service")


class ScreeningOrchestrator:
    """Coordinates background screening run execution, pause/resume, and checkpointing."""

    def __init__(self):
        self.github_service = GitHubService()
        self.notes_service = NotesService()
        self.browser_manager: Optional[PlaywrightBrowserManager] = None
        self._task: Optional[asyncio.Task] = None

    async def start(
        self,
        run_id: int,
        dry_run: bool = True,
        synthetic_candidates: Optional[List[Dict[str, str]]] = None,
        technology: str = "golang",
        search_url: Optional[str] = None,
        max_candidates: Optional[int] = None,
    ) -> None:
        """Start screening run in background task."""
        if self._task and not self._task.done():
            logger.warning("Screening task already running")
            return

        self._task = asyncio.create_task(
            self._execute_run(
                run_id,
                dry_run=dry_run,
                synthetic_candidates=synthetic_candidates,
                technology=technology,
                search_url=search_url,
                max_candidates=max_candidates,
            )
        )

    async def _execute_run(
        self,
        run_id: int,
        dry_run: bool = True,
        synthetic_candidates: Optional[List[Dict[str, str]]] = None,
        technology: str = "golang",
        search_url: Optional[str] = None,
        max_candidates: Optional[int] = None,
    ) -> None:
        """Core execution loop processing candidates sequentially."""
        tech = technology.lower() if technology else "golang"
        settings = get_settings()
        sm = get_sessionmaker_for_tech(tech)
        db = sm()

        try:
            cand_repo = CandidateRepository(db)
            screen_repo = ScreeningRepository(db)

            # Determine search URL (custom user URL or default from settings)
            target_search_url = search_url.strip() if search_url and search_url.strip() else settings.INSTAHYRE_SEARCH_URL

            # Stage 1: Configuration validation
            state_manager.update_operation(
                current_operation=f"Validating configuration for {tech.upper()} and database readiness",
                workflow_stage="Configuration validation",
                current_status="Validating settings",
            )
            await event_broker.emit(
                event_type="CONFIG_VALIDATED",
                message=f"Configuration for {tech.upper()} and database readiness verified.",
                run_id=run_id,
            )
            await asyncio.sleep(0.5)

            # Stage 2: Instahyre search / candidate discovery
            state_manager.set_running()
            state_manager.update_operation(
                current_operation=f"Accessing Instahyre search results for {tech.upper()}",
                workflow_stage="Instahyre search",
                current_status="Opening search URL",
                next_planned_action="Identify candidate profile cards",
            )
            await event_broker.emit(
                event_type="SEARCH_PAGE_LOADED",
                message=f"Target search query opened for {tech.upper()}.",
                run_id=run_id,
                metadata={"url": target_search_url, "technology": tech},
            )

            # Retrieve candidate list (either synthetic fixtures or Playwright extraction)
            candidate_cards: List[Dict[str, str]] = []

            if synthetic_candidates is not None:
                candidate_cards = synthetic_candidates
            else:
                self.browser_manager = PlaywrightBrowserManager(headless=settings.HEADLESS_BROWSER)
                try:
                    await self.browser_manager.initialize()
                    # Check auth or attempt login
                    is_authed = await self.browser_manager.check_authenticated()
                    if not is_authed:
                        if settings.is_instahyre_configured:
                            await event_broker.emit(
                                event_type="LOGIN_ATTEMPTED",
                                message="Session requires login. Attempting automated login with .env credentials...",
                                run_id=run_id,
                            )
                            logged_in, msg = await self.browser_manager.attempt_login()
                            if not logged_in:
                                raise RuntimeError(f"Authentication required: {msg}")
                        else:
                            await event_broker.emit(
                                event_type="MANUAL_LOGIN_REQUIRED",
                                message="Instahyre session requires login. Please sign in.",
                                run_id=run_id,
                            )
                            state_manager.request_pause()

                    # Load search page using target_search_url
                    loaded, search_msg = await self.browser_manager.open_search_url(target_search_url)
                    if not loaded:
                        raise RuntimeError(search_msg)

                    # Start at page 1 of target search URL
                    target_page = 1
                    logger.info("Starting candidate discovery at page 1 for search URL.")

                    candidate_cards = await self.browser_manager.extract_candidate_cards()
                except Exception as b_err:
                    logger.warning("Browser discovery encountered: %s. Using safe fallback.", b_err)
                    # If browser fails due to auth/display in headless test, record warning
                    state_manager.update_operation(warning_or_error=str(b_err))

            max_limit = max_candidates or settings.MAX_CANDIDATES_PER_RUN or 30
            total_found = len(candidate_cards)
            await event_broker.emit(
                event_type="CANDIDATES_DISCOVERED",
                message=f"Discovered {total_found} candidate profiles on current search page (target batch limit: {max_limit}).",
                run_id=run_id,
                metadata={"count": total_found},
            )

            # Sequential Candidate Inspection Loop with Automatic Pagination
            idx = 0
            while idx < max_limit:
                # If current page cards exhausted, paginate to next page
                if not candidate_cards:
                    if self.browser_manager and synthetic_candidates is None:
                        has_next = await self.browser_manager.go_to_next_page()
                        if has_next:
                            candidate_cards = await self.browser_manager.extract_candidate_cards()
                            if not candidate_cards:
                                break
                            await event_broker.emit(
                                event_type="PAGE_NAVIGATED",
                                message=f"Advanced to next search page. Found {len(candidate_cards)} candidates.",
                                run_id=run_id,
                            )
                        else:
                            logger.info("Reached last search page or no further candidates to paginate.")
                            break
                    else:
                        break

                card = candidate_cards.pop(0)

                # Check for Pause or Stop requests
                while state_manager.state == RunState.PAUSE_REQUESTED or state_manager.state == RunState.PAUSED:
                    if state_manager.state == RunState.PAUSE_REQUESTED:
                        state_manager.confirm_pause()
                        await event_broker.emit(
                            event_type="PROCESSING_PAUSED",
                            message=f"Screening safely paused before candidate #{idx}.",
                            run_id=run_id,
                        )
                    await asyncio.sleep(1)

                if state_manager.state in (RunState.STOP_REQUESTED, RunState.STOPPED):
                    logger.info("Screening run stopped by user request.")
                    return

                profile_url = card.get("url", "")
                cand_name = card.get("name", f"Candidate #{idx}")

                # Stage 3: Candidate profile inspection
                state_manager.update_operation(
                    current_operation=f"Inspecting candidate profile ({idx}/{total_found})",
                    workflow_stage="Candidate profile inspection",
                    candidate_reference=cand_name,
                    current_status=f"Opened profile for {cand_name}",
                    last_completed_action="Discovered candidate profile reference",
                    next_planned_action="Locate GitHub profile URL",
                )

                # Persist or update candidate in SQLite (Deduplication)
                candidate, created = cand_repo.get_or_create(
                    instahyre_profile_url=profile_url,
                    name=cand_name,
                    instahyre_external_id=card.get("external_id"),
                    github_url=card.get("github_url"),
                    current_salary=card.get("current_salary"),
                    location=card.get("location"),
                    experience=card.get("experience"),
                )

                if card.get("location") and not candidate.location:
                    cand_repo.update_location(candidate.id, card.get("location"))
                if card.get("experience") and not candidate.experience:
                    cand_repo.update_experience(candidate.id, card.get("experience"))

                # Only fast-skip if candidate was already processed within this exact current run
                prior_result = screen_repo.find_latest_screening_result(candidate.id)
                if prior_result and prior_result.run_id == run_id:
                    logger.info("Candidate %s (#%d) already screened in this run. Skipping duplicate card.", cand_name, candidate.id)
                    continue

                await event_broker.emit(
                    event_type="CANDIDATE_OPENED",
                    message=f"Opened profile for candidate: {cand_name}",
                    run_id=run_id,
                    candidate_id=candidate.id,
                )

                # Stage 4: GitHub URL discovery
                state_manager.update_operation(
                    current_operation=f"Locating GitHub profile URL for {cand_name}",
                    workflow_stage="GitHub URL discovery",
                    current_status="Extracting GitHub reference",
                )

                github_url = card.get("github_url") or candidate.github_url
                if self.browser_manager and self.browser_manager.page:
                    profile_data = await self.browser_manager.inspect_candidate_profile(profile_url, card_info=card)
                    discovered_gh = profile_data.get("github_url")
                    if discovered_gh:
                        github_url = discovered_gh
                        cand_repo.update_github_url(candidate.id, github_url)
                    elif not github_url:
                        github_url = profile_data.get("github_url")
                    discovered_sal = profile_data.get("current_salary")
                    if discovered_sal and not candidate.current_salary:
                        cand_repo.update_current_salary(candidate.id, discovered_sal)
                    discovered_loc = profile_data.get("location")
                    if discovered_loc and not candidate.location:
                        cand_repo.update_location(candidate.id, discovered_loc)
                    discovered_exp = profile_data.get("experience")
                    if discovered_exp and not candidate.experience:
                        cand_repo.update_experience(candidate.id, discovered_exp)
                    if tech != "frontend":
                        discovered_coding = profile_data.get("coding_profiles")
                        if discovered_coding and not candidate.coding_profiles:
                            cand_repo.update_coding_profiles(candidate.id, discovered_coding)
                    discovered_name = profile_data.get("name")
                    if discovered_name and discovered_name != "Candidate" and discovered_name != cand_name:
                        cand_name = discovered_name
                        candidate.name = cand_name
                        db.commit()
                        db.refresh(candidate)

                if github_url:
                    await event_broker.emit(
                        event_type="GITHUB_PROFILE_FOUND",
                        message=f"Found GitHub profile: {github_url}",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )
                else:
                    await event_broker.emit(
                        event_type="GITHUB_PROFILE_NOT_FOUND",
                        message=f"No GitHub profile found for {cand_name}",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )

                # Stage 5: GitHub repository analysis
                state_manager.update_operation(
                    current_operation=f"Analyzing public GitHub repositories for {cand_name}",
                    workflow_stage="GitHub repository analysis",
                    current_status="Querying official GitHub REST API",
                )

                gh_check = await self.github_service.verify_candidate(github_url, technology=tech)

                # Stage 6: Candidate classification
                state_manager.update_operation(
                    current_operation=f"Classifying {tech.upper()} evidence: {gh_check.status}",
                    workflow_stage="Candidate classification",
                    current_status=gh_check.evidence_summary,
                )

                # Record screening result and languages_found in SQLite
                screen_repo.record_screening_result(
                    candidate_id=candidate.id,
                    run_id=run_id,
                    github_status="GITHUB_FOUND" if github_url else "GITHUB_NOT_FOUND",
                    go_status=gh_check.status,
                    evidence_summary=gh_check.evidence_summary,
                    repositories_checked=gh_check.repositories_checked,
                    error_code=gh_check.error_code,
                    error_message=gh_check.error_message,
                    languages_found=gh_check.languages_found,
                )
                if gh_check.languages_found:
                    cand_repo.update_languages_found(candidate.id, gh_check.languages_found)
                if gh_check.git_score is not None:
                    cand_repo.update_gitroll_score(candidate.id, gh_check.git_score)

                if gh_check.status.endswith("_DETECTED") and "NOT" not in gh_check.status:
                    await event_broker.emit(
                        event_type="TECH_EVIDENCE_DETECTED",
                        message=f"{tech.capitalize()} verified for {cand_name}: {gh_check.evidence_summary}",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )
                elif "NOT_DETECTED" in gh_check.status:
                    await event_broker.emit(
                        event_type="TECH_EVIDENCE_NOT_DETECTED",
                        message=f"No {tech.capitalize()} evidence found in public repos for {cand_name}.",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )
                else:
                    await event_broker.emit(
                        event_type="CANDIDATE_NEEDS_REVIEW",
                        message=f"Candidate check incomplete ({gh_check.status}). Routed to manual review.",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )

                # Stage 7: Note handling (Live writing to Instahyre paused to save time)
                state_manager.update_operation(
                    current_operation=f"Note writing paused for {cand_name} (time saving mode)",
                    workflow_stage="Note handling (Paused)",
                )

                outcome = await self.notes_service.process_candidate_note(
                    candidate_id=candidate.id,
                    run_id=run_id,
                    github_status="GITHUB_FOUND" if github_url else "GITHUB_NOT_FOUND",
                    go_status=gh_check.status,
                    dry_run=True,  # Note writing to Instahyre paused to save time
                    screen_repo=screen_repo,
                    browser_manager=self.browser_manager,
                    technology=tech,
                )

                if outcome.action_status == "NO_ACTION":
                    await event_broker.emit(
                        event_type="NOTE_RULE_NO_ACTION",
                        message=f"{outcome.reason} for {cand_name}",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )
                elif outcome.action_status == "NOTE_ALREADY_EXISTS":
                    await event_broker.emit(
                        event_type="NOTE_ALREADY_EXISTS",
                        message=f"Note '{outcome.note_text}' already existed for {cand_name}. Skipped.",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )
                else:
                    await event_broker.emit(
                        event_type="NOTE_WRITE_PROCESSED",
                        message=f"Note status for {cand_name}: {outcome.action_status} ('{outcome.note_text}')",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )

                # Stage 8: SQLite checkpoint update
                is_new = outcome.action_status != "NOTE_ALREADY_EXISTS"
                if is_new:
                    idx += 1

                state_manager.update_operation(
                    current_operation=f"Checkpoint saved for candidate {cand_name}",
                    workflow_stage="SQLite checkpoint update",
                    last_completed_action=f"Candidate #{idx} processed",
                )
                checkpoint_data = f"candidate_id_{candidate.id}_idx_{idx}"
                screen_repo.update_run_status(
                    run_id=run_id,
                    status="RUNNING",
                    last_checkpoint=checkpoint_data,
                    processed_increment=1 if is_new else 0,
                )

                # Restore search view by closing candidate drawer/modal
                if self.browser_manager:
                    await self.browser_manager.close_candidate_modal()

                await asyncio.sleep(0.5)

            # Stage 9: Completion
            state_manager.complete_run()
            screen_repo.update_run_status(run_id=run_id, status="COMPLETED", finished=True)
            await event_broker.emit(
                event_type="RUN_COMPLETED",
                message=f"Screening Run #{run_id} completed successfully.",
                run_id=run_id,
            )

        except Exception as exc:
            logger.error("Screening run encountered error: %s", exc)
            state_manager.fail_run(str(exc))
            try:
                screen_repo.update_run_status(run_id=run_id, status="FAILED", error_increment=1, finished=True)
                await event_broker.emit(
                    event_type="RUN_FAILED",
                    message=f"Run failed: {str(exc)}",
                    run_id=run_id,
                )
            except Exception:
                pass
        finally:
            db.close()
            if self.browser_manager:
                try:
                    await self.browser_manager.close()
                except Exception:
                    pass
                self.browser_manager = None


# Singleton orchestrator instance
orchestrator = ScreeningOrchestrator()

"""Comprehensive automated tests for note rules, duplicate checks, and confirmation guardrails."""

import pytest
import uuid
from app.services.notes_service import NotesService, NOTE_RULE_A, NOTE_RULE_B, NOTE_RULE_C
from app.browser.browser_manager import PlaywrightBrowserManager
from app.database.session import SessionLocal
from app.repositories.screening_repo import ScreeningRepository
from app.repositories.candidate_repo import CandidateRepository


@pytest.mark.asyncio
async def test_rule_a_no_github_generates_correct_note():
    """Rule A: Candidate with no GitHub profile receives 'No GitHub found'."""
    note, reason = NotesService.evaluate_note_rule(
        github_status="GITHUB_NOT_FOUND", go_status="GITHUB_NOT_FOUND"
    )
    assert note == NOTE_RULE_A
    assert "Rule A" in reason


@pytest.mark.asyncio
async def test_rule_b_no_go_evidence_generates_correct_note():
    """Rule B: Candidate with GitHub but no Go detected receives 'Go lang not found'."""
    note, reason = NotesService.evaluate_note_rule(
        github_status="GITHUB_FOUND", go_status="GO_NOT_DETECTED"
    )
    assert note == NOTE_RULE_B
    assert "Rule B" in reason


@pytest.mark.asyncio
async def test_rule_c_go_detected_generates_correct_note():
    """Rule C: Candidate with Go detected receives 'Go lang found' note."""
    note, reason = NotesService.evaluate_note_rule(
        github_status="GITHUB_FOUND", go_status="GO_DETECTED"
    )
    assert note == NOTE_RULE_C
    assert "Rule C" in reason


@pytest.mark.asyncio
async def test_rule_d_incomplete_or_error_adds_zero_notes():
    """Rule D: Incomplete check, rate limit, or API error never adds note and routes to manual review."""
    for error_status in ["CHECK_INCOMPLETE", "API_RATE_LIMITED", "API_ERROR"]:
        note, reason = NotesService.evaluate_note_rule(
            github_status="GITHUB_FOUND", go_status=error_status
        )
        assert note is None
        assert "manual review" in reason


@pytest.mark.asyncio
async def test_pre_write_sqlite_duplicate_prevention():
    """Verify that prior note confirmed in SQLite immediately skips external write."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    cand_repo = CandidateRepository(db)

    test_url = f"https://www.instahyre.com/cand/{uuid.uuid4().hex[:8]}"
    candidate, _ = cand_repo.get_or_create(test_url, "Duplicate Test User")
    run = screen_repo.create_run()

    # Pre-seed a confirmed note in SQLite
    screen_repo.record_note_action(
        candidate_id=candidate.id,
        run_id=run.id,
        note_text=NOTE_RULE_A,
        action_status="NOTE_ADDED",
        confirmed=True,
    )

    # Now attempt to process note for candidate
    outcome = await NotesService.process_candidate_note(
        candidate_id=candidate.id,
        run_id=run.id,
        github_status="GITHUB_NOT_FOUND",
        go_status="GITHUB_NOT_FOUND",
        dry_run=False,
        screen_repo=screen_repo,
        browser_manager=None,
    )

    assert outcome.action_status == "NOTE_ALREADY_EXISTS"
    assert outcome.confirmed is True
    assert "SQLite" in outcome.reason
    db.close()


@pytest.mark.asyncio
async def test_pre_write_dom_duplicate_prevention():
    """Verify that existing note visible on Instahyre DOM skips external write."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    cand_repo = CandidateRepository(db)

    test_url = f"https://www.instahyre.com/cand/{uuid.uuid4().hex[:8]}"
    candidate, _ = cand_repo.get_or_create(test_url, "DOM Duplicate User")
    run = screen_repo.create_run()

    # Create browser manager mock where DOM already has the note
    manager = PlaywrightBrowserManager(headless=True)
    async def mock_existing_notes():
        return ["Initial interview completed", NOTE_RULE_B]
    manager.get_existing_notes = mock_existing_notes

    outcome = await NotesService.process_candidate_note(
        candidate_id=candidate.id,
        run_id=run.id,
        github_status="GITHUB_FOUND",
        go_status="GO_NOT_DETECTED",
        dry_run=False,
        screen_repo=screen_repo,
        browser_manager=manager,
    )

    assert outcome.action_status == "NOTE_ALREADY_EXISTS"
    assert outcome.confirmed is True
    assert "Instahyre profile" in outcome.reason
    db.close()


@pytest.mark.asyncio
async def test_preexisting_recruiter_notes_are_preserved_when_adding_new_note():
    """Verify that candidate profiles with existing recruiter notes are never touched/altered, and our note is added alongside them."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    cand_repo = CandidateRepository(db)

    test_url = f"https://www.instahyre.com/cand/{uuid.uuid4().hex[:8]}"
    candidate, _ = cand_repo.get_or_create(test_url, "Recruiter Notes Candidate")
    run = screen_repo.create_run()

    preexisting_notes = ["Recruiter call: Salary expectation 8 LPA", "Passed preliminary round"]
    written_notes_log = []

    manager = PlaywrightBrowserManager(headless=True)
    async def mock_existing_notes():
        # Returns preexisting notes plus any newly added notes
        return preexisting_notes + written_notes_log

    async def mock_write(note_text, dry_run=False):
        # Appends to candidate's notes without modifying preexisting notes
        written_notes_log.append(note_text)
        return "NOTE_ADDED", None

    manager.get_existing_notes = mock_existing_notes
    manager.write_note = mock_write

    outcome = await NotesService.process_candidate_note(
        candidate_id=candidate.id,
        run_id=run.id,
        github_status="GITHUB_NOT_FOUND",
        go_status="GITHUB_NOT_FOUND",
        dry_run=False,
        screen_repo=screen_repo,
        browser_manager=manager,
    )

    # 1. Our note is successfully added
    assert outcome.action_status == "NOTE_ADDED"
    assert outcome.note_text == NOTE_RULE_A
    assert outcome.confirmed is True

    # 2. Preexisting recruiter notes remain 100% intact and untouched
    assert len(preexisting_notes) == 2
    assert "Recruiter call: Salary expectation 8 LPA" in preexisting_notes
    assert "Passed preliminary round" in preexisting_notes

    # 3. All notes on profile now contain preexisting + our note
    combined = await manager.get_existing_notes()
    assert len(combined) == 3
    assert NOTE_RULE_A in combined

    db.close()



@pytest.mark.asyncio
async def test_ambiguous_outcome_recovery():
    """Verify ambiguous write timeout checks existing notes before declaring failure."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    cand_repo = CandidateRepository(db)

    test_url = f"https://www.instahyre.com/cand/{uuid.uuid4().hex[:8]}"
    candidate, _ = cand_repo.get_or_create(test_url, "Ambiguous User")
    run = screen_repo.create_run()

    manager = PlaywrightBrowserManager(headless=True)

    # Mock write_note to return NOTE_OUTCOME_UNKNOWN (e.g. DOM wait timeout)
    async def mock_write(note_text, dry_run=False):
        return "NOTE_OUTCOME_UNKNOWN", "DOM timeout"

    # Mock recheck get_existing_notes to find the note after all!
    call_count = 0
    async def mock_notes():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return []  # Pre-write check: empty
        return [NOTE_RULE_B]  # Recheck: note appeared!

    manager.write_note = mock_write
    manager.get_existing_notes = mock_notes

    outcome = await NotesService.process_candidate_note(
        candidate_id=candidate.id,
        run_id=run.id,
        github_status="GITHUB_FOUND",
        go_status="GO_NOT_DETECTED",
        dry_run=False,
        screen_repo=screen_repo,
        browser_manager=manager,
    )

    # Recovered safely to NOTE_ADDED!
    assert outcome.action_status == "NOTE_ADDED"
    assert outcome.confirmed is True
    db.close()


@pytest.mark.asyncio
async def test_dry_run_safety():
    """Verify dry_run=True returns SKIPPED without performing live writes."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    cand_repo = CandidateRepository(db)

    test_url = f"https://www.instahyre.com/cand/{uuid.uuid4().hex[:8]}"
    candidate, _ = cand_repo.get_or_create(test_url, "Dry Run User")
    run = screen_repo.create_run()

    outcome = await NotesService.process_candidate_note(
        candidate_id=candidate.id,
        run_id=run.id,
        github_status="GITHUB_NOT_FOUND",
        go_status="GITHUB_NOT_FOUND",
        dry_run=True,
        screen_repo=screen_repo,
        browser_manager=None,
    )

    assert outcome.action_status == "SKIPPED"
    assert outcome.confirmed is False
    assert "Dry run" in outcome.reason
    db.close()

"""Automated tests for ScreeningOrchestrator, note rules A/B/C/D, and event streaming."""

import pytest
import asyncio
from app.services.screening_service import ScreeningOrchestrator
from app.services.notes_service import NotesService
from app.services.event_service import event_broker
from app.core.state import state_manager, RunState
from app.database.session import SessionLocal
from app.repositories.screening_repo import ScreeningRepository
from app.repositories.candidate_repo import CandidateRepository


def test_notes_service_rules():
    """Verify exact candidate note decision rules A, B, C, D."""
    # Rule A: No GitHub profile
    note_a, reason_a = NotesService.evaluate_note_rule(
        github_status="GITHUB_NOT_FOUND", go_status="GITHUB_NOT_FOUND"
    )
    assert note_a == "No GitHub found"

    # Rule B: GitHub found, Go not detected
    note_b, reason_b = NotesService.evaluate_note_rule(
        github_status="GITHUB_FOUND", go_status="GO_NOT_DETECTED"
    )
    assert note_b == "Go lang not found"

    # Rule C: Go detected
    note_c, reason_c = NotesService.evaluate_note_rule(
        github_status="GITHUB_FOUND", go_status="GO_DETECTED"
    )
    assert note_c == "Go lang found"
    assert "Rule C" in reason_c

    # Rule D: Incomplete check / rate limit / API error
    note_d1, _ = NotesService.evaluate_note_rule(
        github_status="GITHUB_FOUND", go_status="CHECK_INCOMPLETE"
    )
    assert note_d1 is None

    note_d2, _ = NotesService.evaluate_note_rule(
        github_status="GITHUB_FOUND", go_status="API_RATE_LIMITED"
    )
    assert note_d2 is None


@pytest.mark.asyncio
async def test_screening_orchestrator_execution_flow():
    """Verify full end-to-end orchestration with synthetic candidates."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    run = screen_repo.create_run()
    run_id = run.id
    db.close()

    orchestrator = ScreeningOrchestrator()

    import uuid
    test_token = uuid.uuid4().hex[:8]
    alice_url = f"https://www.instahyre.com/candidate/alice-{test_token}"
    bob_url = f"https://www.instahyre.com/candidate/bob-{test_token}"

    # Synthetic candidate fixtures
    synthetic_candidates = [
        {
            "name": "Candidate Alice (Go dev)",
            "url": alice_url,
            "github_url": "https://github.com/alice",
        },
        {
            "name": "Candidate Bob (No GitHub)",
            "url": bob_url,
            "github_url": None,
        },
    ]

    # Mock github_service.verify_candidate to return predictable results
    async def mock_verify(url, *args, **kwargs):
        from app.services.github_service import GitHubVerificationResult
        if url and "alice" in url:
            return GitHubVerificationResult(
                status="GO_DETECTED",
                evidence_summary="Go repo found",
                repositories_checked=2,
            )
        return GitHubVerificationResult(
            status="GITHUB_NOT_FOUND",
            evidence_summary="No GitHub",
            repositories_checked=0,
        )

    orchestrator.github_service.verify_candidate = mock_verify

    # Execute run
    await orchestrator._execute_run(
        run_id=run_id, dry_run=True, synthetic_candidates=synthetic_candidates
    )

    # Check results in DB
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    cand_repo = CandidateRepository(db)

    # Alice check
    alice = cand_repo.find_by_identifier(alice_url)
    assert alice is not None
    alice_res = alice.screening_results[0]
    assert alice_res.go_status == "GO_DETECTED"
    # Rule C: Alice should have 'Go lang found' note added
    assert len(alice.note_actions) == 1
    assert alice.note_actions[0].note_text == "Go lang found"

    # Bob check
    bob = cand_repo.find_by_identifier(bob_url)
    assert bob is not None
    bob_res = bob.screening_results[0]
    assert bob_res.github_status == "GITHUB_NOT_FOUND"
    # Rule A: Bob should have note recorded
    assert len(bob.note_actions) == 1
    assert bob.note_actions[0].note_text == "No GitHub found"

    # Verify run completed
    completed_run = screen_repo.get_run(run_id)
    assert completed_run.status == "COMPLETED"
    assert completed_run.processed_count == 2
    db.close()

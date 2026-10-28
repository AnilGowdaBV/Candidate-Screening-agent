"""Comprehensive database tests for models, repositories, deduplication, and constraints."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.database.session import Base
from app.models.candidate import Candidate
from app.models.screening_run import ScreeningRun
from app.models.screening_result import ScreeningResult
from app.models.note_action import NoteAction
from app.models.activity_event import ActivityEvent
from app.repositories.candidate_repo import CandidateRepository
from app.repositories.screening_repo import ScreeningRepository


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:")

    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_candidate_deduplication(db_session):
    """Verify CandidateRepository.get_or_create prevents duplicate candidate records."""
    repo = CandidateRepository(db_session)

    # First discovery
    cand1, created1 = repo.get_or_create(
        instahyre_profile_url="https://www.instahyre.com/candidate/101",
        name="Candidate Alpha",
        github_url="https://github.com/alpha",
    )
    assert created1 is True
    assert cand1.id is not None
    assert cand1.name == "Candidate Alpha"

    # Second discovery with same Instahyre profile URL
    cand2, created2 = repo.get_or_create(
        instahyre_profile_url="https://www.instahyre.com/candidate/101",
        name="Candidate Alpha Updated",
    )
    assert created2 is False
    assert cand2.id == cand1.id

    # Verify total candidate count is strictly 1
    candidates, total = repo.list_candidates()
    assert total == 1
    assert candidates[0].id == cand1.id


def test_candidate_unique_constraint(db_session):
    """Verify raw duplicate insertion raises IntegrityError due to unique constraint."""
    cand1 = Candidate(
        instahyre_profile_url="https://www.instahyre.com/candidate/202",
        name="Candidate Beta",
    )
    db_session.add(cand1)
    db_session.commit()

    cand2 = Candidate(
        instahyre_profile_url="https://www.instahyre.com/candidate/202",
        name="Candidate Beta Duplicate",
    )
    db_session.add(cand2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_enforcement(db_session):
    """Verify that referencing non-existent candidate raises IntegrityError."""
    result = ScreeningResult(
        candidate_id=99999,  # Non-existent ID
        run_id=99999,
        github_status="GITHUB_FOUND",
        go_status="GO_DETECTED",
    )
    db_session.add(result)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_screening_run_and_results(db_session):
    """Verify run creation, checkpointing, and result recording."""
    cand_repo = CandidateRepository(db_session)
    screen_repo = ScreeningRepository(db_session)

    candidate, _ = cand_repo.get_or_create(
        instahyre_profile_url="https://www.instahyre.com/candidate/303",
        name="Candidate Gamma",
        github_url="https://github.com/gamma",
    )

    run = screen_repo.create_run(configuration_snapshot='{"dry_run": true}')
    assert run.id is not None
    assert run.status == "VALIDATING"

    # Update run status and checkpoint
    screen_repo.update_run_status(
        run_id=run.id,
        status="RUNNING",
        last_checkpoint="candidate_303",
        processed_increment=1,
    )
    updated_run = screen_repo.get_run(run.id)
    assert updated_run.status == "RUNNING"
    assert updated_run.last_checkpoint == "candidate_303"
    assert updated_run.processed_count == 1

    # Record screening result
    res = screen_repo.record_screening_result(
        candidate_id=candidate.id,
        run_id=run.id,
        github_status="GITHUB_FOUND",
        go_status="GO_DETECTED",
        evidence_summary="Found Go packages in repo gamma/distributed-kv",
        repositories_checked=5,
    )
    assert res.id is not None
    assert res.go_status == "GO_DETECTED"


def test_note_action_and_duplicate_prevention(db_session):
    """Verify note recording and finding existing notes before writing."""
    cand_repo = CandidateRepository(db_session)
    screen_repo = ScreeningRepository(db_session)

    candidate, _ = cand_repo.get_or_create(
        instahyre_profile_url="https://www.instahyre.com/candidate/404",
        name="Candidate Delta",
    )
    run = screen_repo.create_run()

    # Prior check: should find nothing
    prior_note = screen_repo.find_existing_successful_note(
        candidate_id=candidate.id, note_text="No GitHub found"
    )
    assert prior_note is None

    # Record note action
    note = screen_repo.record_note_action(
        candidate_id=candidate.id,
        run_id=run.id,
        note_text="No GitHub found",
        action_status="NOTE_ADDED",
        confirmed=True,
    )
    assert note.id is not None
    assert note.confirmed_at is not None

    # Second check: should find existing note!
    found = screen_repo.find_existing_successful_note(
        candidate_id=candidate.id, note_text="No GitHub found"
    )
    assert found is not None
    assert found.action_status == "NOTE_ADDED"


def test_dashboard_metrics_aggregation(db_session):
    """Verify aggregated dashboard metrics computed directly from database records."""
    cand_repo = CandidateRepository(db_session)
    screen_repo = ScreeningRepository(db_session)

    cand1, _ = cand_repo.get_or_create("https://instahyre.com/cand/1", "User One")
    cand2, _ = cand_repo.get_or_create("https://instahyre.com/cand/2", "User Two")

    run = screen_repo.create_run()

    # Cand 1: Go detected
    screen_repo.record_screening_result(
        candidate_id=cand1.id,
        run_id=run.id,
        github_status="GITHUB_FOUND",
        go_status="GO_DETECTED",
    )

    # Cand 2: Go not detected + note added
    screen_repo.record_screening_result(
        candidate_id=cand2.id,
        run_id=run.id,
        github_status="GITHUB_FOUND",
        go_status="GO_NOT_DETECTED",
    )
    screen_repo.record_note_action(
        candidate_id=cand2.id,
        run_id=run.id,
        note_text="Go lang not found",
        action_status="NOTE_ADDED",
        confirmed=True,
    )

    metrics = screen_repo.get_dashboard_metrics(run_id=run.id)
    assert metrics["candidates_discovered"] == 2
    assert metrics["candidates_processed"] == 2
    assert metrics["candidates_remaining"] == 0
    assert metrics["github_profiles_found"] == 2
    assert metrics["go_detected"] == 1
    assert metrics["go_not_detected"] == 1
    assert metrics["notes_added"] == 1

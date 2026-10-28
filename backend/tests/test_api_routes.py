"""Tests for candidates, runs, metrics, and events API routes."""

from starlette.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.repositories.candidate_repo import CandidateRepository
from app.repositories.screening_repo import ScreeningRepository

client = TestClient(app)


def test_candidates_api_list_and_get():
    """Verify GET /api/candidates and GET /api/candidates/{id}."""
    db = SessionLocal()
    cand_repo = CandidateRepository(db)
    cand, _ = cand_repo.get_or_create(
        instahyre_profile_url="https://www.instahyre.com/api-test-candidate",
        name="API Test Candidate",
        github_url="https://github.com/api-test",
    )
    cand_id = cand.id
    db.close()

    # List
    response = client.get("/api/candidates")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["id"] == cand_id for c in data["items"])

    # Get by ID
    single_res = client.get(f"/api/candidates/{cand_id}")
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["name"] == "API Test Candidate"
    assert single_data["github_url"] == "https://github.com/api-test"


def test_runs_and_metrics_api():
    """Verify GET /api/runs and GET /api/metrics."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    run = screen_repo.create_run(configuration_snapshot='{"test": true}')
    run_id = run.id
    db.close()

    # List runs
    runs_res = client.get("/api/runs")
    assert runs_res.status_code == 200
    runs_data = runs_res.json()
    assert any(r["id"] == run_id for r in runs_data)

    # Get single run
    single_run = client.get(f"/api/runs/{run_id}")
    assert single_run.status_code == 200
    assert single_run.json()["status"] == "VALIDATING"

    # Get metrics
    metrics_res = client.get("/api/metrics")
    assert metrics_res.status_code == 200
    m_data = metrics_res.json()
    assert "candidates_discovered" in m_data
    assert "go_detected" in m_data
    assert "notes_added" in m_data


def test_events_api():
    """Verify GET /api/events."""
    db = SessionLocal()
    screen_repo = ScreeningRepository(db)
    screen_repo.record_activity_event(
        event_type="TEST_EVENT",
        message="Test event message",
    )
    db.close()

    res = client.get("/api/events")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    assert any(e["event_type"] == "TEST_EVENT" for e in events)

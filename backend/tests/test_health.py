"""Tests for Health and Status API endpoints."""

from starlette.testclient import TestClient
from app.main import app
from app import __version__

client = TestClient(app)


def test_health_endpoint():
    """Verify /api/health responds with healthy status and correct version."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == __version__
    assert "environment" in data


def test_system_status_endpoint():
    """Verify /api/status returns operational state, run_state, and no secret keys."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "run_state" in data
    assert "current_operation" in data
    assert "is_github_configured" in data
    assert "is_instahyre_configured" in data
    assert "instahyre_search_url" in data
    # Verify no secret fields exist in response
    assert "password" not in data
    assert "token" not in data


def test_safe_config_endpoint():
    """Verify /api/config exposes non-secret operational parameters only."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "dry_run" in data
    assert "max_candidates_per_run" in data
    assert "password" not in data
    assert "token" not in data

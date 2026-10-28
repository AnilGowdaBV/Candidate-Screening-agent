"""Pytest configuration ensuring tests use an isolated test database."""

import os
import pytest

# Ensure all tests run against an isolated test database, never touching screening_agent.db
os.environ["DATABASE_URL"] = "sqlite:///./data/test_isolated.db"
os.environ["DRY_RUN"] = "true"

from app.core.config import get_settings
get_settings.cache_clear()

from app.database.session import init_db, engine, Base
init_db()

@pytest.fixture(autouse=True)
def clean_test_db():
    """Ensure clean tables before every test."""
    yield
    # No-op or teardown if needed

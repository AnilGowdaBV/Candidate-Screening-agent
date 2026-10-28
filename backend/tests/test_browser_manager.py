"""Automated tests for browser selectors, candidate parser, and note duplicate detection."""

import pytest
from app.browser.selectors import (
    AUTH_SELECTORS,
    SEARCH_SELECTORS,
    PROFILE_SELECTORS,
)
from app.browser.browser_manager import PlaywrightBrowserManager


def test_selectors_structure():
    """Verify all required selector keys exist."""
    assert "email_input" in AUTH_SELECTORS
    assert "password_input" in AUTH_SELECTORS
    assert "submit_button" in AUTH_SELECTORS
    assert "logged_in_indicator" in AUTH_SELECTORS

    assert "search_container" in SEARCH_SELECTORS
    assert "candidate_link" in SEARCH_SELECTORS
    assert "candidate_cards" in SEARCH_SELECTORS

    assert "github_link" in PROFILE_SELECTORS
    assert "note_textarea" in PROFILE_SELECTORS
    assert "note_save_button" in PROFILE_SELECTORS


@pytest.mark.asyncio
async def test_write_note_dry_run_simulation():
    """Verify that dry_run=True returns SKIPPED and does not execute real writes."""
    manager = PlaywrightBrowserManager(headless=True)

    # Mock get_existing_notes to return empty list
    async def mock_get_notes():
        return []

    manager.get_existing_notes = mock_get_notes

    # Call write_note in dry_run mode
    status, msg = await manager.write_note("No GitHub found", dry_run=True)
    assert status == "SKIPPED"
    assert "Dry run" in (msg or "")


@pytest.mark.asyncio
async def test_write_note_duplicate_detection():
    """Verify that existing note returns NOTE_ALREADY_EXISTS and skips writing."""
    manager = PlaywrightBrowserManager(headless=True)

    # Mock get_existing_notes returning a prior note
    async def mock_get_notes():
        return ["Candidate spoke well on call", "No GitHub found"]

    manager.get_existing_notes = mock_get_notes

    status, msg = await manager.write_note("No GitHub found", dry_run=False)
    assert status == "NOTE_ALREADY_EXISTS"
    assert msg is None

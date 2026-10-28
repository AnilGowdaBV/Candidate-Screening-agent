"""Tests for configuration and secret safety."""

from app.core.config import Settings, DEFAULT_SEARCH_URL


def test_default_search_url_preserved():
    """Verify default search URL contains all critical query parameters unchanged."""
    settings = Settings()
    url = settings.INSTAHYRE_SEARCH_URL
    assert url == DEFAULT_SEARCH_URL
    assert "boolean_query=" in url
    assert "GO+OR+Golang" in url
    assert "workex_max=3" in url
    assert "workex_min=1" in url
    assert "status=1" in url


def test_secrets_masked_in_safe_status():
    """Verify secrets are never returned in safe status dictionary."""
    settings = Settings(
        _env_file=None,
        INSTAHYRE_EMAIL=None,
        INSTAHYRE_PASSWORD="super_secret_password",
        GITHUB_TOKEN="ghp_testtokenthatshouldneverleak12345678",
    )
    safe = settings.get_safe_status()
    # Confirm password and token are absent
    assert "super_secret_password" not in str(safe)
    assert "ghp_testtoken" not in str(safe)
    assert safe["is_github_configured"] is True
    assert safe["is_instahyre_configured"] is False  # Email was not set


def test_credentials_detection():
    """Verify credential presence logic."""
    settings_empty = Settings(_env_file=None, INSTAHYRE_EMAIL=None, INSTAHYRE_PASSWORD=None, GITHUB_TOKEN=None)
    assert settings_empty.is_github_token_configured is False
    assert settings_empty.is_instahyre_configured is False

    settings_full = Settings(
        INSTAHYRE_EMAIL="test@example.com",
        INSTAHYRE_PASSWORD="mypassword",
        GITHUB_TOKEN="ghp_1234567890abcdef",
    )
    assert settings_full.is_github_token_configured is True
    assert settings_full.is_instahyre_configured is True

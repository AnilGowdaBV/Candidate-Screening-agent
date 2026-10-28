"""Unit tests for the new QA Automation domain with Playwright, JavaScript, and TypeScript verification."""

import pytest
import httpx
from app.database.session import get_engine_for_tech, get_sessionmaker_for_tech, TECHNOLOGY_DB_MAP
from app.services.notes_service import NotesService, TECHNOLOGY_NOTE_MAP
from app.services.github_service import GitHubService, TECHNOLOGY_SPECS


def test_qa_automation_registered_in_db_map():
    assert "qa_automation" in TECHNOLOGY_DB_MAP
    assert TECHNOLOGY_DB_MAP["qa_automation"] == "screening_qa_automation.db"
    assert TECHNOLOGY_DB_MAP["qa"] == "screening_qa_automation.db"

    eng = get_engine_for_tech("qa_automation")
    assert eng is not None


def test_qa_automation_notes_service():
    assert "qa_automation" in TECHNOLOGY_NOTE_MAP
    spec = TECHNOLOGY_NOTE_MAP["qa_automation"]
    assert spec["found"] == "QA Automation found"
    assert spec["not_found"] == "QA Automation not found"
    assert spec["status_detected"] == "QA_AUTOMATION_DETECTED"
    assert spec["status_not_detected"] == "QA_AUTOMATION_NOT_DETECTED"

    # Rule A
    note_a, reason_a = NotesService.evaluate_note_rule("GITHUB_NOT_FOUND", "GITHUB_NOT_FOUND", technology="qa_automation")
    assert note_a == "No GitHub found"
    assert "Rule A" in reason_a

    # Rule C
    note_c, reason_c = NotesService.evaluate_note_rule("GITHUB_FOUND", "QA_AUTOMATION_DETECTED", technology="qa_automation")
    assert note_c == "QA Automation found"
    assert "Rule C" in reason_c

    # Rule B
    note_b, reason_b = NotesService.evaluate_note_rule("GITHUB_FOUND", "QA_AUTOMATION_NOT_DETECTED", technology="qa_automation")
    assert note_b == "QA Automation not found"
    assert "Rule B" in reason_b

    # Rule D
    note_d, reason_d = NotesService.evaluate_note_rule("GITHUB_FOUND", "API_ERROR", technology="qa_automation")
    assert note_d is None


@pytest.mark.asyncio
async def test_qa_automation_github_detection_with_playwright():
    gh = GitHubService(token="dummy_token")
    assert "qa_automation" in TECHNOLOGY_SPECS

    mock_repos_playwright_ts = [
        {
            "name": "playwright-e2e-framework",
            "language": "TypeScript",
            "topics": ["playwright", "testing", "typescript"],
            "description": "Automated end-to-end tests using Playwright and TypeScript",
        }
    ]

    # Directly verify the inspect logic for repos
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._data = json_data
            self.text = ""

        def json(self):
            return self._data

    class MockClient:
        async def get(self, url, headers=None):
            if "/users/alice/repos" in url:
                return MockResponse(200, mock_repos_playwright_ts)
            if "/users/alice" in url:
                return MockResponse(200, {"login": "alice"})
            return MockResponse(404, {})

    res = await gh._inspect_user("alice", MockClient(), technology="qa_automation")
    assert res.status == "QA_AUTOMATION_DETECTED"
    assert res.languages_found == "Playwright, TypeScript"


@pytest.mark.asyncio
async def test_qa_automation_github_detection_with_js_qa():
    gh = GitHubService(token="dummy_token")

    mock_repos_js_qa = [
        {
            "name": "qa-automation-suite",
            "language": "JavaScript",
            "topics": ["qa", "automation", "testing"],
            "description": "Automation testing scripts in JavaScript",
        }
    ]

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._data = json_data
            self.text = ""

        def json(self):
            return self._data

    class MockClient:
        async def get(self, url, headers=None):
            if "/users/bob/repos" in url:
                return MockResponse(200, mock_repos_js_qa)
            if "/users/bob" in url:
                return MockResponse(200, {"login": "bob"})
            return MockResponse(404, {})

    res = await gh._inspect_user("bob", MockClient(), technology="qa_automation")
    assert res.status == "QA_AUTOMATION_DETECTED"
    assert res.languages_found == "JavaScript"


@pytest.mark.asyncio
async def test_qa_automation_github_detection_all_three():
    gh = GitHubService(token="dummy_token")

    mock_repos_all_three = [
        {
            "name": "playwright-suite",
            "language": "TypeScript",
            "topics": ["playwright", "testing"],
            "description": "Playwright e2e",
        },
        {
            "name": "legacy-automation",
            "language": "JavaScript",
            "topics": ["javascript", "qa"],
            "description": "JS tests",
        },
    ]

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._data = json_data
            self.text = ""

        def json(self):
            return self._data

    class MockClient:
        async def get(self, url, headers=None):
            if "/users/dave/repos" in url:
                return MockResponse(200, mock_repos_all_three)
            if "/users/dave" in url:
                return MockResponse(200, {"login": "dave"})
            return MockResponse(404, {})

    res = await gh._inspect_user("dave", MockClient(), technology="qa_automation")
    assert res.status == "QA_AUTOMATION_DETECTED"
    assert res.languages_found == "Playwright, TypeScript, JavaScript"


@pytest.mark.asyncio
async def test_qa_automation_github_detection_not_found():
    gh = GitHubService(token="dummy_token")

    mock_unrelated_repos = [
        {
            "name": "recipe-book",
            "language": "Ruby",
            "topics": ["recipes", "cooking"],
            "description": "My favorite family recipes",
        }
    ]

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._data = json_data
            self.text = ""

        def json(self):
            return self._data

    class MockClient:
        async def get(self, url, headers=None):
            if "/users/charlie/repos" in url:
                return MockResponse(200, mock_unrelated_repos)
            if "/users/charlie" in url:
                return MockResponse(200, {"login": "charlie"})
            return MockResponse(404, {})

    res = await gh._inspect_user("charlie", MockClient(), technology="qa_automation")
    assert res.status == "QA_AUTOMATION_NOT_DETECTED"
    assert res.languages_found == "QA_Automation not found"


def test_sheet_tsv_export_includes_languages_found():
    from app.services.sheet_export_service import _build_tsv_for_rows
    from unittest.mock import MagicMock

    cand = MagicMock()
    cand.name = "Test QA Dev"
    cand.instahyre_profile_url = "https://instahyre.com/candidate/123"
    cand.github_url = "https://github.com/testqadev"
    cand.current_salary = "18 LPA"
    cand.location = "Bengaluru"
    cand.experience = "4 Years"
    cand.gitroll_rating = 8.5
    cand.coding_profiles = None
    cand.languages_found = "Playwright, TypeScript, JavaScript"

    res = MagicMock()
    res.go_status = "QA_AUTOMATION_DETECTED"
    res.languages_found = "Playwright, TypeScript, JavaScript"

    tsv = _build_tsv_for_rows([(cand, res)], tech_name="qa_automation")
    lines = tsv.split("\n")
    headers = lines[0].split("\t")
    row = lines[1].split("\t")

    assert "Languages Found" in headers
    lang_idx = headers.index("Languages Found")
    assert row[lang_idx] == "Playwright, TypeScript, JavaScript"


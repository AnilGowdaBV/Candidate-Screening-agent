"""Automated tests for GitHub REST API integration with mocked responses."""

import pytest
import httpx
from app.services.github_service import (
    GitHubService,
    normalize_github_url,
    GitHubVerificationResult,
)


def test_normalize_github_url():
    """Verify robust parsing of various GitHub profile URL structures."""
    # Standard clean URL
    u1, norm1 = normalize_github_url("https://github.com/johndoe")
    assert u1 == "johndoe"
    assert norm1 == "https://github.com/johndoe"

    # With trailing slash
    u2, norm2 = normalize_github_url("https://github.com/janedoe/")
    assert u2 == "janedoe"
    assert norm2 == "https://github.com/janedoe"

    # Missing protocol
    u3, norm3 = normalize_github_url("github.com/bob-smith")
    assert u3 == "bob-smith"
    assert norm3 == "https://github.com/bob-smith"

    # With query parameter sub-paths
    u4, norm4 = normalize_github_url("https://www.github.com/alice?tab=repositories")
    assert u4 == "alice"
    assert norm4 == "https://github.com/alice"

    # Reserved routes
    u_res, _ = normalize_github_url("https://github.com/features")
    assert u_res is None

    # Invalid URL
    u_inv, _ = normalize_github_url("https://linkedin.com/in/someone")
    assert u_inv is None

    # None or empty
    assert normalize_github_url(None) == (None, None)
    assert normalize_github_url("") == (None, None)


@pytest.mark.asyncio
async def test_go_detected_via_primary_language():
    """Verify GO_DETECTED when repository has primary language 'Go'."""
    def handler(request: httpx.Request):
        url = str(request.url)
        if url.endswith("/users/alex"):
            return httpx.Response(200, json={"login": "alex", "public_repos": 1})
        if "/users/alex/repos" in url:
            return httpx.Response(200, json=[
                {
                    "name": "distributed-queue",
                    "language": "Go",
                    "topics": ["queues"],
                    "languages_url": "https://api.github.com/repos/alex/distributed-queue/languages",
                }
            ])
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        result = await service.verify_candidate("https://github.com/alex", client=client)

    assert result.status == "GO_DETECTED"
    assert "distributed-queue" in result.evidence_summary
    assert result.repositories_checked == 1


@pytest.mark.asyncio
async def test_go_detected_via_topics():
    """Verify GO_DETECTED when repository topics tag contains 'golang'."""
    def handler(request: httpx.Request):
        url = str(request.url)
        if url.endswith("/users/maria"):
            return httpx.Response(200, json={"login": "maria"})
        if "/users/maria/repos" in url:
            return httpx.Response(200, json=[
                {
                    "name": "microservices-template",
                    "language": None,
                    "topics": ["microservices", "golang"],
                    "languages_url": "https://api.github.com/repos/maria/microservices-template/languages",
                }
            ])
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        result = await service.verify_candidate("https://github.com/maria", client=client)

    assert result.status == "GO_DETECTED"
    assert "topics: Go/Golang" in result.evidence_summary


@pytest.mark.asyncio
async def test_go_detected_via_languages_byte_breakdown():
    """Verify GO_DETECTED when language statistics contain Go bytes even if primary is Python."""
    def handler(request: httpx.Request):
        url = str(request.url)
        if url.endswith("/users/dave"):
            return httpx.Response(200, json={"login": "dave"})
        if "/users/dave/repos" in url:
            return httpx.Response(200, json=[
                {
                    "name": "mixed-project",
                    "language": "Python",
                    "topics": [],
                    "languages_url": "https://api.github.com/repos/dave/mixed-project/languages",
                }
            ])
        if "/repos/dave/mixed-project/languages" in url:
            return httpx.Response(200, json={"Python": 60000, "Go": 15000})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        result = await service.verify_candidate("https://github.com/dave", client=client)

    assert result.status == "GO_DETECTED"
    assert "15,000 bytes of Go" in result.evidence_summary


@pytest.mark.asyncio
async def test_go_not_detected_clean_repos():
    """Verify GO_NOT_DETECTED when user public repos contain Python/JS but zero Go."""
    def handler(request: httpx.Request):
        url = str(request.url)
        if url.endswith("/users/emma"):
            return httpx.Response(200, json={"login": "emma"})
        if "/users/emma/repos" in url:
            return httpx.Response(200, json=[
                {
                    "name": "frontend-app",
                    "language": "TypeScript",
                    "topics": ["react"],
                    "languages_url": "https://api.github.com/repos/emma/frontend-app/languages",
                }
            ])
        if "/repos/emma/frontend-app/languages" in url:
            return httpx.Response(200, json={"TypeScript": 50000, "HTML": 3000})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        result = await service.verify_candidate("https://github.com/emma", client=client)

    assert result.status == "GO_NOT_DETECTED"
    assert "no Go/Golang detected" in result.evidence_summary
    assert result.repositories_checked == 1


@pytest.mark.asyncio
async def test_github_not_found_404():
    """Verify GITHUB_NOT_FOUND when username does not exist on GitHub."""
    def handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not Found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        result = await service.verify_candidate("https://github.com/nonexistent_ghost_user_12345", client=client)

    assert result.status == "GITHUB_NOT_FOUND"


@pytest.mark.asyncio
async def test_rate_limit_handling():
    """Verify API_RATE_LIMITED on HTTP 403 rate limit response."""
    def handler(request: httpx.Request):
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded for user"},
            headers={"X-RateLimit-Remaining": "0"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        result = await service.verify_candidate("https://github.com/anyuser", client=client)

    assert result.status == "API_RATE_LIMITED"
    assert result.error_code == "RATE_LIMIT"


@pytest.mark.asyncio
async def test_cache_deduplication():
    """Verify that second call for the same username returns cached result without API requests."""
    call_count = 0

    def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        url = str(request.url)
        if url.endswith("/users/cacheuser"):
            return httpx.Response(200, json={"login": "cacheuser"})
        if "/users/cacheuser/repos" in url:
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GitHubService(token="mock_token")
        res1 = await service.verify_candidate("https://github.com/cacheuser", client=client)
        assert res1.status == "GO_NOT_DETECTED"
        current_calls = call_count

        # Second call should hit memory cache immediately
        res2 = await service.verify_candidate("https://github.com/cacheuser", client=client)
        assert res2.status == "GO_NOT_DETECTED"
        assert call_count == current_calls  # Zero extra network calls made!

"""GitHub REST API integration for public repository inspection and Go/Golang verification."""

import re
from typing import Optional, List, Dict, Any, Tuple
import httpx
from pydantic import BaseModel
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("github_service")

# Reserved GitHub path segments that are not valid user profiles
RESERVED_GITHUB_NAMES = {
    "about", "pricing", "features", "explore", "topics", "collections",
    "trending", "login", "join", "enterprise", "orgs", "settings", "search",
    "notifications", "marketplace", "sponsors", "pulls", "issues"
}

GITHUB_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9][a-zA-Z0-9_\-\.]*)(?:[/?#].*)?$",
    re.IGNORECASE
)


class GitHubVerificationResult(BaseModel):
    """Normalized outcome of public repository inspection for Go/Golang."""
    status: str  # GO_DETECTED, GO_NOT_DETECTED, GITHUB_NOT_FOUND, CHECK_INCOMPLETE, API_RATE_LIMITED, API_ERROR
    username: Optional[str] = None
    evidence_summary: str
    repositories_checked: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    languages_found: Optional[str] = None
    git_score: Optional[float] = None


DOMAIN_FRAMEWORKS = {
    "golang": ["gin", "fiber", "echo", "grpc", "goroutine", "goroutines", "microservice", "protobuf", "go-zero", "chi"],
    "python": ["fastapi", "django", "flask", "pytorch", "tensorflow", "pandas", "numpy", "celery", "pydantic"],
    "java": ["spring", "springboot", "spring-boot", "microservice", "kafka", "hibernate", "backend", "maven", "gradle"],
    "javascript": ["react", "node", "nodejs", "express", "nextjs", "vue", "fullstack", "redux"],
    "typescript": ["typescript", "nestjs", "angular", "nextjs", "prisma", "typeorm", "trpc"],
    "frontend": ["react", "vue", "nextjs", "angular", "tailwind", "redux", "ui", "frontend", "svelte"],
    "qa_automation": ["playwright", "cypress", "selenium", "pytest", "testng", "cucumber", "e2e", "automation"],
    "qa": ["playwright", "cypress", "selenium", "pytest", "testng", "cucumber", "e2e", "automation"],
}

def calculate_qa_git_score(user_data: dict, repos: list, languages_found: str = "", technology: str = "general") -> float:
    """
    100% Objective, Deterministic, GitRoll-aligned scoring engine across all domains.
    Zero guessing: Strictly computed from verified GitHub REST API data.
    """
    public_repos = (user_data.get("public_repos") or 0) if isinstance(user_data, dict) else 0
    followers = (user_data.get("followers") or 0) if isinstance(user_data, dict) else 0
    created_at_str = (user_data.get("created_at") or "") if isinstance(user_data, dict) else ""

    score = 3.30

    orig_repos = [r for r in repos if isinstance(r, dict) and not r.get("fork", False)]
    stars = sum(r.get("stargazers_count", 0) for r in orig_repos)
    forks = sum(r.get("forks_count", 0) for r in orig_repos)
    impact = stars + forks

    # 1. Public Original Code Volume (excludes empty/forked repos)
    orig_count = len(orig_repos)
    if orig_count >= 30 or public_repos >= 40:
        score += 0.65
    elif orig_count >= 18 or public_repos >= 25:
        score += 0.50
    elif orig_count >= 8 or public_repos >= 10:
        score += 0.35
    elif orig_count >= 3 or public_repos >= 4:
        score += 0.20

    # 2. Peer Impact & Community Traction (Stars & Forks on original work)
    if impact >= 20:
        score += 0.85
    elif impact >= 10:
        score += 0.65
    elif impact >= 5:
        score += 0.45
    elif impact >= 2:
        score += 0.25
    elif impact == 1:
        score += 0.10

    # 3. Domain Ecosystem & Framework Depth (Technology specific)
    tech_lower = (technology or "general").lower()
    framework_keywords = DOMAIN_FRAMEWORKS.get(tech_lower, [])
    has_domain_framework = False

    for r in orig_repos:
        r_desc = ((r.get("description") or "") + " " + (r.get("name") or "")).lower()
        r_topics = [str(t).lower() for t in (r.get("topics") or [])]
        if any(kw in r_desc or kw in r_topics for kw in framework_keywords):
            has_domain_framework = True
            break

    langs_lower = (languages_found or "").lower()
    if any(kw in langs_lower for kw in framework_keywords):
        has_domain_framework = True

    if has_domain_framework:
        score += 0.40

    # 4. Code Language Breadth (Excludes markup/styling)
    raw_langs = [r.get("language") for r in orig_repos if r.get("language")]
    code_langs = set(l for l in raw_langs if l not in ["HTML", "CSS", "SCSS", "Shell", "CMake", "Makefile"])
    if len(code_langs) >= 3:
        score += 0.45
    elif len(code_langs) >= 2:
        score += 0.30
    elif len(code_langs) == 1:
        score += 0.15

    # 5. Non-Trivial Codebase Depth (Repositories with > 100KB verified size)
    substantial_repos = [r for r in orig_repos if (r.get("size") or 0) >= 100]
    if len(substantial_repos) >= 10:
        score += 0.35
    elif len(substantial_repos) >= 4:
        score += 0.20
    elif len(substantial_repos) >= 1:
        score += 0.10

    # 6. Verified Account Tenure (GitHub account age)
    if created_at_str:
        try:
            created_year = int(created_at_str[:4])
            age = 2026 - created_year
            if age >= 6:
                score += 0.30
            elif age >= 3:
                score += 0.20
            elif age >= 1:
                score += 0.10
        except Exception:
            pass

    # 7. Follower Count (Peer recognition)
    if followers >= 20:
        score += 0.30
    elif followers >= 5:
        score += 0.15
    elif followers >= 1:
        score += 0.05

    # 8. Strict Quality Guardrails:
    if impact == 0 and orig_count <= 2:
        score = min(score, 3.85)
    elif impact <= 1:
        score = min(score, 4.45)
    elif impact <= 3:
        score = min(score, 5.30)

    return round(min(8.00, max(3.10, score)), 2)


def normalize_github_url(raw_url: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract username and normalized URL from arbitrary GitHub profile link.
    Returns (username, normalized_url).
    """
    if not raw_url or not isinstance(raw_url, str):
        return None, None

    clean = raw_url.strip().rstrip(".,:;/)]}>'\"`\\")
    match = GITHUB_URL_PATTERN.match(clean)
    if not match:
        return None, None

    username = match.group(1).strip().rstrip(".,:;/)]}>'\"`\\")
    if username.lower() in RESERVED_GITHUB_NAMES or len(username) < 2:
        return None, None

    normalized_url = f"https://github.com/{username}"
    return username, normalized_url


TECHNOLOGY_SPECS = {
    "golang": {
        "label": "Go/Golang",
        "primary_languages": ["go"],
        "topics": ["go", "golang", "goroutine", "goroutines"],
        "languages_keys": ["Go"],
        "status_detected": "GO_DETECTED",
        "status_not_detected": "GO_NOT_DETECTED",
    },
    "python": {
        "label": "Python",
        "primary_languages": ["python"],
        "topics": ["python", "python3", "django", "flask", "fastapi", "pandas", "numpy"],
        "languages_keys": ["Python"],
        "status_detected": "PYTHON_DETECTED",
        "status_not_detected": "PYTHON_NOT_DETECTED",
    },
    "java": {
        "label": "Java",
        "primary_languages": ["java"],
        "topics": ["java", "spring", "springboot", "spring-boot", "hibernate", "maven", "gradle"],
        "languages_keys": ["Java"],
        "status_detected": "JAVA_DETECTED",
        "status_not_detected": "JAVA_NOT_DETECTED",
    },
    "javascript": {
        "label": "JavaScript",
        "primary_languages": ["javascript"],
        "topics": ["javascript", "js", "node", "nodejs", "express", "react", "vue"],
        "languages_keys": ["JavaScript"],
        "status_detected": "JAVASCRIPT_DETECTED",
        "status_not_detected": "JAVASCRIPT_NOT_DETECTED",
    },
    "typescript": {
        "label": "TypeScript",
        "primary_languages": ["typescript"],
        "topics": ["typescript", "ts", "angular", "nest", "nestjs", "nextjs"],
        "languages_keys": ["TypeScript"],
        "status_detected": "TYPESCRIPT_DETECTED",
        "status_not_detected": "TYPESCRIPT_NOT_DETECTED",
    },
    "frontend": {
        "label": "Frontend Development",
        "primary_languages": ["javascript", "typescript", "html", "css", "vue", "svelte"],
        "topics": ["frontend", "react", "vue", "angular", "nextjs", "svelte", "tailwindcss", "html", "css", "web", "redux", "ui", "ux", "frontend-development"],
        "languages_keys": ["JavaScript", "TypeScript", "HTML", "CSS", "Vue", "Svelte"],
        "status_detected": "FRONTEND_DETECTED",
        "status_not_detected": "FRONTEND_NOT_DETECTED",
    },
    "qa_automation": {
        "label": "QA Automation",
        "primary_languages": ["typescript", "javascript", "python"],
        "topics": [
            "playwright", "playwright-test", "playwright-testing", "playwright-js", "playwright-ts",
            "qa", "automation", "qa-automation", "test-automation", "e2e", "e2e-testing",
            "testing", "automation-testing", "test-framework", "selenium", "cypress"
        ],
        "languages_keys": ["TypeScript", "JavaScript"],
        "status_detected": "QA_AUTOMATION_DETECTED",
        "status_not_detected": "QA_AUTOMATION_NOT_DETECTED",
    },
    "qa": {
        "label": "QA Automation",
        "primary_languages": ["typescript", "javascript", "python"],
        "topics": [
            "playwright", "playwright-test", "playwright-testing", "playwright-js", "playwright-ts",
            "qa", "automation", "qa-automation", "test-automation", "e2e", "e2e-testing",
            "testing", "automation-testing", "test-framework", "selenium", "cypress"
        ],
        "languages_keys": ["TypeScript", "JavaScript"],
        "status_detected": "QA_AUTOMATION_DETECTED",
        "status_not_detected": "QA_AUTOMATION_NOT_DETECTED",
    },
}


class GitHubService:
    """Official GitHub REST API client with deterministic language detection."""

    def __init__(self, token: Optional[str] = None, timeout_seconds: Optional[int] = None):
        settings = get_settings()
        self.token = token or (
            settings.GITHUB_TOKEN.get_secret_value() if settings.GITHUB_TOKEN else None
        )
        self.timeout = timeout_seconds or settings.API_REQUEST_TIMEOUT_SECONDS
        self.base_url = "https://api.github.com"
        # Local in-memory cache to prevent redundant API queries
        self._cache: Dict[str, GitHubVerificationResult] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Prepare request headers without leaking secrets."""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Candidate-Screening-Agent/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def verify_candidate(
        self,
        github_url: Optional[str],
        client: Optional[httpx.AsyncClient] = None,
        technology: str = "golang",
    ) -> GitHubVerificationResult:
        """
        Verify whether the public GitHub profile contains reliable evidence of the selected technology.
        """
        tech = technology.lower() if technology else "golang"
        if tech not in TECHNOLOGY_SPECS:
            tech = "golang"

        username, normalized_url = normalize_github_url(github_url)
        if not username:
            return GitHubVerificationResult(
                status="GITHUB_NOT_FOUND",
                username=None,
                evidence_summary="No valid GitHub profile URL found for candidate",
                repositories_checked=0,
                languages_found="No GitHub found",
            )

        cache_key = f"{username.lower()}_{tech}"
        if cache_key in self._cache:
            logger.info("Using cached GitHub verification for user %s (%s)", username, tech)
            return self._cache[cache_key]

        if client:
            result = await self._inspect_user(username, client, tech)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as new_client:
                result = await self._inspect_user(username, new_client, tech)

        spec = TECHNOLOGY_SPECS[tech]
        if result.status in (spec["status_detected"], spec["status_not_detected"]):
            self._cache[cache_key] = result

        return result

    async def _inspect_user(
        self, username: str, client: httpx.AsyncClient, technology: str = "golang"
    ) -> GitHubVerificationResult:
        """Query user repositories and inspect language evidence for the target technology."""
        tech = technology.lower() if technology else "golang"
        spec = TECHNOLOGY_SPECS.get(tech, TECHNOLOGY_SPECS["golang"])
        tech_label = spec["label"]
        status_det = spec["status_detected"]
        status_not_det = spec["status_not_detected"]

        headers = self._get_headers()

        # Step 1: Verify profile exists
        try:
            user_resp = await client.get(f"{self.base_url}/users/{username}", headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return GitHubVerificationResult(
                status="CHECK_INCOMPLETE",
                username=username,
                evidence_summary="Network timeout while contacting GitHub API",
                error_code="TIMEOUT",
                error_message=str(exc),
            )
        except Exception as exc:
            return GitHubVerificationResult(
                status="API_ERROR",
                username=username,
                evidence_summary="Unexpected error contacting GitHub API",
                error_code="CLIENT_ERROR",
                error_message=str(exc),
            )

        # Rate limit handling
        if user_resp.status_code == 403 and "rate limit" in user_resp.text.lower():
            logger.warning("GitHub API rate limit encountered for user %s", username)
            return GitHubVerificationResult(
                status="API_RATE_LIMITED",
                username=username,
                evidence_summary="GitHub API rate limit reached",
                error_code="RATE_LIMIT",
            )

        if user_resp.status_code == 404:
            return GitHubVerificationResult(
                status="GITHUB_NOT_FOUND",
                username=username,
                evidence_summary=f"GitHub user '{username}' not found (404)",
                languages_found="No GitHub found",
            )

        if user_resp.status_code != 200:
            return GitHubVerificationResult(
                status="API_ERROR",
                username=username,
                evidence_summary=f"GitHub API returned HTTP {user_resp.status_code}",
                error_code=f"HTTP_{user_resp.status_code}",
            )

        # Step 2: Fetch public repositories (sorted by recently updated, up to 100)
        try:
            repos_url = f"{self.base_url}/users/{username}/repos?per_page=100&sort=updated"
            repos_resp = await client.get(repos_url, headers=headers)
        except Exception as exc:
            return GitHubVerificationResult(
                status="CHECK_INCOMPLETE",
                username=username,
                evidence_summary="Failed to retrieve user repository list",
                error_code="FETCH_REPOS_FAILED",
                error_message=str(exc),
            )

        if repos_resp.status_code == 403 and "rate limit" in repos_resp.text.lower():
            return GitHubVerificationResult(
                status="API_RATE_LIMITED",
                username=username,
                evidence_summary="Rate limit exceeded during repository fetch",
                error_code="RATE_LIMIT",
            )

        if repos_resp.status_code != 200:
            return GitHubVerificationResult(
                status="API_ERROR",
                username=username,
                evidence_summary=f"Failed to fetch repositories (HTTP {repos_resp.status_code})",
                error_code=f"HTTP_{repos_resp.status_code}",
            )

        repos: List[Dict[str, Any]] = repos_resp.json()
        if not repos:
            not_found_str = "QA_Automation not found" if tech in ("qa_automation", "qa") else f"{tech_label} not found"
            return GitHubVerificationResult(
                status=status_not_det,
                username=username,
                evidence_summary=f"User '{username}' has 0 public repositories",
                repositories_checked=0,
                languages_found=not_found_str,
            )

        # Step 3: Scan repositories for target technology evidence
        if tech == "frontend":
            ts_evidence_repos: List[str] = []
            js_evidence_repos: List[str] = []
            repos_checked_count = 0

            for repo in repos:
                repo_name = repo.get("name", "")
                primary_lang = (repo.get("language") or "").strip().lower()
                topics = [t.lower() for t in (repo.get("topics", []) or [])]
                repos_checked_count += 1

                # Check TypeScript
                if not ts_evidence_repos:
                    if primary_lang == "typescript":
                        ts_evidence_repos.append(f"{repo_name} (primary language: TypeScript)")
                    elif any(t in ["typescript", "ts"] for t in topics):
                        ts_evidence_repos.append(f"{repo_name} (topics: TypeScript)")

                # Check JavaScript
                if not js_evidence_repos:
                    if primary_lang in ["javascript", "html", "css"]:
                        js_evidence_repos.append(f"{repo_name} (primary language: {repo.get('language')})")
                    elif any(t in ["javascript", "js", "react", "vue", "nextjs", "angular", "svelte", "frontend", "redux"] for t in topics):
                        js_evidence_repos.append(f"{repo_name} (topics: JavaScript/Frontend)")

                # If either or both not yet found, check languages_url
                if (not ts_evidence_repos or not js_evidence_repos) and repo.get("languages_url"):
                    try:
                        lang_resp = await client.get(repo.get("languages_url"), headers=headers)
                        if lang_resp.status_code == 200:
                            lang_data = lang_resp.json()
                            if not ts_evidence_repos and lang_data.get("TypeScript", 0) > 0:
                                ts_evidence_repos.append(f"{repo_name} ({lang_data['TypeScript']:,} bytes of TypeScript)")
                            if not js_evidence_repos and lang_data.get("JavaScript", 0) > 0:
                                js_evidence_repos.append(f"{repo_name} ({lang_data['JavaScript']:,} bytes of JavaScript)")
                        elif lang_resp.status_code == 403 and "rate limit" in lang_resp.text.lower():
                            return GitHubVerificationResult(
                                status="API_RATE_LIMITED",
                                username=username,
                                evidence_summary=f"Rate limit hit while inspecting repository {repo_name}",
                                repositories_checked=repos_checked_count,
                                error_code="RATE_LIMIT",
                            )
                    except Exception:
                        pass

                # If both are confirmed, stop scanning further repos
                if ts_evidence_repos and js_evidence_repos:
                    break

            user_data = user_resp.json() if user_resp.status_code == 200 else {}
            if ts_evidence_repos and js_evidence_repos:
                langs_str = "TypeScript, JavaScript"
                evidence_str = f"Both TypeScript and JavaScript found: TypeScript in {ts_evidence_repos[0]} & JavaScript in {js_evidence_repos[0]}"
                git_score = calculate_qa_git_score(user_data, repos, languages_found=langs_str, technology="frontend")
                logger.info("Candidate %s: FRONTEND_DETECTED (%s, GitScore: %s/10)", username, evidence_str, git_score)
                return GitHubVerificationResult(
                    status="FRONTEND_DETECTED",
                    username=username,
                    evidence_summary=evidence_str,
                    repositories_checked=repos_checked_count,
                    languages_found=langs_str,
                    git_score=git_score,
                )
            elif ts_evidence_repos:
                langs_str = "TypeScript"
                evidence_str = f"TypeScript found in: {ts_evidence_repos[0]}"
                git_score = calculate_qa_git_score(user_data, repos, languages_found=langs_str, technology="frontend")
                logger.info("Candidate %s: FRONTEND_DETECTED (%s, GitScore: %s/10)", username, evidence_str, git_score)
                return GitHubVerificationResult(
                    status="FRONTEND_DETECTED",
                    username=username,
                    evidence_summary=evidence_str,
                    repositories_checked=repos_checked_count,
                    languages_found=langs_str,
                    git_score=git_score,
                )
            elif js_evidence_repos:
                langs_str = "JavaScript"
                evidence_str = f"JavaScript found in: {js_evidence_repos[0]}"
                git_score = calculate_qa_git_score(user_data, repos, languages_found=langs_str, technology="frontend")
                logger.info("Candidate %s: FRONTEND_DETECTED (%s, GitScore: %s/10)", username, evidence_str, git_score)
                return GitHubVerificationResult(
                    status="FRONTEND_DETECTED",
                    username=username,
                    evidence_summary=evidence_str,
                    repositories_checked=repos_checked_count,
                    languages_found=langs_str,
                    git_score=git_score,
                )
            else:
                no_tech_summary = f"Inspected {repos_checked_count} public repositories; neither TypeScript nor JavaScript detected"
                logger.info("Candidate %s: FRONTEND_NOT_DETECTED (%s)", username, no_tech_summary)
                return GitHubVerificationResult(
                    status="FRONTEND_NOT_DETECTED",
                    username=username,
                    evidence_summary=no_tech_summary,
                    repositories_checked=repos_checked_count,
                    languages_found="Frontend not found",
                )

        if tech in ("qa_automation", "qa"):
            found_playwright = False
            found_ts = False
            found_js = False
            playwright_repos: List[str] = []
            ts_repos: List[str] = []
            js_repos: List[str] = []
            repos_checked_count = 0

            for repo in repos:
                repo_name = repo.get("name", "")
                repo_name_lower = repo_name.lower()
                repo_desc_lower = (repo.get("description") or "").lower()
                primary_lang = (repo.get("language") or "").strip().lower()
                topics = [t.lower() for t in (repo.get("topics", []) or [])]
                repos_checked_count += 1

                # 1. Playwright check
                if not found_playwright:
                    if (
                        "playwright" in repo_name_lower
                        or "playwright" in repo_desc_lower
                        or any("playwright" in t for t in topics)
                    ):
                        found_playwright = True
                        playwright_repos.append(repo_name)

                # 2. TypeScript (TS) check
                if not found_ts:
                    if primary_lang == "typescript" or any(t in ["typescript", "ts"] for t in topics):
                        found_ts = True
                        ts_repos.append(repo_name)

                # 3. JavaScript (JS) check
                if not found_js:
                    if primary_lang in ["javascript", "node", "nodejs"] or any(
                        t in ["javascript", "js", "node", "nodejs"] for t in topics
                    ):
                        found_js = True
                        js_repos.append(repo_name)

                # Query languages API if TS or JS not yet confirmed
                if (not found_ts or not found_js) and repo.get("languages_url"):
                    try:
                        lang_resp = await client.get(repo.get("languages_url"), headers=headers)
                        if lang_resp.status_code == 200:
                            lang_data = lang_resp.json()
                            if not found_ts and lang_data.get("TypeScript", 0) > 0:
                                found_ts = True
                                ts_repos.append(repo_name)
                            if not found_js and lang_data.get("JavaScript", 0) > 0:
                                found_js = True
                                js_repos.append(repo_name)
                        elif lang_resp.status_code == 403 and "rate limit" in lang_resp.text.lower():
                            return GitHubVerificationResult(
                                status="API_RATE_LIMITED",
                                username=username,
                                evidence_summary=f"Rate limit hit while inspecting repository {repo_name}",
                                repositories_checked=repos_checked_count,
                                error_code="RATE_LIMIT",
                            )
                    except Exception:
                        pass

                # If all 3 have been confirmed across candidate repos, stop early
                if found_playwright and found_ts and found_js:
                    break

            langs_list: List[str] = []
            if found_playwright:
                langs_list.append("Playwright")
            if found_ts:
                langs_list.append("TypeScript")
            if found_js:
                langs_list.append("JavaScript")

            if langs_list:
                languages_found_str = ", ".join(langs_list)
                evidence_str = f"QA Automation found: {languages_found_str}"
                user_data = user_resp.json() if user_resp.status_code == 200 else {}
                git_score = calculate_qa_git_score(user_data, repos, languages_found=languages_found_str)
                logger.info("Candidate %s: QA_AUTOMATION_DETECTED (%s, GitScore: %s/10)", username, evidence_str, git_score)
                return GitHubVerificationResult(
                    status="QA_AUTOMATION_DETECTED",
                    username=username,
                    evidence_summary=evidence_str,
                    repositories_checked=repos_checked_count,
                    languages_found=languages_found_str,
                    git_score=git_score,
                )
            else:
                languages_found_str = "QA_Automation not found"
                no_tech_summary = f"Inspected {repos_checked_count} public repositories; no Playwright, TypeScript, or JavaScript detected"
                logger.info("Candidate %s: QA_AUTOMATION_NOT_DETECTED (%s)", username, no_tech_summary)
                return GitHubVerificationResult(
                    status="QA_AUTOMATION_NOT_DETECTED",
                    username=username,
                    evidence_summary=no_tech_summary,
                    repositories_checked=repos_checked_count,
                    languages_found=languages_found_str,
                )


        repos_checked_count = 0
        tech_evidence_repos: List[str] = []

        primary_langs_lower = [l.lower() for l in spec["primary_languages"]]
        topics_lower = [t.lower() for t in spec["topics"]]
        lang_keys = spec["languages_keys"]

        for repo in repos:
            repo_name = repo.get("name", "")
            primary_lang = repo.get("language") or ""
            topics = repo.get("topics", []) or []
            repos_checked_count += 1

            # Check primary language field
            if primary_lang and primary_lang.strip().lower() in primary_langs_lower:
                tech_evidence_repos.append(f"{repo_name} (primary language: {primary_lang})")
                break

            # Check topics
            if any(t.lower() in topics_lower for t in topics):
                tech_evidence_repos.append(f"{repo_name} (topics: {tech_label})")
                break

            # Check repository languages API endpoint for non-primary usage
            languages_url = repo.get("languages_url")
            if languages_url:
                try:
                    lang_resp = await client.get(languages_url, headers=headers)
                    if lang_resp.status_code == 200:
                        lang_data = lang_resp.json()
                        for k in lang_keys:
                            if k in lang_data and lang_data[k] > 0:
                                bytes_count = lang_data[k]
                                tech_evidence_repos.append(f"{repo_name} ({bytes_count:,} bytes of {k})")
                                break
                        if tech_evidence_repos:
                            break
                    elif lang_resp.status_code == 403 and "rate limit" in lang_resp.text.lower():
                        return GitHubVerificationResult(
                            status="API_RATE_LIMITED",
                            username=username,
                            evidence_summary=f"Rate limit hit while inspecting repository {repo_name}",
                            repositories_checked=repos_checked_count,
                            error_code="RATE_LIMIT",
                        )
                except Exception:
                    pass

        # Step 4: Classify results
        if tech_evidence_repos:
            evidence_str = f"{tech_label} evidence detected in: {', '.join(tech_evidence_repos)}"
            user_data = user_resp.json() if user_resp.status_code == 200 else {}
            git_score = calculate_qa_git_score(user_data, repos, languages_found=evidence_str, technology=technology)

            langs_list = [tech_label]
            if technology.lower() == "java":
                for r in repos:
                    r_desc = ((r.get("description") or "") + " " + (r.get("name") or "")).lower()
                    r_topics = [str(t).lower() for t in (r.get("topics") or [])]
                    if any(k in r_desc or k in r_topics for k in ["spring", "springboot", "spring-boot"]):
                        if "Spring Boot" not in langs_list:
                            langs_list.append("Spring Boot")
                    if any(k in r_desc or k in r_topics for k in ["kafka", "rabbitmq"]):
                        if "Kafka" not in langs_list:
                            langs_list.append("Kafka")
            langs_str = ", ".join(langs_list)

            logger.info("Candidate %s: %s (%s, GitScore: %s/10)", username, status_det, evidence_str, git_score)
            return GitHubVerificationResult(
                status=status_det,
                username=username,
                evidence_summary=evidence_str,
                repositories_checked=repos_checked_count,
                languages_found=langs_str,
                git_score=git_score,
            )

        # No evidence in any inspected repository
        no_tech_summary = f"Inspected {repos_checked_count} public repositories; no {tech_label} detected"
        logger.info("Candidate %s: %s (%s)", username, status_not_det, no_tech_summary)
        return GitHubVerificationResult(
            status=status_not_det,
            username=username,
            evidence_summary=no_tech_summary,
            repositories_checked=repos_checked_count,
            languages_found=f"{tech_label} not found",
        )

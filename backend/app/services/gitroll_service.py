"""Service for fetching candidate code quality ratings and grade scores from GitRoll (gitroll.io)."""

import asyncio
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import httpx
from app.core.logging import get_logger

logger = get_logger("gitroll_service")

GITROLL_SCAN_API = "https://gitroll.io/api/user-scan"
GITROLL_PROFILE_BASE = "https://gitroll.io/profile"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_github_username(github_url_or_handle: str) -> Optional[str]:
    """Extract clean GitHub username from full URL or handle."""
    if not github_url_or_handle:
        return None
    cleaned = github_url_or_handle.strip().rstrip("/")
    if "github.com/" in cleaned:
        parts = cleaned.split("github.com/")
        handle = parts[-1].split("/")[0].split("?")[0].strip()
        return handle if handle else None
    return cleaned.split("/")[0].split("?")[0].strip()


class GitRollService:
    """Interacts with GitRoll to scan repositories and retrieve overall candidate ratings."""

    @classmethod
    async def fetch_rating(
        cls,
        github_url_or_handle: str,
        max_poll_seconds: int = 45,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """
        Fetch GitRoll overall rating and letter grade for a given GitHub user.
        
        Returns:
            {
                "success": bool,
                "username": str,
                "score": float or None,
                "grade": str or None,
                "note_text": str or None,  # Exact format: "Overall Rating: <Grade> <Score>"
                "profile_url": str or None,
                "error": str or None,
            }
        """
        username = extract_github_username(github_url_or_handle)
        if not username:
            return {
                "success": False,
                "username": None,
                "score": None,
                "grade": None,
                "note_text": None,
                "profile_url": None,
                "error": "No valid GitHub username could be extracted",
            }

        logger.info("Initiating GitRoll scan check for username: '%s'", username)

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
                # 1. Trigger or look up user scan via GitRoll API
                post_resp = await client.post(GITROLL_SCAN_API, json={"user": username})
                if post_resp.status_code != 200:
                    logger.warning("GitRoll user-scan API returned HTTP %d: %s", post_resp.status_code, post_resp.text[:200])
                    return {
                        "success": False,
                        "username": username,
                        "score": None,
                        "grade": None,
                        "note_text": None,
                        "profile_url": None,
                        "error": f"GitRoll API returned status {post_resp.status_code}",
                    }

                scan_data = post_resp.json()
                profile_id = scan_data.get("profileId") or f"s{scan_data.get('id', '')}"
                if not profile_id or profile_id == "s":
                    return {
                        "success": False,
                        "username": username,
                        "score": None,
                        "grade": None,
                        "note_text": None,
                        "profile_url": None,
                        "error": "GitRoll did not return a valid profileId",
                    }

                profile_url = f"{GITROLL_PROFILE_BASE}/{profile_id}"
                logger.info("User scan mapped to profile URL: %s (existing=%s)", profile_url, scan_data.get("existing"))

                # 2. Poll profile URL until rating is available or max_poll_seconds is reached
                elapsed = 0
                while elapsed <= max_poll_seconds:
                    prof_resp = await client.get(profile_url)
                    if prof_resp.status_code == 404:
                        logger.info("GitRoll profile 404 for '%s'", username)
                        return {
                            "success": False,
                            "username": username,
                            "score": None,
                            "grade": None,
                            "note_text": None,
                            "profile_url": profile_url,
                            "error": "GitRoll profile returned 404 (not found)",
                        }

                    if prof_resp.status_code == 200:
                        score, grade = cls._parse_rating_from_html(prof_resp.text)
                        if score is not None and grade:
                            note_text = f"Overall Rating: {grade} {score:.2f}"
                            logger.info(
                                "GitRoll rating resolved for '%s': %s (Score: %.2f, Grade: %s, Profile: %s)",
                                username, note_text, score, grade, profile_url
                            )
                            return {
                                "success": True,
                                "username": username,
                                "score": score,
                                "grade": grade,
                                "note_text": note_text,
                                "profile_url": profile_url,
                                "error": None,
                            }

                        # Check for immediate no-code messages (no need to wait 45s)
                        text_lower = prof_resp.text.lower()
                        if any(phrase in text_lower for phrase in [
                            "results are not available",
                            "does not have any scannable repository",
                            "does not have any public repository",
                            "no scannable repository",
                            "insufficient code",
                            "the user does not have any",
                        ]):
                            logger.info("GitRoll profile confirmed unscannable for '%s': %s", username, profile_url)
                            return {
                                "success": False,
                                "username": username,
                                "score": None,
                                "grade": None,
                                "note_text": None,
                                "profile_url": profile_url,
                                "error": "GitRoll returned 'No scannable repository' (insufficient code data)",
                            }

                    # Wait before next poll iteration
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                    logger.debug("Waiting for GitRoll analysis for '%s' (%ds elapsed)...", username, elapsed)

                return {
                    "success": False,
                    "username": username,
                    "score": None,
                    "grade": None,
                    "note_text": None,
                    "profile_url": profile_url,
                    "error": f"Scan in progress on GitRoll (still calculating after {max_poll_seconds}s)",
                }

        except Exception as e:
            logger.error("Exception during GitRoll check for '%s': %s", username, e, exc_info=True)
            return {
                "success": False,
                "username": username,
                "score": None,
                "grade": None,
                "note_text": None,
                "profile_url": None,
                "error": str(e),
            }

    @staticmethod
    def _parse_rating_from_html(html: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract overall score float and letter grade from GitRoll profile page HTML."""
        # Check og:image or metadata parameters
        score_match = re.search(r'overallScore=([0-9.]+)', html)
        grade_match = re.search(r'overallRatingLetter=([A-Za-z+-]+)', html)

        score: Optional[float] = None
        grade: Optional[str] = None

        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                pass

        if grade_match:
            grade = grade_match.group(1).strip()

        # Fallback: check DOM text structure if metadata is missing
        if score is None or grade is None:
            dom_score_match = re.search(r'Overall Rating.*?([A-Z][+-]?).*?([0-9]\.[0-9]{1,2})', html, re.DOTALL)
            if dom_score_match:
                grade = grade or dom_score_match.group(1).strip()
                try:
                    score = score or float(dom_score_match.group(2))
                except ValueError:
                    pass

        return score, grade

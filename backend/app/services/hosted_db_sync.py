"""Publish the local SQLite file so the hosted site picks it up on the next deploy."""

import logging
import shutil
import subprocess
import threading
from pathlib import Path

from app.database.session import TECHNOLOGY_DB_MAP, _canonical_tech, base_dir

logger = logging.getLogger("screening_agent.hosted_db_sync")

_repo_root = Path(__file__).resolve().parents[3]
_image_data = _repo_root / "backend" / "data"


def schedule_hosted_db_sync(technology: str) -> None:
    """Copy this technology's database into the image and push it."""
    from app.core.config import get_settings
    if get_settings().ENVIRONMENT.lower() == "production":
        return
    tech = _canonical_tech(technology)
    threading.Thread(target=_publish, args=(tech,), daemon=True).start()


def _publish(tech: str) -> None:
    filename = TECHNOLOGY_DB_MAP[tech]
    source = base_dir / filename
    if not source.exists():
        logger.warning("No local database to publish for %s", tech)
        return
    _image_data.mkdir(parents=True, exist_ok=True)
    target = _image_data / filename
    shutil.copy2(source, target)
    rel = f"backend/data/{filename}"
    try:
        subprocess.run(["git", "add", "--", rel], cwd=_repo_root, check=True, capture_output=True, text=True)
        staged = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", rel],
            cwd=_repo_root,
        )
        if staged.returncode == 0:
            logger.info("Hosted database for %s is already current", tech)
            return
        subprocess.run(
            ["git", "commit", "-m", f"Update the hosted {tech} database after the latest screening run."],
            cwd=_repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=_repo_root, check=True, capture_output=True, text=True)
        logger.info("Pushed %s so the hosted site can rebuild with the new database", rel)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        logger.error("Could not publish the hosted database for %s: %s", tech, detail[-500:])

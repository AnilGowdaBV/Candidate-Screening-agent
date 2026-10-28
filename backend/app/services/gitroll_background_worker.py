"""Background worker to continuously fetch GitRoll ratings for candidates simultaneously."""

import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
from datetime import datetime, timezone
from app.core.logging import get_logger
from app.database.session import get_sessionmaker_for_tech
from app.models.candidate import Candidate
from app.models.screening_result import ScreeningResult
from app.services.gitroll_service import GitRollService

logger = get_logger("gitroll_worker")

async def run_worker(technology: str = "java"):
    logger.info("Starting GitRoll simultaneous background worker for '%s'...", technology)
    sm = get_sessionmaker_for_tech(technology)
    last_processed_id = 0
    
    while True:
        try:
            db = sm()
            try:
                # Query candidates sequentially by ID where github_url is set, target tech was detected, and not yet scored
                cand = (
                    db.query(Candidate)
                    .join(ScreeningResult, ScreeningResult.candidate_id == Candidate.id)
                    .filter(Candidate.github_url.isnot(None))
                    .filter(Candidate.gitroll_rating.is_(None))
                    .filter((Candidate.gitroll_grade != "N/A") | (Candidate.gitroll_grade.is_(None)))
                    .filter(Candidate.id > last_processed_id)
                    .filter(ScreeningResult.go_status.like('%_DETECTED'))
                    .filter(~ScreeningResult.go_status.like('%NOT_DETECTED%'))
                    .order_by(Candidate.id.asc())
                    .first()
                )
                
                # If reached end of list, wrap around to re-check any that were still calculating
                if not cand:
                    last_processed_id = 0
                    db.close()
                    await asyncio.sleep(3)
                    continue
                
                last_processed_id = cand.id
                gh_url = cand.github_url
                cand_id = cand.id
                cand_name = cand.name
                print(f"[GitRoll Worker] Scanning: {cand_name} (#{cand_id}) -> {gh_url}", flush=True)
                
                try:
                    res = await GitRollService.fetch_rating(gh_url, max_poll_seconds=20, poll_interval=4)
                    cand.gitroll_scanned_at = datetime.now(timezone.utc)
                    cand.gitroll_profile_url = res.get("profile_url")
                    
                    if res.get("success"):
                        cand.gitroll_rating = res.get("score")
                        cand.gitroll_grade = res.get("grade")
                        cand.gitroll_note_status = "RATING_FETCHED"
                        print(f"[GitRoll Worker] SUCCESS: {cand_name} -> Grade: {cand.gitroll_grade}, Rating: {cand.gitroll_rating:.2f}", flush=True)
                        logger.info(
                            "GitRoll score resolved for %s (#%d): Grade=%s Score=%.2f",
                            cand_name, cand_id, cand.gitroll_grade, cand.gitroll_rating
                        )
                    else:
                        err = str(res.get("error", "")).lower()
                        # Only mark N/A if candidate truly does not exist on GitRoll/GitHub (404)
                        if "404" in err or "user not found" in err or "invalid github username" in err:
                            cand.gitroll_grade = "N/A"
                            cand.gitroll_note_status = "NO_RATING_AVAILABLE"
                            print(f"[GitRoll Worker] N/A: {cand_name} -> {err}", flush=True)
                            logger.info("GitRoll rating confirmed unavailable for %s (#%d): %s", cand_name, cand_id, err)
                        else:
                            cand.gitroll_grade = "Pending Scan"
                            print(f"[GitRoll Worker] PENDING: {cand_name} (scan in progress on GitRoll)", flush=True)
                            logger.info("GitRoll scan in progress for %s (#%d); will retry on next pass", cand_name, cand_id)
                            
                    db.commit()
                except Exception as e:
                    logger.warning("Error fetching GitRoll for candidate %s: %s", cand_name, e)
                    db.rollback()
                    
            finally:
                db.close()
                
        except Exception as exc:
            logger.error("GitRoll background worker loop error: %s", exc)
            await asyncio.sleep(5)
            
        await asyncio.sleep(1)

if __name__ == "__main__":
    tech = sys.argv[1] if len(sys.argv) > 1 else "java"
    asyncio.run(run_worker(tech))

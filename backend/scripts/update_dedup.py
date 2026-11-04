from pathlib import Path

file_path = Path("backend/app/services/screening_service.py")
content = file_path.read_text(encoding="utf-8")

target = """                # Only fast-skip if candidate was already processed within this exact current run
                prior_result = screen_repo.find_latest_screening_result(candidate.id)
                if prior_result and prior_result.run_id == run_id:
                    logger.info("Candidate %s (#%d) already screened in this run. Skipping duplicate card.", cand_name, candidate.id)
                    continue"""

replacement = """                # Skip candidate if already screened previously across any run
                prior_result = screen_repo.find_latest_screening_result(candidate.id)
                if prior_result and prior_result.go_status not in ("CHECK_INCOMPLETE", "API_RATE_LIMITED", "API_ERROR"):
                    logger.info("Candidate %s (#%d) already screened previously (%s). Skipping duplicate profile.", cand_name, candidate.id, prior_result.go_status)
                    await event_broker.emit(
                        event_type="CANDIDATE_SKIPPED_DUPLICATE",
                        message=f"{cand_name} was already screened earlier ({prior_result.go_status}). Skipping duplicate.",
                        run_id=run_id,
                        candidate_id=candidate.id,
                    )
                    continue"""

assert target in content, "Target block not found!"
new_content = content.replace(target, replacement, 1)
file_path.write_text(new_content, encoding="utf-8", newline="\r\n")
print("Successfully updated cross-run deduplication logic!")

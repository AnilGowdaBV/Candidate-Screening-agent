"""Pydantic schemas for runs, activity events, and metrics."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ScreeningRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    last_checkpoint: Optional[str] = None
    processed_count: int
    error_count: int
    configuration_snapshot: Optional[str] = None


class ActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: Optional[int] = None
    candidate_id: Optional[int] = None
    event_type: str
    message: str
    created_at: datetime
    metadata_json: Optional[str] = None


class DashboardMetrics(BaseModel):
    candidates_discovered: int
    candidates_processed: int
    candidates_remaining: int
    github_profiles_found: int
    github_profiles_missing: int
    go_detected: int
    go_not_detected: int
    notes_added: int
    notes_already_present: int
    candidates_needing_review: int
    errors: int

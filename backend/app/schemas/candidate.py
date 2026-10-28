"""Pydantic schemas for candidate representation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ScreeningResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    github_status: str
    go_status: str
    evidence_summary: Optional[str] = None
    repositories_checked: int
    checked_at: datetime
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    languages_found: Optional[str] = None


class NoteActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    note_text: str
    action_status: str
    attempted_at: datetime
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instahyre_profile_url: str
    instahyre_external_id: Optional[str] = None
    name: str
    github_url: Optional[str] = None
    gitroll_rating: Optional[float] = None
    actual_gitroll_score: Optional[float] = None
    gitroll_grade: Optional[str] = None
    gitroll_profile_url: Optional[str] = None
    gitroll_scanned_at: Optional[datetime] = None
    gitroll_note_status: Optional[str] = None
    current_salary: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    coding_profiles: Optional[str] = None
    languages_found: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
    screening_results: List[ScreeningResultRead] = []
    note_actions: List[NoteActionRead] = []


class CandidateListResponse(BaseModel):
    items: List[CandidateRead]
    total: int
    limit: int
    offset: int

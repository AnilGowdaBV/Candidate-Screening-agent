"""API endpoints for candidate records and filtering."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.candidate_repo import CandidateRepository
from app.schemas.candidate import CandidateRead, CandidateListResponse

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
def list_candidates(
    search: Optional[str] = Query(None, description="Search by name, profile, or github"),
    filter_status: Optional[str] = Query(None, description="Filter by classification status"),
    limit: int = Query(250, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve paginated and filterable list of candidate records."""
    repo = CandidateRepository(db)
    items, total = repo.list_candidates(
        search_query=search,
        filter_status=filter_status,
        limit=limit,
        offset=offset,
    )
    return CandidateListResponse(
        items=[CandidateRead.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Fetch candidate details by ID."""
    repo = CandidateRepository(db)
    cand = repo.get_by_id(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateRead.model_validate(cand)


@router.post("/{candidate_id}/gitroll-scan")
async def scan_candidate_gitroll(
    candidate_id: int,
    add_instahyre_note: bool = Query(False, description="Whether to write rating note to Instahyre profile"),
    dry_run: bool = Query(False, description="Preview rating and note without writing to Instahyre"),
    db: Session = Depends(get_db),
):
    """
    Trigger GitRoll assessment scan for candidate. Extracts rating/grade and optionally
    writes 'Overall Rating: <Grade> <Score>' to Instahyre profile with 100% duplicate protection.
    """
    from app.services.gitroll_scan_manager import GitRollScanManager

    manager = GitRollScanManager()
    result = await manager.scan_candidate(
        candidate_id=candidate_id,
        db=db,
        add_instahyre_note=add_instahyre_note,
        dry_run=dry_run,
    )
    if not result.get("success") and result.get("note_status") != "NO_RATING_AVAILABLE":
        raise HTTPException(status_code=400, detail=result.get("error", "GitRoll scan failed"))
    return result


@router.post("/export-google-sheets")
async def export_to_google_sheet(
    technology: str = Query("javascript", description="Technology to export"),
    sheet_url: Optional[str] = Query(None, description="Target Google Sheet URL"),
):
    """Export candidate records to Google Sheet in ascending order."""
    from app.services.sheet_export_service import export_candidates_to_google_sheet
    target_url = sheet_url.strip() if sheet_url and sheet_url.strip() else None
    res = await export_candidates_to_google_sheet(technology=technology, sheet_url=target_url)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Export failed"))
    return res


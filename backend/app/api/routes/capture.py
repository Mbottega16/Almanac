from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.routes.resources import _to_out
from app.config import settings
from app.schemas.capture import BatchImportRequest, BatchImportResult
from app.schemas.resource import ResourceCreate
from app.services import capture_service, resource_service

router = APIRouter()


@router.post("/resources/batch", response_model=BatchImportResult)
def batch_import(items: list[BatchImportRequest], db: Session = Depends(get_db)):
    """Upserts each resource on `link` — re-importing an existing link updates
    it in place instead of duplicating. Both capture paths (the session-assisted
    flow and the live-research flow below) commit through this one endpoint."""
    created, updated = [], []
    for item in items:
        resource, was_created = resource_service.upsert_resource(db, item)
        (created if was_created else updated).append(_to_out(resource))
    return BatchImportResult(created=created, updated=updated)


class ResearchRequest(BaseModel):
    links: list[str]
    notes: str | None = None


class ResearchResponse(BaseModel):
    # Draft, UNSAVED resources — review them, then POST the ones you want to
    # /api/resources/batch to actually store them.
    drafts: list[ResourceCreate]


@router.get("/capture/enabled")
def capture_enabled():
    """Frontend uses this to decide whether to show the live-research UI."""
    return {"enabled": bool(settings.anthropic_api_key)}


@router.post("/capture/research", response_model=ResearchResponse)
def research(body: ResearchRequest):
    """Live Claude-assisted capture. Disabled (503) until ANTHROPIC_API_KEY is
    set — see app/services/capture_service.py. Returns drafts only; nothing is
    written here."""
    if not body.links:
        raise HTTPException(status_code=422, detail="Provide at least one link")
    try:
        drafts = capture_service.research_links(body.links, body.notes)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ResearchResponse(drafts=drafts)

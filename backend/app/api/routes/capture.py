from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.routes.resources import _to_out
from app.schemas.capture import BatchImportRequest, BatchImportResult
from app.services import resource_service

router = APIRouter()


@router.post("/resources/batch", response_model=BatchImportResult)
def batch_import(items: list[BatchImportRequest], db: Session = Depends(get_db)):
    """Upserts each resource on `link` — re-importing an existing link updates
    it in place instead of duplicating. Both capture paths (the current
    session-assisted flow and, later, live Claude research) call this one
    endpoint."""
    created, updated = [], []
    for item in items:
        resource, was_created = resource_service.upsert_resource(db, item)
        (created if was_created else updated).append(_to_out(resource))
    return BatchImportResult(created=created, updated=updated)


# Phase 7 (live Claude-assisted capture) adds a POST /capture/research route
# here: given raw links or a source site, it fetches each page, drafts a
# subject/grade/type/cost/UDL-tagged entry, and returns *draft, unsaved*
# resources for review — committed via the batch endpoint above, not directly.
# Not built yet: requires ANTHROPIC_API_KEY, intentionally blank until the
# user approves the spend (see backend/.env.example), same pattern as
# Chegga's coaching feature.

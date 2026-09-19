from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.resource import UdlCoverageOut
from app.services import resource_service

router = APIRouter()


@router.get("/udl-coverage", response_model=UdlCoverageOut)
def udl_coverage(
    q: str | None = None,
    subject: str | None = None,
    grade_band: str | None = None,
    tag: str | None = None,
    audience: str | None = None,
    db: Session = Depends(get_db),
):
    """For the current theme search, how many matching resources support each
    UDL principle (Engagement / Representation / Action & Expression) and each
    format. A thin principle is a gap the teacher still needs to fill."""
    return resource_service.udl_coverage(db, q, subject, grade_band, tag, audience)


@router.get("/stats")
def library_stats(db: Session = Depends(get_db)):
    """Library-wide coverage + blind-spot map: totals by subject / cost /
    scope / link status, the subject x UDL-principle matrix, and the
    thinnest cells. Powers the Stats page."""
    return resource_service.library_stats(db)

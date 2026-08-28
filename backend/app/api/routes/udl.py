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
    db: Session = Depends(get_db),
):
    """For the current theme search, how many matching resources support each
    UDL principle (Engagement / Representation / Action & Expression) and each
    format. A thin principle is a gap the teacher still needs to fill."""
    return resource_service.udl_coverage(db, q, subject, grade_band, tag)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.resource import NameCount
from app.services import resource_service

router = APIRouter()


def _as_counts(rows) -> list[NameCount]:
    return [NameCount(name=name, count=count) for name, count in rows]


@router.get("/subjects", response_model=list[NameCount])
def list_subjects(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_subjects_with_counts(db))


@router.get("/grade-bands", response_model=list[NameCount])
def list_grade_bands(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_grade_bands_with_counts(db))


@router.get("/resource-types", response_model=list[NameCount])
def list_resource_types(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_resource_types_with_counts(db))


@router.get("/audiences", response_model=list[NameCount])
def list_audiences(db: Session = Depends(get_db)):
    """'students' (lesson planning) vs 'educators' (professional learning)."""
    return _as_counts(resource_service.list_audiences_with_counts(db))


@router.get("/credit-types", response_model=list[NameCount])
def list_credit_types(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_credit_types_with_counts(db))


@router.get("/scopes", response_model=list[NameCount])
def list_scopes(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_scopes_with_counts(db))


@router.get("/publishers", response_model=list[NameCount])
def list_publishers(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_publishers_with_counts(db))


@router.get("/sources", response_model=list[NameCount])
def list_sources(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_sources_with_counts(db))


@router.get("/tags", response_model=list[NameCount])
def list_tags(db: Session = Depends(get_db)):
    return _as_counts(resource_service.list_tags_with_counts(db))


@router.get("/standards", response_model=list[NameCount])
def list_standards(db: Session = Depends(get_db)):
    """CCSS / NGSS / C3 codes parsed out of resources' `standards` text —
    so a teacher can jump straight to 'what covers CCSS.MATH.6.RP.A.3'."""
    return _as_counts(resource_service.list_standards_with_counts(db))

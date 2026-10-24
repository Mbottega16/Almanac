from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.resource import Resource
from app.schemas.resource import (
    ResourceCreate,
    ResourceListOut,
    ResourceOut,
    ResourceUpdate,
)
from app.services import resource_service

router = APIRouter()


def _to_out(resource: Resource) -> ResourceOut:
    return ResourceOut(
        id=resource.id,
        link=resource.link,
        title=resource.title,
        description=resource.description,
        description_source=resource.description_source,
        subject=resource.subject,
        grade_band=resource.grade_band,
        age_min=resource.age_min,
        age_max=resource.age_max,
        resource_type=resource.resource_type,
        scope=resource.scope,
        publisher=resource.publisher,
        duration_minutes=resource.duration_minutes,
        materials=resource.materials,
        learning_outcomes=resource_service.outcomes_to_list(resource.learning_outcomes),
        cost=resource.cost,
        price_note=resource.price_note,
        source_site=resource.source_site,
        license=resource.license,
        standards=resource.standards,
        granularity=resource.granularity,
        udl_rationale=resource.udl_rationale,
        audience=resource.audience or "students",
        credit_type=resource.credit_type,
        credit_hours=resource.credit_hours,
        credit_note=resource.credit_note,
        tags=[t.name for t in resource.tags],
        udl_principles=[p.name for p in resource.udl_principles],
        standard_codes=[s.code for s in resource.standards_rel],
        source=resource.source,
        link_status=resource.link_status,
        link_checked_at=resource.link_checked_at,
        visited_at=resource.visited_at,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


@router.get("/resources", response_model=ResourceListOut)
def search_resources(
    q: str | None = None,
    subject: str | None = None,
    grade_band: str | None = None,
    resource_type: str | None = None,
    scope: str | None = None,
    publisher: str | None = None,
    granularity: str | None = None,
    cost: str | None = None,
    source_site: str | None = None,
    udl: str | None = None,
    tag: str | None = None,
    standard: str | None = None,
    age: int | None = None,
    audience: str | None = None,
    credit_type: str | None = None,
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """`credit_type=any` returns everything that grants some credit.
    `limit` is capped: pages are fetched incrementally as the user scrolls,
    so no single response ever has to carry the whole library."""
    total, items, meta = resource_service.list_resources(
        db, q, subject, grade_band, resource_type, scope, publisher, granularity,
        cost, source_site, udl, tag, standard, age, limit, offset,
        audience=audience, credit_type=credit_type,
    )
    return ResourceListOut(
        total=total,
        items=[_to_out(r) for r in items],
        matched_terms=meta.get("matched_terms", []),
        unmatched_terms=meta.get("unmatched_terms", []),
        broadened=meta.get("broadened", False),
    )


@router.post("/resources", response_model=ResourceOut, status_code=201)
def create_resource(data: ResourceCreate, db: Session = Depends(get_db)):
    if resource_service.get_resource_by_link(db, data.link) is not None:
        raise HTTPException(status_code=409, detail="A resource with this link already exists")
    return _to_out(resource_service.create_resource(db, data))


@router.get("/resources/random", response_model=ResourceOut)
def random_resource(
    subject: str | None = None,
    tag: str | None = None,
    cost: str | None = None,
    db: Session = Depends(get_db),
):
    """Picks one random resource — powers the 'Surprise me' button. Optionally
    scoped so 'surprise me, but a free science one' works too."""
    resource = resource_service.random_resource(db, subject, tag, cost)
    if resource is None:
        raise HTTPException(status_code=404, detail="No resources match")
    return _to_out(resource)


@router.get("/resources/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = resource_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_out(resource)


@router.put("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: int, data: ResourceUpdate, db: Session = Depends(get_db)):
    resource = resource_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_out(resource_service.update_resource(db, resource, data))


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = resource_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource_service.delete_resource(db, resource)


@router.post("/resources/{resource_id}/visit", response_model=ResourceOut)
def visit_resource(resource_id: int, db: Session = Depends(get_db)):
    """Call this when the user actually opens the link (not on hover/search) —
    marks visited_at so the UI can show a 'visited' badge."""
    resource = resource_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_out(resource_service.mark_visited(db, resource))


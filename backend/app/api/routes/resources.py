from fastapi import APIRouter, Depends, HTTPException
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
        resource_type=resource.resource_type,
        cost=resource.cost,
        price_note=resource.price_note,
        source_site=resource.source_site,
        license=resource.license,
        standards=resource.standards,
        tags=[t.name for t in resource.tags],
        udl_principles=[p.name for p in resource.udl_principles],
        source=resource.source,
        is_favorite=resource.is_favorite,
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
    cost: str | None = None,
    source_site: str | None = None,
    udl: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    total, items = resource_service.list_resources(
        db, q, subject, grade_band, resource_type, cost, source_site, udl, tag,
        favorite, limit, offset,
    )
    return ResourceListOut(total=total, items=[_to_out(r) for r in items])


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


@router.post("/resources/{resource_id}/favorite", response_model=ResourceOut)
def favorite_resource(resource_id: int, favorite: bool = True, db: Session = Depends(get_db)):
    """Toggle 'saved to my collection'. `favorite=false` un-saves."""
    resource = resource_service.get_resource(db, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_out(resource_service.set_favorite(db, resource, favorite))

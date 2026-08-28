from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.resource import Resource, resource_tags, resource_udl
from app.models.tag import Tag
from app.models.udl import UDL_PRINCIPLES, UdlPrinciple


def _get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    tags = []
    for raw in names:
        name = raw.strip().lower()
        if not name:
            continue
        tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def _resolve_udl(db: Session, names: list[str]) -> list[UdlPrinciple]:
    """UDL principles are a fixed set — unknown names are dropped rather than
    created, so the lookup table stays exactly the three canonical rows."""
    wanted = {n.strip().lower() for n in names if n.strip().lower() in UDL_PRINCIPLES}
    if not wanted:
        return []
    return list(
        db.execute(select(UdlPrinciple).where(UdlPrinciple.name.in_(wanted))).scalars()
    )


def _base_query(
    q: str | None = None,
    subject: str | None = None,
    grade_band: str | None = None,
    resource_type: str | None = None,
    cost: str | None = None,
    source_site: str | None = None,
    udl: str | None = None,
    tag: str | None = None,
    favorite: bool | None = None,
):
    stmt = select(Resource)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Resource.title.ilike(like))
            | (Resource.description.ilike(like))
            | (Resource.link.ilike(like))
            | (Resource.standards.ilike(like))
        )
    if subject:
        stmt = stmt.where(Resource.subject == subject)
    if grade_band:
        stmt = stmt.where(Resource.grade_band == grade_band)
    if resource_type:
        stmt = stmt.where(Resource.resource_type == resource_type)
    if cost:
        stmt = stmt.where(Resource.cost == cost)
    if source_site:
        stmt = stmt.where(Resource.source_site == source_site)
    if tag:
        stmt = stmt.join(Resource.tags).where(Tag.name == tag.strip().lower())
    if udl:
        stmt = stmt.join(Resource.udl_principles).where(
            UdlPrinciple.name == udl.strip().lower()
        )
    if favorite is not None:
        stmt = stmt.where(Resource.is_favorite == favorite)
    return stmt


def list_resources(
    db: Session,
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
) -> tuple[int, list[Resource]]:
    stmt = _base_query(
        q, subject, grade_band, resource_type, cost, source_site, udl, tag, favorite
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(Resource.created_at.desc()).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars().unique())
    return total, items


def get_resource(db: Session, resource_id: int) -> Resource | None:
    return db.get(Resource, resource_id)


def random_resource(
    db: Session,
    subject: str | None = None,
    tag: str | None = None,
    cost: str | None = None,
) -> Resource | None:
    stmt = _base_query(subject=subject, tag=tag, cost=cost)
    stmt = stmt.order_by(func.random()).limit(1)
    return db.execute(stmt).scalars().unique().first()


def get_resource_by_link(db: Session, link: str) -> Resource | None:
    return db.execute(select(Resource).where(Resource.link == link)).scalar_one_or_none()


def create_resource(db: Session, data, source: str = "manual") -> Resource:
    resource = Resource(
        link=data.link,
        title=data.title,
        description=data.description,
        description_source=data.description_source,
        subject=data.subject,
        grade_band=data.grade_band,
        resource_type=data.resource_type,
        cost=data.cost,
        price_note=data.price_note,
        source_site=data.source_site,
        license=data.license,
        standards=data.standards,
        source=source,
    )
    resource.tags = _get_or_create_tags(db, data.tags)
    resource.udl_principles = _resolve_udl(db, data.udl_principles)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def update_resource(db: Session, resource: Resource, data) -> Resource:
    updates = data.model_dump(exclude_unset=True, exclude={"tags", "udl_principles"})
    for field, value in updates.items():
        setattr(resource, field, value)
    if data.tags is not None:
        resource.tags = _get_or_create_tags(db, data.tags)
    if data.udl_principles is not None:
        resource.udl_principles = _resolve_udl(db, data.udl_principles)
    db.commit()
    db.refresh(resource)
    return resource


def delete_resource(db: Session, resource: Resource) -> None:
    db.delete(resource)
    db.commit()


def mark_visited(db: Session, resource: Resource) -> Resource:
    resource.visited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource)
    return resource


def set_favorite(db: Session, resource: Resource, is_favorite: bool) -> Resource:
    resource.is_favorite = is_favorite
    db.commit()
    db.refresh(resource)
    return resource


def upsert_resource(db: Session, data, source: str = "capture") -> tuple[Resource, bool]:
    """Create, or update-in-place if `link` already exists. Returns
    (resource, created). Defaults to source='capture' — this is what the
    batch/import endpoint calls."""
    existing = get_resource_by_link(db, data.link)
    if existing is None:
        return create_resource(db, data, source=source), True
    existing.title = data.title
    existing.description = data.description
    existing.description_source = data.description_source
    existing.subject = data.subject
    existing.grade_band = data.grade_band
    existing.resource_type = data.resource_type
    existing.cost = data.cost
    existing.price_note = data.price_note
    existing.source_site = data.source_site
    existing.license = data.license
    existing.standards = data.standards
    existing.tags = _get_or_create_tags(db, data.tags)
    existing.udl_principles = _resolve_udl(db, data.udl_principles)
    db.commit()
    db.refresh(existing)
    return existing, False


# --- Faceted counts -------------------------------------------------------

def _column_counts(db: Session, column) -> list[tuple[str, int]]:
    stmt = (
        select(column, func.count(Resource.id))
        .where(column.is_not(None))
        .group_by(column)
        .order_by(column)
    )
    return list(db.execute(stmt).all())


def list_subjects_with_counts(db: Session) -> list[tuple[str, int]]:
    return _column_counts(db, Resource.subject)


def list_grade_bands_with_counts(db: Session) -> list[tuple[str, int]]:
    return _column_counts(db, Resource.grade_band)


def list_resource_types_with_counts(db: Session) -> list[tuple[str, int]]:
    return _column_counts(db, Resource.resource_type)


def list_sources_with_counts(db: Session) -> list[tuple[str, int]]:
    return _column_counts(db, Resource.source_site)


def list_tags_with_counts(db: Session) -> list[tuple[str, int]]:
    stmt = (
        select(Tag.name, func.count(resource_tags.c.resource_id))
        .join(resource_tags, resource_tags.c.tag_id == Tag.id)
        .group_by(Tag.name)
        .order_by(Tag.name)
    )
    return list(db.execute(stmt).all())


# --- UDL coverage -------------------------------------------------------

def udl_coverage(
    db: Session,
    q: str | None = None,
    subject: str | None = None,
    grade_band: str | None = None,
    tag: str | None = None,
) -> dict:
    """For a theme search, how many matching resources hit each UDL principle
    and each resource type — so a teacher can see at a glance which of the
    three principles is thin and needs filling."""
    match = _base_query(q=q, subject=subject, grade_band=grade_band, tag=tag).subquery()

    total = db.execute(select(func.count()).select_from(match)).scalar_one()

    per_principle = {name: 0 for name in UDL_PRINCIPLES}
    principle_stmt = (
        select(UdlPrinciple.name, func.count(func.distinct(match.c.id)))
        .select_from(match)
        .join(resource_udl, resource_udl.c.resource_id == match.c.id)
        .join(UdlPrinciple, UdlPrinciple.id == resource_udl.c.udl_principle_id)
        .group_by(UdlPrinciple.name)
    )
    for name, count in db.execute(principle_stmt).all():
        per_principle[name] = count

    by_type: dict[str, int] = {}
    type_stmt = (
        select(match.c.resource_type, func.count())
        .select_from(match)
        .where(match.c.resource_type.is_not(None))
        .group_by(match.c.resource_type)
        .order_by(func.count().desc())
    )
    for rtype, count in db.execute(type_stmt).all():
        by_type[rtype] = count

    return {
        "total": total,
        "engagement": per_principle["engagement"],
        "representation": per_principle["representation"],
        "action_expression": per_principle["action_expression"],
        "by_type": by_type,
    }

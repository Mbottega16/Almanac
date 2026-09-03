import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.resource import Resource, resource_tags, resource_udl
from app.models.standard import Standard, resource_standards
from app.models.tag import Tag
from app.models.udl import UDL_PRINCIPLES, UdlPrinciple
from app.services.links import canonical_link

# Pull recognisable standard codes out of the free-text `standards` field so
# they can become real filterable rows. Deliberately conservative — a code
# it doesn't recognise stays in the text column and just isn't filterable.
_STANDARD_PATTERNS = (
    # NGSS performance expectations: MS-LS1-1, 3-LS1-1, HS-PS2-4, K-ESS2-1
    ("NGSS", re.compile(r"\b(?:K|[1-5]|MS|HS)-[A-Z]{2,4}\d?-\d{1,2}\b")),
    # C3 Framework: D2.Civ.1.6-8, D2.His.3.9-12
    ("C3", re.compile(r"\bD[1-4]\.[A-Za-z]{2,4}\.\d{1,2}\.(?:K-2|3-5|6-8|9-12)\b")),
    # CCSS full form: CCSS.MATH.CONTENT.6.RP.A.3, CCSS.ELA-LITERACY.RL.6.1
    ("CCSS", re.compile(r"\bCCSS\.[A-Z-]+(?:\.[A-Z0-9]+){2,6}[a-z]?\b", re.I)),
    # CCSS loose form: 6.RP.A.3, K.CC.A.1, RL.6.1, W.7.2.b
    ("CCSS", re.compile(r"\b(?:K|\d{1,2}|[A-Z]{1,3})\.[A-Z]{1,3}(?:\.[A-Z0-9]+){1,4}[a-z]?\b")),
)


def extract_standard_codes(raw: str | None) -> list[tuple[str, str]]:
    """(framework, normalized code) pairs found in a free-text standards
    string. Deduped, order-preserving."""
    if not raw:
        return []
    seen: dict[str, str] = {}
    for framework, pat in _STANDARD_PATTERNS:
        for m in pat.findall(raw):
            code = m.upper().strip(". ")
            if len(code) >= 4 and code not in seen:
                seen[code] = framework
    # The loose CCSS pattern also matches the tail of a full "CCSS.x.y.z"
    # code — drop the bare duplicate when the full form is present.
    full = [c for c in seen if c.startswith("CCSS.")]
    for code in list(seen):
        if not code.startswith("CCSS.") and any(f.endswith("." + code) for f in full):
            del seen[code]
    return [(fw, code) for code, fw in seen.items()]

# When a source only gives a grade band, back-fill an age range from it so the
# `age` filter works library-wide. Rough but useful (US grade -> typical age).
GRADE_TO_AGE = {
    "PreK": (3, 5),
    "K-2": (5, 8),
    "3-5": (8, 11),
    "6-8": (11, 14),
    "9-12": (14, 18),
    "HigherEd/Adult": (18, 99),
    "All": (5, 18),
}

# Plain scalar columns copied straight from the payload on create/upsert.
_SCALAR_FIELDS = (
    "title", "description", "description_source", "subject", "grade_band",
    "age_min", "age_max", "resource_type", "scope", "publisher",
    "duration_minutes", "materials",
    "cost", "price_note", "source_site", "license", "standards",
    "granularity", "udl_rationale",
)


def _outcomes_to_str(outcomes: list[str] | None) -> str | None:
    if not outcomes:
        return None
    cleaned = [o.strip() for o in outcomes if o and o.strip()]
    return "\n".join(cleaned) or None


def outcomes_to_list(raw: str | None) -> list[str]:
    return [line for line in (raw or "").splitlines() if line.strip()]


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


def _get_or_create_standards(db: Session, raw: str | None) -> list[Standard]:
    out = []
    for framework, code in extract_standard_codes(raw):
        std = db.execute(select(Standard).where(Standard.code == code)).scalar_one_or_none()
        if std is None:
            std = Standard(code=code, framework=framework)
            db.add(std)
            db.flush()
        out.append(std)
    return out


def _resolve_udl(db: Session, names: list[str]) -> list[UdlPrinciple]:
    """UDL principles are a fixed set — unknown names are dropped rather than
    created, so the lookup table stays exactly the three canonical rows."""
    wanted = {n.strip().lower() for n in names if n.strip().lower() in UDL_PRINCIPLES}
    if not wanted:
        return []
    return list(
        db.execute(select(UdlPrinciple).where(UdlPrinciple.name.in_(wanted))).scalars()
    )


def _apply_fields(db: Session, resource: Resource, data) -> None:
    """Copy scalars + relationships + derived fields from a payload onto a
    Resource. Shared by create and upsert so they never drift apart."""
    for field in _SCALAR_FIELDS:
        setattr(resource, field, getattr(data, field))
    # Audit-only column: present on ResourceCreate, not on ResourceUpdate.
    if getattr(data, "evidence", None) is not None:
        resource.evidence = data.evidence
    resource.learning_outcomes = _outcomes_to_str(data.learning_outcomes)
    # Back-fill an age range from the grade band when the source didn't give one.
    if resource.age_min is None and resource.age_max is None and data.grade_band in GRADE_TO_AGE:
        resource.age_min, resource.age_max = GRADE_TO_AGE[data.grade_band]
    resource.tags = _get_or_create_tags(db, data.tags)
    resource.udl_principles = _resolve_udl(db, data.udl_principles)
    resource.standards_rel = _get_or_create_standards(db, data.standards)


def _base_query(
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
            | (Resource.learning_outcomes.ilike(like))
            | (Resource.materials.ilike(like))
            | (Resource.publisher.ilike(like))
        )
    if subject:
        stmt = stmt.where(Resource.subject == subject)
    if grade_band:
        stmt = stmt.where(Resource.grade_band == grade_band)
    if resource_type:
        stmt = stmt.where(Resource.resource_type == resource_type)
    if scope:
        stmt = stmt.where(Resource.scope == scope)
    if publisher:
        stmt = stmt.where(Resource.publisher == publisher)
    if granularity:
        stmt = stmt.where(Resource.granularity == granularity)
    if cost:
        stmt = stmt.where(Resource.cost == cost)
    if source_site:
        stmt = stmt.where(Resource.source_site == source_site)
    if age is not None:
        stmt = stmt.where(
            Resource.age_min.is_not(None),
            Resource.age_max.is_not(None),
            Resource.age_min <= age,
            Resource.age_max >= age,
        )
    if tag:
        stmt = stmt.join(Resource.tags).where(Tag.name == tag.strip().lower())
    if udl:
        stmt = stmt.join(Resource.udl_principles).where(
            UdlPrinciple.name == udl.strip().lower()
        )
    if standard:
        stmt = stmt.join(Resource.standards_rel).where(
            Standard.code == standard.strip().upper()
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
    scope: str | None = None,
    publisher: str | None = None,
    granularity: str | None = None,
    cost: str | None = None,
    source_site: str | None = None,
    udl: str | None = None,
    tag: str | None = None,
    standard: str | None = None,
    age: int | None = None,
    favorite: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[Resource]]:
    stmt = _base_query(
        q, subject, grade_band, resource_type, scope, publisher, granularity,
        cost, source_site, udl, tag, standard, age, favorite,
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
    return db.execute(
        select(Resource).where(Resource.link == canonical_link(link))
    ).scalar_one_or_none()


def create_resource(db: Session, data, source: str = "manual", commit: bool = True) -> Resource:
    resource = Resource(link=canonical_link(data.link), source=source)
    db.add(resource)  # in the session before _apply_fields flushes related rows
    _apply_fields(db, resource, data)
    if commit:
        db.commit()
        db.refresh(resource)
    else:
        db.flush()  # caller batches many creates into one transaction (seed load)
    return resource


def update_resource(db: Session, resource: Resource, data) -> Resource:
    updates = data.model_dump(
        exclude_unset=True, exclude={"tags", "udl_principles", "learning_outcomes"}
    )
    if "link" in updates and updates["link"]:
        updates["link"] = canonical_link(updates["link"])
    for field, value in updates.items():
        setattr(resource, field, value)
    if data.learning_outcomes is not None:
        resource.learning_outcomes = _outcomes_to_str(data.learning_outcomes)
    if data.tags is not None:
        resource.tags = _get_or_create_tags(db, data.tags)
    if data.udl_principles is not None:
        resource.udl_principles = _resolve_udl(db, data.udl_principles)
    if "standards" in updates:
        resource.standards_rel = _get_or_create_standards(db, resource.standards)
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


def upsert_resource(
    db: Session, data, source: str = "capture", commit: bool = True
) -> tuple[Resource, bool]:
    """Create, or update-in-place if `link` already exists. Returns
    (resource, created). Defaults to source='capture' — this is what the
    batch/import endpoint calls. Pass commit=False to batch many upserts
    into a single transaction (the seed loader does this)."""
    existing = get_resource_by_link(db, data.link)
    if existing is None:
        return create_resource(db, data, source=source, commit=commit), True
    _apply_fields(db, existing, data)
    if commit:
        db.commit()
        db.refresh(existing)
    else:
        db.flush()
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


def list_scopes_with_counts(db: Session) -> list[tuple[str, int]]:
    return _column_counts(db, Resource.scope)


def list_publishers_with_counts(db: Session) -> list[tuple[str, int]]:
    return _column_counts(db, Resource.publisher)


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


def list_standards_with_counts(db: Session) -> list[tuple[str, int]]:
    stmt = (
        select(Standard.code, func.count(resource_standards.c.resource_id))
        .join(resource_standards, resource_standards.c.standard_id == Standard.id)
        .group_by(Standard.code)
        .order_by(Standard.framework, Standard.code)
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

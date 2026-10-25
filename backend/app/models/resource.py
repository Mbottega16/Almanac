from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


resource_tags = Table(
    "resource_tags",
    Base.metadata,
    Column("resource_id", ForeignKey("resources.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

resource_udl = Table(
    "resource_udl",
    Base.metadata,
    Column("resource_id", ForeignKey("resources.id"), primary_key=True),
    Column("udl_principle_id", ForeignKey("udl_principles.id"), primary_key=True),
)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    link: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # How the description was produced: 'manual' (typed), 'excerpt' (pulled
    # from the source page, attributed), or 'generated' (AI summary).
    description_source: Mapped[str] = mapped_column(String, default="manual")

    subject: Mapped[str] = mapped_column(String, nullable=False, index=True)
    grade_band: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Age range the resource targets. Filled from grade_band when a source
    # only gives grades — see resource_service.GRADE_TO_AGE.
    age_min: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    age_max: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    resource_type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # How big a chunk of teaching this is:
    #   'lesson'     — a single class period / one-off activity (the default)
    #   'unit'       — a multi-lesson module on one topic
    #   'course'     — a full semester or year of one subject
    #   'curriculum' — a publisher's complete, multi-grade program
    # 'course' and 'curriculum' are usually a commercial product; pair with
    # `publisher` and (often) cost='paid'.
    scope: Mapped[str] = mapped_column(String, default="lesson", index=True)
    # The program / publisher behind a course or curriculum
    # ("Illustrative Mathematics", "OpenSciEd", "EL Education"). Null for
    # one-off lessons.
    publisher: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # What a teacher needs on hand to run it ("" / null = nothing / digital-only).
    materials: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Newline-separated "Students will be able to …" statements; the API
    # serialises this to/from a list[str].
    learning_outcomes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 'free' | 'paid' | 'freemium'
    cost: Mapped[str] = mapped_column(String, default="free", index=True)
    price_note: Mapped[str | None] = mapped_column(String, nullable=True)

    source_site: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    license: Mapped[str | None] = mapped_column(String, nullable=True)
    standards: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 'specific' — links one lesson/activity/video a teacher can use as-is.
    # 'collection' — links a browse/portal/library page, not a single resource.
    # Lets Browse hide the "here's a website, go dig" rows when a teacher
    # needs something class-ready today.
    granularity: Mapped[str] = mapped_column(String, default="specific", index=True)
    # Who the resource is for:
    #   'students'  — something you teach with (lessons, units, curricula)
    #   'educators' — the teacher's own professional learning (PD courses,
    #                 webinars, certifications)
    # A separate axis from `scope`, which measures the *size* of student-facing
    # content: a course you teach and a course you take are different searches.
    audience: Mapped[str] = mapped_column(String, default="students", index=True)
    # Credit a professional-learning resource grants, if any:
    # 'ceu' | 'pd_hours' | 'certificate' | 'graduate_credit'. Null = none.
    credit_type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    credit_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Who grants the credit and any catch ("certificate costs $10", "approved
    # for social workers — check your district for teacher renewal"). Credit
    # is easy to overstate; the qualifier lives here, next to the claim.
    credit_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # One short, attributed sentence quoted from the page at research time —
    # proof the resource is real (a row describing a page that doesn't exist
    # is worse than no row). Audit-only, never shown to users. Stays inside
    # the pointer-index rule: a brief attributed excerpt, <= 200 chars.
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Why each assigned UDL principle applies — one line per principle, e.g.
    # "representation: captions + transcript + diagrams". Surfaced on hover
    # so the coverage readout is auditable, not taken on faith.
    udl_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Link health, refreshed by scripts/flag_dead_links.py: 'unknown' (never
    # checked), 'ok', 'dead' (4xx/5xx or gone), 'redirect' (off-host bounce),
    # 'unreachable' (DNS/timeout from the checker — not proof it's dead).
    link_status: Mapped[str] = mapped_column(String, default="unknown", index=True)
    link_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Row provenance: 'manual' (typed in directly) or 'capture' (batch/import flow).
    source: Mapped[str] = mapped_column(String, default="manual")
    visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=resource_tags, back_populates="resources"
    )
    udl_principles: Mapped[list["UdlPrinciple"]] = relationship(
        secondary=resource_udl, back_populates="resources"
    )
    # Standard codes parsed out of the free-text `standards` field. See
    # app/models/standard.py and resource_service.extract_standard_codes.
    standards_rel: Mapped[list["Standard"]] = relationship(
        secondary="resource_standards", back_populates="resources"
    )

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
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

    # Row provenance: 'manual' (typed in directly) or 'capture' (batch/import flow).
    source: Mapped[str] = mapped_column(String, default="manual")
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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

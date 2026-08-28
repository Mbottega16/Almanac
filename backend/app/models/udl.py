from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# The three UDL principles are a fixed, closed set. They get a real lookup
# table + join (not a CSV column) because filtering "show me Representation
# resources for fractions" is a first-class feature — same reasoning as tags.
UDL_PRINCIPLES = ("engagement", "representation", "action_expression")


class UdlPrinciple(Base):
    __tablename__ = "udl_principles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    resources: Mapped[list["Resource"]] = relationship(
        secondary="resource_udl", back_populates="udl_principles"
    )


def seed_udl_principles(db) -> None:
    """Idempotently ensure the three fixed principle rows exist. Called on
    startup alongside Base.metadata.create_all."""
    from sqlalchemy import select

    existing = set(db.execute(select(UdlPrinciple.name)).scalars())
    for name in UDL_PRINCIPLES:
        if name not in existing:
            db.add(UdlPrinciple(name=name))
    db.commit()

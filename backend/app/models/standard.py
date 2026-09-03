from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Standard codes are parsed out of each resource's free-text `standards`
# field into their own rows + join — the same first-class-filter reasoning
# as tags and UDL principles. "What covers CCSS.MATH.6.RP.A.3" is how a lot
# of lesson planning actually starts; a substring match on a text column
# can't answer it cleanly.
resource_standards = Table(
    "resource_standards",
    Base.metadata,
    Column("resource_id", ForeignKey("resources.id"), primary_key=True),
    Column("standard_id", ForeignKey("standards.id"), primary_key=True),
)


class Standard(Base):
    __tablename__ = "standards"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The normalized code, e.g. "CCSS.MATH.CONTENT.6.RP.A.3", "MS-LS1-1",
    # "D2.CIV.1.6-8". Uppercased on write.
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    # 'CCSS' | 'NGSS' | 'C3' | 'OTHER' — for grouping in the facet list.
    framework: Mapped[str] = mapped_column(String, default="OTHER", index=True)

    resources: Mapped[list["Resource"]] = relationship(
        secondary=resource_standards, back_populates="standards_rel"
    )

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResourceBase(BaseModel):
    link: str
    title: str | None = None
    description: str | None = None
    description_source: str = "manual"
    subject: str
    grade_band: str | None = None
    age_min: int | None = None
    age_max: int | None = None
    resource_type: str | None = None
    scope: str = "lesson"
    publisher: str | None = None
    duration_minutes: int | None = None
    materials: str | None = None
    learning_outcomes: list[str] = []
    cost: str = "free"
    price_note: str | None = None
    source_site: str | None = None
    license: str | None = None
    standards: str | None = None
    granularity: str = "specific"
    udl_rationale: str | None = None
    audience: str = "students"
    credit_type: str | None = None
    credit_hours: float | None = None
    credit_note: str | None = None
    tags: list[str] = []
    udl_principles: list[str] = []


class ResourceCreate(ResourceBase):
    # Audit-only — accepted on write, never returned by ResourceOut. One
    # short attributed sentence quoted from the page (proof it's real).
    evidence: str | None = None


class ResourceUpdate(BaseModel):
    link: str | None = None
    title: str | None = None
    description: str | None = None
    description_source: str | None = None
    subject: str | None = None
    grade_band: str | None = None
    age_min: int | None = None
    age_max: int | None = None
    resource_type: str | None = None
    scope: str | None = None
    publisher: str | None = None
    duration_minutes: int | None = None
    materials: str | None = None
    learning_outcomes: list[str] | None = None
    cost: str | None = None
    price_note: str | None = None
    source_site: str | None = None
    license: str | None = None
    standards: str | None = None
    granularity: str | None = None
    evidence: str | None = None
    udl_rationale: str | None = None
    audience: str | None = None
    credit_type: str | None = None
    credit_hours: float | None = None
    credit_note: str | None = None
    tags: list[str] | None = None
    udl_principles: list[str] | None = None


class ResourceOut(ResourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    standard_codes: list[str] = []
    link_status: str
    link_checked_at: datetime | None
    visited_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResourceListOut(BaseModel):
    total: int
    items: list[ResourceOut]
    # Set only for a free-text search. `unmatched_terms` are words the library
    # has nothing for; `broadened` means those were dropped to answer at all.
    matched_terms: list[str] = []
    unmatched_terms: list[str] = []
    broadened: bool = False


class NameCount(BaseModel):
    name: str
    count: int


class UdlCoverageOut(BaseModel):
    total: int
    engagement: int
    representation: int
    action_expression: int
    by_type: dict[str, int]

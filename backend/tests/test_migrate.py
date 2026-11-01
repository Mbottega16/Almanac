"""Guard the persistent-DB migration: every new `resources` column needs an
`_ADDED_COLUMNS` entry, or an existing database 500s on every query.

`BASELINE_COLUMNS` is the schema that predates the migration mechanism. Adding
a column to `Resource` without listing it in `_ADDED_COLUMNS` fails the drift
test; the old-schema test proves the listed migrations really upgrade a table.
"""
from sqlalchemy import Column, MetaData, Table, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register every model on Base.metadata)
from app.db.base import Base
from app.db.migrate import _ADDED_COLUMNS, ensure_columns
from app.models.resource import Resource
from app.services.resource_service import list_resources

BASELINE_COLUMNS = frozenset({
    "id", "link", "title", "description", "description_source", "subject",
    "grade_band", "age_min", "age_max", "resource_type", "scope", "publisher",
    "duration_minutes", "materials", "learning_outcomes", "cost", "price_note",
    "source_site", "license", "standards", "granularity", "evidence",
    "udl_rationale", "link_status", "link_checked_at", "source", "visited_at",
    "created_at", "updated_at",
})


def _unmigrated_columns() -> list[str]:
    return sorted(
        c.name
        for c in Resource.__table__.columns
        if c.name not in BASELINE_COLUMNS and c.name not in _ADDED_COLUMNS
    )


def _old_resources_table() -> Table:
    """The `resources` table as it was before the _ADDED_COLUMNS work."""
    cols = [
        Column(c.name, c.type, primary_key=c.primary_key, unique=c.unique, nullable=c.nullable)
        for c in Resource.__table__.columns
        if c.name not in _ADDED_COLUMNS
    ]
    return Table("resources", MetaData(), *cols)


def test_every_new_resource_column_has_a_migration():
    assert _unmigrated_columns() == [], (
        "Resource columns missing from _ADDED_COLUMNS in app/db/migrate.py "
        "(a persistent DB would fail on them): " + ", ".join(_unmigrated_columns())
    )


def test_old_schema_upgrades_and_list_resources_runs():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[t for t in Base.metadata.sorted_tables if t.name != "resources"],
    )
    _old_resources_table().create(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO resources (link, subject, description_source, scope, cost, "
            "granularity, link_status, source, created_at, updated_at) VALUES "
            "('https://example.com/old', 'Math', 'manual', 'lesson', 'free', "
            "'specific', 'unknown', 'manual', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )

    assert set(ensure_columns(engine)) == set(_ADDED_COLUMNS)
    assert ensure_columns(engine) == []  # second boot is a no-op

    session = sessionmaker(bind=engine)()
    try:
        total, page, meta = list_resources(session)
        assert total == 1
        assert page[0].link == "https://example.com/old"
        assert page[0].audience == "students"  # backfilled by ensure_columns
        assert meta == {}
    finally:
        session.close()
        engine.dispose()

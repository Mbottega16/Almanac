"""Bring an existing SQLite database up to the current model at startup.

`Base.metadata.create_all` creates missing tables but never alters existing
ones, so a database built before a column was added would 500 on every query
touching `resources`. The earlier migrate_add_*.py scripts had to be run by
hand; this runs on every boot and is a no-op once the columns exist.

Only columns added after the persistent-DB work began are listed here, each
with the DDL default that makes existing rows valid.
"""
from sqlalchemy.engine import Engine

_ADDED_COLUMNS = {
    "audience": "VARCHAR DEFAULT 'students'",
    "credit_type": "VARCHAR",
    "credit_hours": "FLOAT",
    "credit_note": "TEXT",
}


def ensure_columns(engine: Engine) -> list[str]:
    if engine.dialect.name != "sqlite":
        return []
    added = []
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(resources)")}
        for name, decl in _ADDED_COLUMNS.items():
            if name not in existing:
                conn.exec_driver_sql(f"ALTER TABLE resources ADD COLUMN {name} {decl}")
                added.append(name)
        if "audience" in added:
            conn.exec_driver_sql("UPDATE resources SET audience = 'students' WHERE audience IS NULL")
    return added

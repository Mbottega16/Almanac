"""One-off, idempotent: add the 2026-08-30 deep-critique columns to an
existing `resources` table — granularity, evidence, udl_rationale,
link_status, link_checked_at. `Base.metadata.create_all` only creates new
tables, it doesn't alter existing ones. Only needed once there's a
persistent database — the Vercel `/tmp` DB is recreated from models on
every cold start.

Run from backend/:  .venv\\Scripts\\python scripts\\migrate_add_critique_fields.py
"""
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

db_path = settings.database_url.removeprefix("sqlite:///").removeprefix("/")
conn = sqlite3.connect(db_path)
cols = {r[1] for r in conn.execute("PRAGMA table_info(resources)")}

ADD = {
    "granularity": "VARCHAR DEFAULT 'specific'",
    "evidence": "TEXT",
    "udl_rationale": "TEXT",
    "link_status": "VARCHAR DEFAULT 'unknown'",
    "link_checked_at": "DATETIME",
}
for name, decl in ADD.items():
    if name not in cols:
        conn.execute(f"ALTER TABLE resources ADD COLUMN {name} {decl}")
        print("added", name)

conn.execute("UPDATE resources SET granularity = 'specific' WHERE granularity IS NULL")
conn.execute("UPDATE resources SET link_status = 'unknown' WHERE link_status IS NULL")
conn.commit()
conn.close()
print("done")

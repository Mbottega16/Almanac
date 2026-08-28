"""One-off, idempotent: add the lesson-format columns (age_min, age_max,
duration_minutes, materials, learning_outcomes) to an existing `resources`
table. `Base.metadata.create_all` only creates new tables, it doesn't alter
existing ones. Only needed once there's a persistent database — the Vercel
`/tmp` DB is recreated from models on every cold start.

Run from backend/:  .venv\\Scripts\\python scripts\\migrate_add_lesson_fields.py
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
    "age_min": "INTEGER",
    "age_max": "INTEGER",
    "duration_minutes": "INTEGER",
    "materials": "TEXT",
    "learning_outcomes": "TEXT",
}
for name, coltype in ADD.items():
    if name not in cols:
        conn.execute(f"ALTER TABLE resources ADD COLUMN {name} {coltype}")
        print("added", name)

conn.commit()
conn.close()
print("done")

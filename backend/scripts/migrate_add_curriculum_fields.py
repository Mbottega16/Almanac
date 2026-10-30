"""One-off, idempotent: add the curriculum columns (scope, publisher) to an
existing `resources` table. `Base.metadata.create_all` only creates new
tables, it doesn't alter existing ones. Only needed for a database created
before these columns existed. Render's DB is rebuilt from the seed on each
boot, so it never needs this.

Run from backend/:  .venv\\Scripts\\python scripts\\migrate_add_curriculum_fields.py
"""
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

db_path = settings.database_url.removeprefix("sqlite:///").removeprefix("/")
conn = sqlite3.connect(db_path)
cols = {r[1] for r in conn.execute("PRAGMA table_info(resources)")}

if "scope" not in cols:
    conn.execute("ALTER TABLE resources ADD COLUMN scope VARCHAR DEFAULT 'lesson'")
    conn.execute("UPDATE resources SET scope = 'lesson' WHERE scope IS NULL")
    print("added scope")
if "publisher" not in cols:
    conn.execute("ALTER TABLE resources ADD COLUMN publisher VARCHAR")
    print("added publisher")

conn.commit()
conn.close()
print("done")

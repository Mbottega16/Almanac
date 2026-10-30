"""Seeding for ephemeral deploys.

On Render's free plan there is no persistent disk, so the SQLite file is
rebuilt after every restart or deploy. Re-seeding 1,098 rows through per-row
commits is slow (about 13 ms per row, so roughly 14 s at this size). Two
speed-ups here:

1. `ensure_seed_db_file()` — if a pre-built `seed/almanac-seed.db` exists and
   the target SQLite file is missing, just copy the file. That's milliseconds
   instead of seconds. The file is not in git: the Render build runs
   `scripts/build_seed_db.py` to make it from the JSON seed.
2. `load_seed_rows()` — the JSON fallback, but as ONE transaction instead of
   1,098 commits.

The real fix is a persistent database (see context.md); this keeps the
restart path fast until then.
"""
import json
import pathlib
import shutil

from sqlalchemy.orm import Session

from app.config import settings

_BACKEND_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SEED_JSON = _BACKEND_ROOT / "seed" / "almanac-seed.json"
SEED_DB = _BACKEND_ROOT / "seed" / "almanac-seed.db"


def _sqlite_path() -> pathlib.Path | None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        return None
    # sqlite:///relative or sqlite:////absolute
    raw = url.split("sqlite:///", 1)[1]
    return pathlib.Path(raw)


def ensure_seed_db_file() -> bool:
    """If the target is a SQLite file that doesn't exist yet and a pre-built
    seed DB is committed, copy it into place. Returns True if it did."""
    target = _sqlite_path()
    if target is None or target.exists() or not SEED_DB.exists():
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SEED_DB, target)
        return True
    except OSError:
        return False


def load_seed_rows(db: Session) -> int:
    """Fallback: load the JSON seed in a single transaction. Returns row count."""
    from app.schemas.resource import ResourceCreate
    from app.services import resource_service

    if not SEED_JSON.exists():
        return 0
    rows = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    for row in rows:
        resource, _ = resource_service.upsert_resource(
            db, ResourceCreate(**row), commit=False
        )
        # link_status is a system field (set by scripts/flag_dead_links.py),
        # not part of the create schema — carry it through from the seed row.
        if row.get("link_status"):
            resource.link_status = row["link_status"]
    db.commit()
    return len(rows)

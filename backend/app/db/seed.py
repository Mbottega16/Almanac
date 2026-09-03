"""Seeding for ephemeral deploys.

On Vercel the SQLite file lives in `/tmp` and is wiped on every cold start,
so the app re-seeds constantly. Re-seeding 289 rows through per-row commits
took ~8s locally and was tripping the serverless function timeout
(intermittent 504s). Two speed-ups here:

1. `ensure_seed_db_file()` — if a committed, pre-built `seed/almanac-seed.db`
   exists and the target SQLite file is missing, just copy the file. That's
   milliseconds instead of seconds. Build it with `scripts/build_seed_db.py`.
2. `load_seed_rows()` — the JSON fallback, but as ONE transaction instead of
   289 commits.

The real fix is a persistent database (see context.md); this keeps the
serverless deploy from timing out until then.
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

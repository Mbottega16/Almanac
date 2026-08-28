"""Load backend/seed/almanac-seed.json into the database via the same
upsert path the batch endpoint uses. Idempotent — re-running updates rows
on `link` rather than duplicating.

Run from backend/:  .venv\\Scripts\\python scripts\\import_seed.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import models as _models  # noqa: F401  (register models on Base.metadata)
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.udl import seed_udl_principles
from app.schemas.resource import ResourceCreate
from app.services import resource_service

SEED = pathlib.Path(__file__).resolve().parent.parent / "seed" / "almanac-seed.json"


def main() -> None:
    rows = json.loads(SEED.read_text(encoding="utf-8"))
    Base.metadata.create_all(bind=engine)
    created = updated = 0
    with SessionLocal() as db:
        seed_udl_principles(db)
        for row in rows:
            _, was_created = resource_service.upsert_resource(db, ResourceCreate(**row))
            if was_created:
                created += 1
            else:
                updated += 1
    print(f"seed import: {created} created, {updated} updated ({len(rows)} rows)")


if __name__ == "__main__":
    main()

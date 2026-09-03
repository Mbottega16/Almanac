"""Build backend/seed/almanac-seed.db from backend/seed/almanac-seed.json.

Commit the resulting .db file. On an ephemeral serverless deploy the app
copies it into place on cold start (milliseconds) instead of re-inserting
the JSON seed row-by-row (~8s, which was tripping the function timeout).

Run from backend/ after any change to almanac-seed.json:
  PYTHONPATH=. .venv/Scripts/python scripts/build_seed_db.py
"""
import pathlib
import time

BACKEND = pathlib.Path(__file__).resolve().parent.parent
SEED_DB = BACKEND / "seed" / "almanac-seed.db"


def main() -> None:
    if SEED_DB.exists():
        SEED_DB.unlink()

    # Point the app at the seed file, then reuse the normal bootstrap path.
    import os

    os.environ["DATABASE_URL"] = f"sqlite:///{SEED_DB.as_posix()}"

    t = time.time()
    from app import models as _models  # noqa: F401  (register every model on Base.metadata)
    from app.db.base import Base
    from app.db.session import SessionLocal, engine
    from app.db.seed import load_seed_rows
    from app.models.resource import Resource
    from app.models.udl import seed_udl_principles

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_udl_principles(db)
        n = load_seed_rows(db)
        total = db.query(Resource).count()

    print(f"built {SEED_DB.relative_to(BACKEND.parent)} — {n} rows in, {total} in db, {time.time() - t:.2f}s")
    print(f"size: {SEED_DB.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()

"""Build backend/seed/almanac-seed.db from backend/seed/almanac-seed.json.

The .db file is a build artifact. It is git-ignored: the JSON is the library,
and the deploy builds the database from it (render.yaml `buildCommand`). On
start the app copies the built file into place (milliseconds) instead of
re-inserting the JSON seed row-by-row.

Run from backend/ (locally, only if you want the prebuilt file):
  .venv/Scripts/python scripts/build_seed_db.py
"""
import pathlib
import sys
import time

BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))  # so `import app` works without PYTHONPATH
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

    # Ship the file without its search index. The index roughly doubles the
    # file, and this file is re-committed on every content change, so it
    # would double the repo's growth too. The app rebuilds it on boot when
    # it's missing (app.main._bootstrap) — ~130 ms at 385 rows.
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS resources_fts")
    with engine.connect() as conn:
        conn.exec_driver_sql("VACUUM")
    engine.dispose()

    print(f"built {SEED_DB.relative_to(BACKEND.parent)} — {n} rows in, {total} in db, {time.time() - t:.2f}s")
    print(f"size: {SEED_DB.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()

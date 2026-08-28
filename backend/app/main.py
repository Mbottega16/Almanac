import logging
import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models as _models  # noqa: F401  (register models on Base.metadata)
from app.api.routes import auth, capture, facets, health, resources, udl
from app.auth import AuthGateMiddleware
from app.db.base import Base
from app.db.seed import ensure_seed_db_file, load_seed_rows
from app.db.session import SessionLocal, engine
from app.models.resource import Resource
from app.models.udl import seed_udl_principles

log = logging.getLogger("almanac.bootstrap")

app = FastAPI(title="Almanac")

# On an ephemeral serverless filesystem the SQLite file in /tmp is gone on
# every cold start. Copying a pre-built seed DB into place (milliseconds)
# instead of re-inserting the JSON seed row-by-row (~8s, was tripping the
# function timeout) is what keeps cold starts fast. Must run before
# create_all and any query.
ensure_seed_db_file()

# MVP: create tables directly from models. Switch to Alembic migrations
# once the schema needs to evolve without dropping data.
Base.metadata.create_all(bind=engine)


def _bootstrap() -> None:
    # Never let a seeding hiccup take down module import (would 500 every route).
    try:
        with SessionLocal() as db:
            seed_udl_principles(db)
            if db.query(Resource).count() == 0:
                n = load_seed_rows(db)
                log.warning("cold DB: loaded %d seed rows via JSON fallback", n)
    except Exception:  # noqa: BLE001
        log.exception("bootstrap seeding failed; continuing with current DB state")


_bootstrap()

# The frontend is deployed separately (Vercel), so the API accepts cross-origin
# requests. Wide open — a single-user tool. The real protection is the auth
# gate below (dormant until ADMIN_PASSWORD is set); see app/auth.py.
# allow_origin_regex (not allow_origins=["*"]) so the browser still accepts
# responses when the frontend sends the auth-gate cookie cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(AuthGateMiddleware)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(facets.router, prefix="/api")
app.include_router(udl.router, prefix="/api")
app.include_router(capture.router, prefix="/api")

# One-service deployment: if a built frontend is present, serve it at / so the
# whole app lives behind a single origin (and /api calls are same-origin, no
# CORS). `backend/static/` is produced by `scripts/build_frontend.py`.
_STATIC = pathlib.Path(__file__).resolve().parent.parent / "static"
if (_STATIC / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="frontend")

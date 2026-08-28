from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401  (register models on Base.metadata)
from app.api.routes import capture, facets, health, resources, udl
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.udl import seed_udl_principles

app = FastAPI(title="Almanac")

# MVP: create tables directly from models. Switch to Alembic migrations
# once the schema needs to evolve without dropping data.
Base.metadata.create_all(bind=engine)

# The three UDL principles are a fixed lookup — make sure they exist.
with SessionLocal() as _db:
    seed_udl_principles(_db)

# Frontend is hosted separately (Vercel) for now, so the API accepts
# cross-origin requests. Wide open — this is a single-user tool with no auth
# gate yet. Tighten to the exact frontend domain, or add real auth, before
# this is anything but personal (see CLAUDE.md, Phase 5).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(facets.router, prefix="/api")
app.include_router(udl.router, prefix="/api")
app.include_router(capture.router, prefix="/api")

# Phase 6 (deployment): mount the built frontend/dist/ here via StaticFiles
# so one Render Web Service can serve both /api/* and the app itself.

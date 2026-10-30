"""LEGACY Vercel fallback entrypoint — exposes the FastAPI ASGI app.

Not used by the live site. Render runs `uvicorn app.main:app` as a single
web service (see render.yaml). This file stays only so the old
`almanac-api.vercel.app` project can still serve the app: Vercel's Python
runtime serves the module-level `app` directly, with no uvicorn process.
Local dev uses `uvicorn app.main:app` (see README).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401

"""Vercel Python entrypoint — exposes the FastAPI ASGI app.

Vercel's Python runtime serves the module-level `app` directly; there is no
uvicorn process in that environment. Local dev still uses
`uvicorn app.main:app` (see README).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401

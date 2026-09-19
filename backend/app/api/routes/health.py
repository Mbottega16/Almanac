from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import search

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Open (no login). Reports which search engine is live — 'fts5' is the
    indexed path; 'python' means the host's SQLite lacks FTS5 and search is
    running on the slow per-row fallback, which needs fixing before the
    library grows."""
    return {
        "status": "ok",
        "search": search.backend_name(db),
        "indexed": search.index_size(db),
    }

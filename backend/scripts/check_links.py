"""Check every resource.link for reachability and print a report of the ones
that look broken (connection errors, 4xx/5xx, or a redirect to a different
host). Read-only — it never edits the DB; use the output to fix resources by
hand, via the update endpoint, or in backend/seed/almanac-seed.json.

Ported from Atlas's identical script (swap Entry -> Resource).

Run from backend/ with the venv:
  PYTHONPATH=. .venv/Scripts/python scripts/check_links.py
Check the committed seed DB instead of the local dev DB:
  DATABASE_URL=sqlite:///seed/almanac-seed.db PYTHONPATH=. .venv/Scripts/python scripts/check_links.py
Options:
  --timeout N   per-request timeout in seconds (default 12)
  --limit N     only check the first N resources (for a quick sample)
"""
import concurrent.futures
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from app.db.session import SessionLocal
from app.models.resource import Resource

UA = "Mozilla/5.0 (compatible; AlmanacLinkCheck/1.0)"


def _arg(name: str, default: int) -> int:
    if name in sys.argv:
        return int(sys.argv[sys.argv.index(name) + 1])
    return default


def _host(url: str) -> str:
    """Registrable-ish host for comparison: lowercase, strip a leading www."""
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def check(row: tuple[int, str, str | None], timeout: int) -> str | None:
    resource_id, link, title = row
    req = urllib.request.Request(link, method="GET", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final = resp.geturl()
            # A www/non-www, http/https, or trailing-slash bounce is normal —
            # only an actual host change (or a bounce to a bare homepage from a
            # deep link) is worth a look.
            if _host(final) != _host(link):
                return f"[redirect] #{resource_id} {title or ''}\n    {link}\n -> {final}"
            src_deep = len(urlsplit(link).path.strip("/")) > 0
            dst_bare = len(urlsplit(final).path.strip("/")) == 0
            if src_deep and dst_bare:
                return f"[bounced to homepage] #{resource_id} {title or ''}\n    {link}\n -> {final}"
            return None
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 429, 999):  # anti-bot noise, not really dead
            return None
        return f"[HTTP {e.code}] #{resource_id} {title or ''}\n    {link}"
    except Exception as e:  # noqa: BLE001 — timeout, DNS, SSL, connection reset
        return f"[{type(e).__name__}] #{resource_id} {title or ''}\n    {link}"


def main() -> None:
    timeout = _arg("--timeout", 12)
    limit = _arg("--limit", 0)

    db = SessionLocal()
    try:
        q = db.query(Resource.id, Resource.link, Resource.title).order_by(Resource.id)
        rows = q.limit(limit).all() if limit else q.all()
    finally:
        db.close()

    print(f"checking {len(rows)} links (timeout {timeout}s)…\n")
    problems: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for result in pool.map(lambda r: check(tuple(r), timeout), rows):
            if result:
                problems.append(result)
                print(result)

    print(f"\n{len(problems)} of {len(rows)} links need a look")


if __name__ == "__main__":
    main()

"""Check every resource.link for reachability and classify its health.

Ported from Atlas's script (swap Entry -> Resource), then extended with a
machine-readable mode and a write-back mode for the `link_status` column.

Status values: 'ok', 'dead' (4xx/5xx or gone), 'redirect' (off-host bounce),
'bounced' (deep link -> a bare homepage), 'unreachable' (DNS/timeout from
the checker — NOT proof it's dead; this build environment can't resolve a
lot of live education domains).

Run from backend/ with the venv:
  PYTHONPATH=. .venv/Scripts/python scripts/check_links.py
Against the library itself (seed/almanac-seed.json), with no database and no
app imports — this is the mode the weekly GitHub Action uses:
  python scripts/check_links.py --seed [--write-status]

Options:
  --timeout N      per-request timeout in seconds (default 12)
  --limit N        only check the first N resources (quick sample)
  --json           emit a JSON array [{id, link, status, detail}] instead of the report
  --write          write status + link_checked_at back to the DB (implies a real run)
  --seed           read seed/almanac-seed.json instead of the DB
  --write-status   (with --seed) record each result in seed/link-status.json, counting
                   consecutive real-4xx failures per link, then set `link_status` on the
                   seed rows. A link is marked 'dead' only after it fails twice in a row,
                   so one bad night on the checker's side never flags a live site.
"""
import concurrent.futures
import datetime
import json
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import certifi

# `app` is imported lazily (see _rows / main) so --seed mode runs on a bare
# `pip install certifi` — that is all the weekly GitHub Action installs.

UA = "Mozilla/5.0 (compatible; AlmanacLinkCheck/1.0)"
_ANTIBOT = {401, 403, 405, 429, 999}  # a response, but a bot-block — not "dead"
# Default Windows Python has no CA bundle wired into `ssl`, so every site
# needing chain validation was falsely flagged "unreachable"
# (CERTIFICATE_VERIFY_FAILED) — use certifi's bundle explicitly.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_RETRIES = 2  # DNS timeouts/resets are often transient, not proof of death


def _arg(name: str, default: int) -> int:
    if name in sys.argv:
        return int(sys.argv[sys.argv.index(name) + 1])
    return default


def _domain(url: str) -> str:
    """Registrable-ish domain: the last two labels, lowercased. Collapses
    www/non-www and regional affiliate subdomains (mpt.pbslearningmedia.org
    == pbslearningmedia.org) so only a real host change trips 'redirect'."""
    labels = (urlsplit(url).hostname or "").lower().split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else ".".join(labels)


def classify(link: str, timeout: int) -> tuple[str, str]:
    """Return (status, detail). status in ok/dead/redirect/bounced/unreachable."""
    req = urllib.request.Request(link, method="GET", headers={"User-Agent": UA})
    last_exc_name = ""
    for attempt in range(_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT) as resp:
                final = resp.geturl()
                if _domain(final) != _domain(link):
                    return "redirect", f"-> {final}"
                if urlsplit(link).path.strip("/") and not urlsplit(final).path.strip("/"):
                    return "bounced", f"-> {final}"
                return "ok", ""
        except urllib.error.HTTPError as e:
            if e.code in _ANTIBOT:
                return "ok", f"HTTP {e.code} (anti-bot, treated as ok)"
            if e.code >= 500:
                # server-side, usually transient — not proof the page is gone
                return "unreachable", f"HTTP {e.code}"
            return "dead", f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001 — timeout, DNS, SSL, connection reset
            last_exc_name = type(e).__name__
            if attempt + 1 < _RETRIES:
                time.sleep(1)
    return "unreachable", last_exc_name


SEED_DIR = pathlib.Path(__file__).resolve().parent.parent / "seed"
SEED_FILE = SEED_DIR / "almanac-seed.json"
STATUS_FILE = SEED_DIR / "link-status.json"
# Only a real 4xx counts against a link. "unreachable" (DNS, timeout, reset)
# says as much about the checker's network as about the site.
_FAILING = {"dead"}


def _seed_rows(limit: int) -> list[tuple[int, str, str | None]]:
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    triples = [(i, r["link"], r.get("title")) for i, r in enumerate(rows)]
    return triples[:limit] if limit else triples


def write_status(results: list[dict]) -> None:
    """Merge results into link-status.json and mirror them onto the seed rows.

    `fails` counts consecutive failing checks; a passing check resets it. A seed
    row gets link_status 'dead' only at fails >= 2. A first failure leaves the
    row's current status alone, so one bad night changes nothing the site shows.
    """
    old = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}
    today = datetime.date.today().isoformat()
    new = {}
    for r in results:
        fails = old.get(r["link"], {}).get("fails", 0) + 1 if r["status"] in _FAILING else 0
        new[r["link"]] = {"status": r["status"], "detail": r["detail"], "checked": today, "fails": fails}
    STATUS_FILE.write_text(json.dumps(dict(sorted(new.items())), indent=1) + "\n", encoding="utf-8")

    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    for row in rows:
        v = new.get(row["link"])
        if v is None:
            continue
        if v["status"] in _FAILING:
            if v["fails"] >= 2:
                row["link_status"] = "dead"
        else:
            row["link_status"] = v["status"]
    SEED_FILE.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    flagged = sum(1 for v in new.values() if v["fails"] >= 2)
    print(f"{STATUS_FILE.name}: {len(new)} links, {flagged} failing twice or more")


def _rows(limit: int) -> list[tuple[int, str, str | None]]:
    from app.db.session import SessionLocal
    from app.models.resource import Resource

    db = SessionLocal()
    try:
        q = db.query(Resource.id, Resource.link, Resource.title).order_by(Resource.id)
        return [tuple(r) for r in (q.limit(limit).all() if limit else q.all())]
    finally:
        db.close()


def main() -> None:
    timeout = _arg("--timeout", 12)
    limit = _arg("--limit", 0)
    as_json = "--json" in sys.argv
    write = "--write" in sys.argv
    seed = "--seed" in sys.argv

    rows = _seed_rows(limit) if seed else _rows(limit)
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        statuses = pool.map(lambda r: classify(r[1], timeout), rows)
        for (rid, link, title), (status, detail) in zip(rows, statuses):
            results.append({"id": rid, "link": link, "title": title,
                            "status": status, "detail": detail})

    if seed and "--write-status" in sys.argv:
        write_status(results)

    if write:
        from app.db.session import SessionLocal
        from app.models.resource import Resource

        now = datetime.datetime.now(datetime.timezone.utc)
        db = SessionLocal()
        try:
            for r in results:
                db.query(Resource).filter(Resource.id == r["id"]).update(
                    {"link_status": r["status"], "link_checked_at": now}
                )
            db.commit()
        finally:
            db.close()

    if as_json:
        print(json.dumps(results, indent=1))
        return

    bad = [r for r in results if r["status"] != "ok"]
    for r in bad:
        print(f'[{r["status"]}] #{r["id"]} {r["title"] or ""}\n    {r["link"]}  {r["detail"]}')
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f'\n{len(bad)} of {len(results)} need a look  |  {counts}')
    if write:
        print("(wrote link_status + link_checked_at back to the DB)")


if __name__ == "__main__":
    main()

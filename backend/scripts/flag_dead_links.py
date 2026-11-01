"""Check every link in backend/seed/almanac-seed.json and write a
`link_status` onto each row, so the committed seed carries link health and
the frontend can badge a known-broken row instead of sending a teacher to
a 404.

This is a thin wrapper over `check_links.write_status`, the one code path that
writes link_status. It applies the same two-strike rule as the weekly Action:
a row goes 'dead' only after two consecutive real-4xx failures (tracked in
backend/seed/link-status.json). A first failure leaves the row's status alone.

Status: 'ok' | 'dead' | 'redirect' | 'bounced' | 'unreachable'. Only 'dead'
should drive a user-facing warning — 'unreachable' means the checker's
network couldn't resolve the host, which is common for live education
domains from a CI/build box, not proof the link is broken.

Run from backend/:
  PYTHONPATH=. .venv/Scripts/python scripts/flag_dead_links.py [--timeout N]
Then rebuild the seed DB:  PYTHONPATH=. .venv/Scripts/python scripts/build_seed_db.py
"""
import concurrent.futures
import json
import sys

from scripts.check_links import SEED_FILE, classify, write_status


def main() -> None:
    timeout = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 15
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(lambda r: classify(r["link"], timeout), rows))

    results = [
        {"link": r["link"], "title": r.get("title"), "status": status, "detail": detail}
        for r, (status, detail) in zip(rows, statuses)
    ]
    write_status(results)

    for r in json.loads(SEED_FILE.read_text(encoding="utf-8")):
        if r.get("link_status") == "dead":
            print(f'  DEAD  {r["link"]}  ({r["title"]})')


if __name__ == "__main__":
    main()

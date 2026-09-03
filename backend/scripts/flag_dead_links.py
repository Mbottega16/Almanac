"""Check every link in backend/seed/almanac-seed.json and write a
`link_status` onto each row, so the committed seed carries link health and
the frontend can badge a known-broken row instead of sending a teacher to
a 404.

Status: 'ok' | 'dead' | 'redirect' | 'bounced' | 'unreachable'. Only 'dead'
should drive a user-facing warning — 'unreachable' means the checker's
network couldn't resolve the host, which is common for live education
domains from a CI/build box, not proof the link is broken.

Run from backend/:
  PYTHONPATH=. .venv/Scripts/python scripts/flag_dead_links.py [--timeout N]
Then rebuild the seed DB:  PYTHONPATH=. .venv/Scripts/python scripts/build_seed_db.py
"""
import collections
import concurrent.futures
import json
import pathlib
import sys

from scripts.check_links import classify

SEED = pathlib.Path(__file__).resolve().parent.parent / "seed" / "almanac-seed.json"


def main() -> None:
    timeout = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 15
    rows = json.loads(SEED.read_text(encoding="utf-8"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(lambda r: classify(r["link"], timeout), rows))

    for row, (status, _detail) in zip(rows, statuses):
        row["link_status"] = status

    SEED.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = collections.Counter(s for s, _ in statuses)
    print(f"{len(rows)} links checked -> {dict(counts)}")
    dead = [r for r in rows if r["link_status"] == "dead"]
    for r in dead:
        print(f'  DEAD  {r["link"]}  ({r["title"]})')


if __name__ == "__main__":
    main()

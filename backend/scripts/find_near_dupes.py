"""Print clusters of resources that look like the same thing entered twice.
`link` is UNIQUE and canonicalized on write, so exact and http/https/www
dupes can't happen any more — this catches the softer cases: two rows on
the same site with near-identical titles, or two links whose path is the
same once IDs/locale segments are stripped.

Read-only. Run from backend/:
  PYTHONPATH=. .venv/Scripts/python scripts/find_near_dupes.py
"""
import collections
import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from app.db.session import SessionLocal
from app.models.resource import Resource
from app.services.links import canonical_link

_LOCALE = re.compile(r"^(en|en-us|en-gb|us|www)$", re.I)


def _norm_title(t: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower()).strip()


def _norm_path(link: str) -> str:
    parts = urlsplit(canonical_link(link))
    segs = [s for s in parts.path.split("/") if s and not _LOCALE.match(s)]
    return parts.hostname + "/" + "/".join(segs).lower()


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.query(Resource.id, Resource.link, Resource.title, Resource.source_site).all()
    finally:
        db.close()

    clusters: list[list] = []

    # same normalized path
    by_path = collections.defaultdict(list)
    for r in rows:
        by_path[_norm_path(r.link)].append(r)
    clusters += [g for g in by_path.values() if len(g) > 1]

    # same source_site + very similar title
    by_site = collections.defaultdict(list)
    for r in rows:
        if r.source_site:
            by_site[r.source_site].append(r)
    for group in by_site.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                ta, tb = _norm_title(a.title), _norm_title(b.title)
                # ignore grade/level numbers so "... Grade 3" vs "... Grade 6"
                # (a real series, not a dupe) doesn't match
                stripped_equal = re.sub(r"\d+", "", ta).split() == re.sub(r"\d+", "", tb).split()
                if SequenceMatcher(None, ta, tb).ratio() > 0.92 and not (
                    stripped_equal and ta != tb
                ):
                    clusters.append([a, b])

    seen: set[frozenset] = set()
    n = 0
    for c in clusters:
        key = frozenset(r.id for r in c)
        if key in seen:
            continue
        seen.add(key)
        n += 1
        print(f"\ncluster {n}:")
        for r in c:
            print(f"  #{r.id}  {r.title}\n        {r.link}")
    print(f"\n{n} possible near-duplicate cluster(s)")


if __name__ == "__main__":
    main()

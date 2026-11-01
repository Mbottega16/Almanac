"""Score UDL principle tag coverage in the seed library.

Reads the seed JSON and reports, for each UDL principle (Engagement,
Representation, Action & Expression), how many resources carry it and in
which formats. Exits 1 if a principle has no tagged resources or if any
resource has no principle at all, so it can gate a harvest PR.

Usage (from the backend folder):
    .venv/bin/python scripts/udl_score.py [path/to/almanac-seed.json]
"""

import json
import pathlib
import sys
from collections import Counter

PRINCIPLES = ("engagement", "representation", "action_expression")
DEFAULT_SEED = pathlib.Path(__file__).resolve().parent.parent / "seed" / "almanac-seed.json"


def score(rows: list[dict]) -> dict:
    """Return per-principle counts, format breakdown, and untagged rows."""
    per_principle = {p: 0 for p in PRINCIPLES}
    formats: dict[str, Counter] = {p: Counter() for p in PRINCIPLES}
    untagged: list[str] = []
    unknown: Counter = Counter()

    for row in rows:
        tags = row.get("udl_principles") or []
        known = [t for t in tags if t in PRINCIPLES]
        for t in tags:
            if t not in PRINCIPLES:
                unknown[t] += 1
        if not known:
            untagged.append(row.get("link", "?"))
            continue
        fmt = row.get("resource_type") or "unspecified"
        for p in known:
            per_principle[p] += 1
            formats[p][fmt] += 1

    return {
        "total": len(rows),
        "per_principle": per_principle,
        "formats": formats,
        "untagged": untagged,
        "unknown": unknown,
    }


def problems(result: dict) -> list[str]:
    """Human-readable reasons the library fails the UDL check."""
    out = []
    for p in PRINCIPLES:
        if result["per_principle"][p] == 0:
            out.append(f"no resources tagged {p}")
    if result["untagged"]:
        out.append(f"{len(result['untagged'])} resources have no UDL principle")
    if result["unknown"]:
        out.append(f"unknown principle names: {dict(result['unknown'])}")
    return out


def main(argv: list[str]) -> int:
    path = pathlib.Path(argv[1]) if len(argv) > 1 else DEFAULT_SEED
    rows = json.loads(path.read_text(encoding="utf-8"))
    result = score(rows)
    total = result["total"]
    print(f"{total} resources in {path.name}")
    for p in PRINCIPLES:
        n = result["per_principle"][p]
        pct = (100 * n / total) if total else 0.0
        top = ", ".join(f"{f} {c}" for f, c in result["formats"][p].most_common(3))
        print(f"  {p:<20} {n:>5} ({pct:4.1f}%)  top formats: {top or '-'}")
    issues = problems(result)
    for issue in issues:
        print(f"FAIL: {issue}")
    if not issues:
        print("PASS: every principle is covered and every resource has one")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

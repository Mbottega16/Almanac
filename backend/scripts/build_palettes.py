"""Extract a colour palette from every resource's favicon.

Card headers use a gradient drawn from the site's own icon, so a resource
reads as *that site* before you get to the title. The colours are computed
here, offline, and committed as a static map the frontend imports — the
browser can't do it at runtime because Google's favicon service sends no
CORS header, so a canvas reading those pixels is tainted and throws.

Needs Pillow, which is deliberately NOT in requirements.txt: this never runs
on the server, only here, and the deploy shouldn't carry an image library
it has no use for.

  PYTHONPATH=. .venv/Scripts/python scripts/build_palettes.py
  PYTHONPATH=. .venv/Scripts/python scripts/build_palettes.py --missing-only
"""
import colorsys
import concurrent.futures
import json
import pathlib
import sys
import urllib.request
from urllib.parse import urlsplit

from PIL import Image

_BACKEND = pathlib.Path(__file__).resolve().parent.parent
SEED_JSON = _BACKEND / "seed" / "almanac-seed.json"
OUT = _BACKEND.parent / "frontend" / "src" / "palettes.json"

FAVICON = "https://www.google.com/s2/favicons?sz=128&domain={}"
UA = "Mozilla/5.0 (compatible; AlmanacPalette/1.0)"
# Google hands back a grey globe for domains it has no icon for. Those pixels
# quantize to flat grey, which we'd rather fall back to than bake in.
_GREY_TOLERANCE = 10


def host_of(link: str) -> str:
    host = (urlsplit(link).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _saturation(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255 for c in rgb)
    return colorsys.rgb_to_hsv(r, g, b)[1]


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def palette_for(host: str, timeout: int = 15) -> list[str] | None:
    """Up to three colours, most-used first, biased so at least one has real
    hue — a logo that's 90% white should still give us its accent."""
    req = urllib.request.Request(FAVICON.format(host), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except Exception:  # noqa: BLE001 — a missing icon is not an error here
        return None
    try:
        import io

        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:  # noqa: BLE001
        return None

    img = img.resize((32, 32))
    counts: dict[tuple[int, int, int], int] = {}
    for r, g, b, a in list(img.getdata()):
        if a < 128:
            continue
        # Bucket to 24 levels per channel so near-identical pixels group.
        key = (r // 24 * 24, g // 24 * 24, b // 24 * 24)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None

    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    # An icon that is nothing but flat grey is Google's placeholder globe.
    if all(
        max(c) - min(c) <= _GREY_TOLERANCE for c, _ in ranked[:3]
    ) and len(ranked) <= 4:
        return None

    chosen: list[tuple[int, int, int]] = [ranked[0][0]]
    vivid = [c for c, _ in ranked if _saturation(c) >= 0.35]
    for colour in vivid:
        if colour not in chosen:
            chosen.append(colour)
            break
    for colour, _ in ranked:
        if len(chosen) >= 3:
            break
        if colour not in chosen:
            chosen.append(colour)
    return [_hex(c) for c in chosen[:3]]


def main() -> None:
    missing_only = "--missing-only" in sys.argv
    rows = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    hosts = sorted({host_of(r["link"]) for r in rows if host_of(r["link"])})

    existing: dict[str, list[str]] = {}
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    todo = [h for h in hosts if not (missing_only and h in existing)]

    print(f"{len(hosts)} domains, fetching {len(todo)}")
    out = dict(existing)
    found = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for host, colours in zip(todo, pool.map(palette_for, todo)):
            if colours:
                out[host] = colours
                found += 1
            else:
                out.pop(host, None)

    # Drop domains no longer in the library so the file can't drift.
    out = {h: c for h, c in out.items() if h in set(hosts)}
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(out)} palettes ({found} fetched this run, "
          f"{len(hosts) - len(out)} fall back to a generated tint)")


if __name__ == "__main__":
    main()

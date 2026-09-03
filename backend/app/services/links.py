"""Canonicalize URLs before they're stored or looked up, so the same site
entered as http/https, with/without `www.`, or with a trailing slash can't
create duplicate resources. Lifted from Atlas's links.py — Almanac had the
same near-dupe problem (2x CommonLit 360, 4 NatGeo rows collapsing to one
page), surfaced by the 2026-08-30 link-validation pass."""
from urllib.parse import urlsplit, urlunsplit

_DEFAULT_PORTS = {"http": "80", "https": "443"}


def canonical_link(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return raw
    if "://" not in raw:
        raw = "https://" + raw

    parts = urlsplit(raw)
    # http/https are treated as the same resource for dedup purposes — almost
    # every site redirects http->https, and collapsing them kills a whole
    # class of duplicates. Non-web schemes are left alone.
    scheme = parts.scheme.lower()
    if scheme == "http":
        scheme = "https"
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    netloc = host
    if parts.port and str(parts.port) != _DEFAULT_PORTS.get(scheme):
        netloc = f"{host}:{parts.port}"

    path = parts.path
    if path in ("", "/"):
        path = ""
    else:
        path = path.rstrip("/")

    # query kept as-is (case- and order-sensitive); fragment dropped
    return urlunsplit((scheme, netloc, path, parts.query, ""))

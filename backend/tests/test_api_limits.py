"""Edge cases for the list endpoint: page-size limits and hostile search text.

Not run in the session that wrote them (the pytest command was refused by the
approval gate there); checked by reading the code they exercise.
"""


def _payload(**over):
    base = {
        "link": "https://example.com/lesson",
        "title": "Example Lesson",
        "description": "A lesson for testing",
        "subject": "Math",
        "grade_band": "3-5",
        "resource_type": "lesson plan",
        "cost": "free",
        "source_site": "Example",
        "udl_principles": ["representation"],
    }
    base.update(over)
    return base


# --- pagination limits -------------------------------------------------------


def test_limit_above_cap_is_rejected(client):
    assert client.get("/api/resources", params={"limit": 201}).status_code == 422


def test_limit_below_one_is_rejected(client):
    assert client.get("/api/resources", params={"limit": 0}).status_code == 422


def test_limit_at_cap_is_accepted(client):
    resp = client.get("/api/resources", params={"limit": 200})
    assert resp.status_code == 200


def test_negative_offset_is_rejected(client):
    assert client.get("/api/resources", params={"offset": -1}).status_code == 422


def test_offset_past_the_end_returns_no_items(client):
    client.post("/api/resources", json=_payload(link="https://p1.com"))
    resp = client.get("/api/resources", params={"offset": 50})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"] == []


def test_search_limit_cap_applies_too(client):
    client.post("/api/resources", json=_payload(link="https://q1.com", title="Fractions one"))
    resp = client.get("/api/resources", params={"q": "fractions", "limit": 201})
    assert resp.status_code == 422


# --- query sanitization ------------------------------------------------------

HOSTILE_QUERIES = [
    "'; DROP TABLE resources; --",
    "\" OR 1=1 --",
    "a' OR '1'='1",
    "NEAR(fractions lesson)",
    "fractions* OR lesson^2",
    "\"",
    "*",
    "{title}:fractions",
    "fractions\x00lesson",
    "%_%",
]


def test_hostile_query_text_never_errors(client):
    client.post("/api/resources", json=_payload(link="https://h1.com", title="Fractions lesson"))
    for query in HOSTILE_QUERIES:
        resp = client.get("/api/resources", params={"q": query})
        assert resp.status_code == 200, query
        assert isinstance(resp.json()["items"], list), query


def test_sql_in_query_does_not_touch_the_table(client):
    client.post("/api/resources", json=_payload(link="https://s1.com"))
    client.post("/api/resources", json=_payload(link="https://s2.com"))
    client.get("/api/resources", params={"q": "'; DROP TABLE resources; --"})
    client.get("/api/resources", params={"q": "x\" OR 1=1 --"})
    assert client.get("/api/resources").json()["total"] == 2


def test_punctuation_only_query_is_a_plain_browse(client):
    # No searchable words left after cleaning -> the same as an empty search.
    client.post("/api/resources", json=_payload(link="https://b1.com"))
    client.post("/api/resources", json=_payload(link="https://b2.com"))
    for query in ('"', "*", "(), ;"):
        assert client.get("/api/resources", params={"q": query}).json()["total"] == 2, query

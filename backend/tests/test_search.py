"""Ranked keyword search.

The behaviour these pin down is what the old single-LIKE search couldn't do:
match several keywords at once, look inside tags, weight rare words above
common ones, and still answer a query containing a word the library has
nothing for.
"""


def _make(client, link, **over):
    body = {
        "link": link,
        "title": "Untitled",
        "description": "",
        "subject": "Science",
        "grade_band": "3-5",
        "resource_type": "lesson plan",
        "cost": "free",
        "tags": [],
        "udl_principles": [],
    }
    body.update(over)
    resp = client.post("/api/resources", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_multi_keyword_query_matches_without_exact_phrase(client):
    """The whole point: these words never appear together as one substring."""
    _make(
        client,
        "https://ex.com/volcano",
        title="Volcano Eruption Model",
        subject="Science",
        grade_band="K-2",
        resource_type="activity",
        tags=["volcano", "earth science", "hands-on"],
    )
    _make(client, "https://ex.com/algebra", title="Algebra Basics", subject="Math")

    resp = client.get("/api/resources", params={"q": "volcano kindergarten activity"})
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["link"] == "https://ex.com/volcano"


def test_tags_are_searchable(client):
    """Tags hold the most specific words and the old search ignored them."""
    _make(client, "https://ex.com/tagged", title="Untitled Lesson", tags=["photosynthesis"])
    _make(client, "https://ex.com/other", title="Something Else")

    body = client.get("/api/resources", params={"q": "photosynthesis"}).json()
    assert body["total"] == 1
    assert body["items"][0]["link"] == "https://ex.com/tagged"


def test_rare_term_outranks_common_one(client):
    """Every row is 'free', so 'free' must not decide the ranking."""
    for i in range(6):
        _make(client, f"https://ex.com/common{i}", title="Free Science Lesson", cost="free")
    _make(
        client,
        "https://ex.com/rare",
        title="Free Tessellation Workshop",
        cost="free",
        tags=["tessellation"],
    )

    body = client.get("/api/resources", params={"q": "free tessellation"}).json()
    assert body["items"][0]["link"] == "https://ex.com/rare"


def test_unmatched_term_is_reported(client):
    _make(client, "https://ex.com/sel", subject="SEL", grade_band="K-2", tags=["feelings"])

    body = client.get("/api/resources", params={"q": "cheetah SEL"}).json()
    assert "cheetah" in body["unmatched_terms"]
    assert "sel" in body["matched_terms"]


def test_dead_term_still_returns_the_rest(client):
    """A micro question the library can't answer exactly should still get a
    macro answer rather than an empty page."""
    _make(
        client,
        "https://ex.com/movement",
        title="Movement Games",
        subject="SEL",
        grade_band="K-2",
        resource_type="activity",
        tags=["movement", "gross motor"],
        granularity="collection",
    )

    body = client.get(
        "/api/resources", params={"q": "cheetah kinesthetic SEL activity"}
    ).json()
    assert body["total"] >= 1
    assert body["items"][0]["link"] == "https://ex.com/movement"
    assert body["unmatched_terms"] == ["cheetah"]


def test_synonym_finds_differently_worded_resource(client):
    """'kinesthetic' is teacher vocabulary; the resource says 'movement'."""
    _make(client, "https://ex.com/move", title="Movement Break Cards", tags=["movement"])
    _make(client, "https://ex.com/quiet", title="Silent Reading Log", tags=["reading"])

    body = client.get("/api/resources", params={"q": "kinesthetic"}).json()
    assert body["total"] == 1
    assert body["items"][0]["link"] == "https://ex.com/move"


def test_filters_still_apply_alongside_a_query(client):
    _make(client, "https://ex.com/k2", title="Weather Unit", grade_band="K-2", tags=["weather"])
    _make(client, "https://ex.com/hs", title="Weather Unit", grade_band="9-12", tags=["weather"])

    body = client.get("/api/resources", params={"q": "weather", "grade_band": "9-12"}).json()
    assert body["total"] == 1
    assert body["items"][0]["link"] == "https://ex.com/hs"


def test_empty_query_browses_everything(client):
    _make(client, "https://ex.com/a")
    _make(client, "https://ex.com/b")

    body = client.get("/api/resources", params={"q": "  "}).json()
    assert body["total"] == 2
    assert body["broadened"] is False


def test_coverage_strip_counts_match_the_result_list(client):
    """The UDL strip and the grid under it must never disagree."""
    _make(client, "https://ex.com/w1", title="Weather Lesson", tags=["weather"],
          udl_principles=["engagement"])
    _make(client, "https://ex.com/w2", title="Cloud Types", tags=["weather"],
          udl_principles=["representation"])
    _make(client, "https://ex.com/nope", title="Algebra", subject="Math", tags=["algebra"])

    results = client.get("/api/resources", params={"q": "weather"}).json()
    coverage = client.get("/api/udl-coverage", params={"q": "weather"}).json()
    assert coverage["total"] == results["total"]

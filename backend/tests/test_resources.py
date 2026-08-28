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
        "tags": ["Fractions", "number sense"],
        "udl_principles": ["representation"],
    }
    base.update(over)
    return base


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_resource(client):
    resp = client.post("/api/resources", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["link"] == "https://example.com/lesson"
    assert sorted(body["tags"]) == ["fractions", "number sense"]  # normalized lowercase
    assert body["udl_principles"] == ["representation"]

    resp = client.get(f"/api/resources/{body['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Example Lesson"


def test_create_duplicate_link_rejected(client):
    assert client.post("/api/resources", json=_payload(link="https://dup.com")).status_code == 201
    assert client.post("/api/resources", json=_payload(link="https://dup.com")).status_code == 409


def test_unknown_udl_principle_is_dropped(client):
    resp = client.post(
        "/api/resources",
        json=_payload(link="https://u.com", udl_principles=["representation", "bogus"]),
    )
    assert resp.json()["udl_principles"] == ["representation"]


def test_search_filters_by_tag_and_subject(client):
    client.post("/api/resources", json=_payload(link="https://a.com", subject="Math", tags=["figures"]))
    client.post("/api/resources", json=_payload(link="https://b.com", subject="Science", tags=["figures"]))
    client.post("/api/resources", json=_payload(link="https://c.com", subject="Science", tags=["cells"]))

    assert client.get("/api/resources", params={"tag": "figures"}).json()["total"] == 2
    resp = client.get("/api/resources", params={"subject": "Science", "tag": "figures"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["link"] == "https://b.com"


def test_cost_filter(client):
    client.post("/api/resources", json=_payload(link="https://free.com", cost="free"))
    client.post("/api/resources", json=_payload(link="https://paid.com", cost="paid", price_note="subscription"))

    resp = client.get("/api/resources", params={"cost": "paid"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["link"] == "https://paid.com"


def test_udl_filter(client):
    client.post("/api/resources", json=_payload(link="https://rep.com", udl_principles=["representation"]))
    client.post("/api/resources", json=_payload(link="https://eng.com", udl_principles=["engagement"]))

    resp = client.get("/api/resources", params={"udl": "engagement"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["link"] == "https://eng.com"


def test_update_resource(client):
    rid = client.post("/api/resources", json=_payload(link="https://up.com", subject="Math")).json()["id"]
    resp = client.put(f"/api/resources/{rid}", json={"subject": "Science", "udl_principles": ["engagement", "action_expression"]})
    assert resp.status_code == 200
    assert resp.json()["subject"] == "Science"
    assert sorted(resp.json()["udl_principles"]) == ["action_expression", "engagement"]


def test_delete_resource(client):
    rid = client.post("/api/resources", json=_payload(link="https://del.com")).json()["id"]
    assert client.delete(f"/api/resources/{rid}").status_code == 204
    assert client.get(f"/api/resources/{rid}").status_code == 404


def test_facet_endpoints(client):
    client.post("/api/resources", json=_payload(link="https://x.com", subject="Arts", grade_band="6-8", resource_type="video", source_site="PBS", tags=["color", "line"]))
    assert any(s["name"] == "Arts" for s in client.get("/api/subjects").json())
    assert any(g["name"] == "6-8" for g in client.get("/api/grade-bands").json())
    assert any(t["name"] == "video" for t in client.get("/api/resource-types").json())
    assert any(s["name"] == "PBS" for s in client.get("/api/sources").json())
    assert {"color", "line"} <= {t["name"] for t in client.get("/api/tags").json()}


def test_visit_marks_visited_at(client):
    rid = client.post("/api/resources", json=_payload(link="https://visit.com")).json()["id"]
    assert client.post(f"/api/resources/{rid}/visit").json()["visited_at"] is not None


def test_favorite_toggle_and_filter(client):
    a = client.post("/api/resources", json=_payload(link="https://fa.com")).json()
    client.post("/api/resources", json=_payload(link="https://fb.com"))
    client.post(f"/api/resources/{a['id']}/favorite")

    resp = client.get("/api/resources", params={"favorite": True})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["link"] == "https://fa.com"

    assert client.post(f"/api/resources/{a['id']}/favorite", params={"favorite": False}).json()["is_favorite"] is False


def test_random_resource_scoped(client):
    client.post("/api/resources", json=_payload(link="https://m.com", subject="Math"))
    resp = client.get("/api/resources/random", params={"subject": "Math"})
    assert resp.status_code == 200
    assert resp.json()["subject"] == "Math"
    assert client.get("/api/resources/random", params={"subject": "Nope"}).status_code == 404


def test_batch_import_upserts_on_link(client):
    batch = [
        _payload(link="https://batch1.com", subject="Math"),
        _payload(link="https://batch2.com", subject="Science"),
    ]
    body = client.post("/api/resources/batch", json=batch).json()
    assert len(body["created"]) == 2 and len(body["updated"]) == 0

    body = client.post(
        "/api/resources/batch",
        json=[_payload(link="https://batch1.com", subject="Arts")],
    ).json()
    assert len(body["created"]) == 0 and len(body["updated"]) == 1
    assert body["updated"][0]["subject"] == "Arts"
    assert client.get("/api/resources").json()["total"] == 2  # still 2 rows, not 3

    # batch rows are provenance 'capture'
    assert body["updated"][0]["source"] == "capture"


def test_udl_coverage(client):
    client.post("/api/resources", json=_payload(link="https://v.com", resource_type="video", tags=["water cycle"], udl_principles=["representation"]))
    client.post("/api/resources", json=_payload(link="https://lab.com", resource_type="activity", tags=["water cycle"], udl_principles=["action_expression", "engagement"]))
    client.post("/api/resources", json=_payload(link="https://other.com", resource_type="video", tags=["photosynthesis"], udl_principles=["representation"]))

    cov = client.get("/api/udl-coverage", params={"q": "", "tag": "water cycle"}).json()
    assert cov["total"] == 2
    assert cov["representation"] == 1
    assert cov["action_expression"] == 1
    assert cov["engagement"] == 1
    assert cov["by_type"] == {"video": 1, "activity": 1}

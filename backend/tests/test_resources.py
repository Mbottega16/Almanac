def _payload(**over):
    base = {
        "link": "https://example.com/lesson",
        "title": "Example Lesson",
        "description": "A lesson for testing",
        "subject": "Math",
        "grade_band": "3-5",
        "resource_type": "lesson plan",
        "duration_minutes": 45,
        "materials": "fraction tiles",
        "learning_outcomes": ["Students will be able to compare fractions"],
        "cost": "free",
        "source_site": "Example",
        "tags": ["Fractions", "number sense"],
        "udl_principles": ["representation"],
    }
    base.update(over)
    return base


def test_learning_outcomes_and_age_backfill(client):
    body = client.post("/api/resources", json=_payload(link="https://lo.com")).json()
    assert body["learning_outcomes"] == ["Students will be able to compare fractions"]
    # grade_band 3-5 -> ages 8-11 auto-filled
    assert body["age_min"] == 8 and body["age_max"] == 11
    assert body["duration_minutes"] == 45


def test_age_filter(client):
    client.post("/api/resources", json=_payload(link="https://k2.com", grade_band="K-2"))
    client.post("/api/resources", json=_payload(link="https://hs.com", grade_band="9-12"))
    resp = client.get("/api/resources", params={"age": 7})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["link"] == "https://k2.com"


def test_explicit_age_range_kept(client):
    body = client.post(
        "/api/resources",
        json=_payload(link="https://ar.com", grade_band="All", age_min=10, age_max=12),
    ).json()
    assert body["age_min"] == 10 and body["age_max"] == 12


def test_scope_defaults_to_lesson_and_filters(client):
    body = client.post("/api/resources", json=_payload(link="https://one.com")).json()
    assert body["scope"] == "lesson"
    assert body["publisher"] is None

    client.post(
        "/api/resources",
        json=_payload(
            link="https://im.com",
            title="Illustrative Mathematics 6–8",
            scope="curriculum",
            publisher="Illustrative Mathematics",
            cost="free",
        ),
    )
    resp = client.get("/api/resources", params={"scope": "curriculum"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["publisher"] == "Illustrative Mathematics"

    # publisher name is searchable via q
    assert client.get("/api/resources", params={"q": "Illustrative"}).json()["total"] == 1
    # and filterable exactly
    assert (
        client.get("/api/resources", params={"publisher": "Illustrative Mathematics"})
        .json()["total"]
        == 1
    )


def test_link_canonicalized_on_write_prevents_near_dupes(client):
    a = client.post("/api/resources", json=_payload(link="http://www.dupe.com/lesson/")).json()
    assert a["link"] == "https://dupe.com/lesson"
    # same resource, messier URL -> the batch upsert must land on the same row
    body = client.post(
        "/api/resources/batch",
        json=[_payload(link="https://www.dupe.com/lesson", subject="Arts")],
    ).json()
    assert len(body["created"]) == 0 and len(body["updated"]) == 1
    assert client.get("/api/resources").json()["total"] == 1


def test_granularity_defaults_specific_and_filters(client):
    client.post("/api/resources", json=_payload(link="https://one.com"))
    client.post(
        "/api/resources",
        json=_payload(link="https://portal.com", granularity="collection"),
    )
    assert client.get("/api/resources").json()["items"][0]["granularity"] in ("specific", "collection")
    r = client.get("/api/resources", params={"granularity": "specific"})
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["link"] == "https://one.com"


def test_evidence_is_write_only(client):
    body = client.post(
        "/api/resources",
        json=_payload(link="https://ev.com", evidence="\"A real quoted sentence.\"",
                      udl_rationale="representation: captions + transcript"),
    ).json()
    assert "evidence" not in body  # audit-only, never returned
    assert body["udl_rationale"] == "representation: captions + transcript"
    assert body["link_status"] == "unknown"


def test_standards_parsed_and_filterable(client):
    client.post(
        "/api/resources",
        json=_payload(link="https://ngss.com", subject="Science",
                      standards="Aligned to NGSS MS-LS1-1 and 3-LS1-1."),
    )
    client.post(
        "/api/resources",
        json=_payload(link="https://ccss.com",
                      standards="CCSS.MATH.CONTENT.6.RP.A.3"),
    )
    body = client.get("/api/resources", params={"standard": "MS-LS1-1"}).json()
    assert body["total"] == 1
    assert body["items"][0]["link"] == "https://ngss.com"
    assert "MS-LS1-1" in body["items"][0]["standard_codes"]
    # case-insensitive on the query
    assert client.get("/api/resources", params={"standard": "ms-ls1-1"}).json()["total"] == 1
    codes = {c["name"] for c in client.get("/api/standards").json()}
    assert {"MS-LS1-1", "3-LS1-1", "CCSS.MATH.CONTENT.6.RP.A.3"} <= codes


def test_scope_and_publisher_facets(client):
    client.post(
        "/api/resources",
        json=_payload(link="https://c.com", scope="course", publisher="OpenSciEd"),
    )
    assert any(s["name"] == "course" for s in client.get("/api/scopes").json())
    assert any(p["name"] == "OpenSciEd" for p in client.get("/api/publishers").json())


def test_library_stats(client):
    client.post("/api/resources", json=_payload(link="https://s1.com", subject="Math",
                                                udl_principles=["representation"]))
    client.post("/api/resources", json=_payload(link="https://s2.com", subject="Science",
                                                cost="paid", udl_principles=["engagement"]))
    st = client.get("/api/stats").json()
    assert st["total"] == 2
    assert {"name": "Math", "count": 1} in st["by_subject"]
    assert any(c["name"] == "paid" for c in st["by_cost"])
    assert st["subject_udl"]["Math"]["representation"] == 1
    assert st["subject_udl"]["Math"]["engagement"] == 0
    assert len(st["thin_cells"]) >= 1


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


def test_auth_gate_dormant_by_default(client):
    # No ADMIN_PASSWORD in the test env -> every route is open.
    assert client.get("/api/auth-status").json() == {"gate_enabled": False}
    assert client.get("/api/resources").status_code == 200


def test_capture_research_disabled_without_key(client):
    assert client.get("/api/capture/enabled").json() == {"enabled": False}
    resp = client.post("/api/capture/research", json={"links": ["https://x.com"]})
    assert resp.status_code == 503
    assert "ANTHROPIC_API_KEY" in resp.json()["detail"]


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

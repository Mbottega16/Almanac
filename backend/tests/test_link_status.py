"""Two-strike link health: one failure never changes what the site shows; two
consecutive real failures mark a row 'dead'. Both entry points (the weekly
check_links --write-status path and flag_dead_links.py) go through
check_links.write_status, so these tests cover the single writer."""
import json

import pytest

from scripts import check_links, flag_dead_links

LINK = "https://example.org/lesson"
OTHER = "https://example.org/other"


@pytest.fixture()
def seed_files(tmp_path, monkeypatch):
    seed = tmp_path / "almanac-seed.json"
    status = tmp_path / "link-status.json"
    monkeypatch.setattr(check_links, "SEED_FILE", seed)
    monkeypatch.setattr(check_links, "STATUS_FILE", status)
    monkeypatch.setattr(flag_dead_links, "SEED_FILE", seed)
    return seed, status


def _write_seed(seed, rows):
    seed.write_text(json.dumps(rows), encoding="utf-8")


def _row_status(seed, link):
    return next(r for r in json.loads(seed.read_text(encoding="utf-8")) if r["link"] == link).get("link_status")


def _result(link, status):
    return {"link": link, "title": "t", "status": status, "detail": ""}


def test_one_failure_leaves_ok_row_ok(seed_files):
    seed, _ = seed_files
    _write_seed(seed, [{"link": LINK, "title": "t", "link_status": "ok"}])

    check_links.write_status([_result(LINK, "dead")])

    assert _row_status(seed, LINK) == "ok"


def test_one_failure_leaves_unknown_row_unknown(seed_files):
    seed, _ = seed_files
    _write_seed(seed, [{"link": LINK, "title": "t", "link_status": "unknown"}])

    check_links.write_status([_result(LINK, "dead")])

    assert _row_status(seed, LINK) == "unknown"


def test_second_consecutive_failure_marks_dead(seed_files):
    seed, status = seed_files
    _write_seed(seed, [{"link": LINK, "title": "t", "link_status": "ok"}])

    check_links.write_status([_result(LINK, "dead")])
    check_links.write_status([_result(LINK, "dead")])

    assert _row_status(seed, LINK) == "dead"
    assert json.loads(status.read_text(encoding="utf-8"))[LINK]["fails"] == 2


def test_a_pass_between_failures_resets_the_count(seed_files):
    seed, status = seed_files
    _write_seed(seed, [{"link": LINK, "title": "t", "link_status": "ok"}])

    check_links.write_status([_result(LINK, "dead")])
    check_links.write_status([_result(LINK, "ok")])
    check_links.write_status([_result(LINK, "dead")])

    assert _row_status(seed, LINK) == "ok"
    assert json.loads(status.read_text(encoding="utf-8"))[LINK]["fails"] == 1


def test_unreachable_never_counts_as_a_failure(seed_files):
    seed, status = seed_files
    _write_seed(seed, [{"link": LINK, "title": "t", "link_status": "ok"}])

    check_links.write_status([_result(LINK, "unreachable")])
    check_links.write_status([_result(LINK, "unreachable")])

    assert _row_status(seed, LINK) == "unreachable"
    assert json.loads(status.read_text(encoding="utf-8"))[LINK]["fails"] == 0


def test_next_link_status_is_two_strikes_for_failures_only():
    assert check_links._next_link_status("dead", 1) is None
    assert check_links._next_link_status("dead", 2) == "dead"
    assert check_links._next_link_status("unreachable", 5) == "unreachable"
    assert check_links._next_link_status("ok", 0) == "ok"


def test_flag_dead_links_one_run_does_not_mark_dead(seed_files, monkeypatch, capsys):
    seed, _ = seed_files
    _write_seed(seed, [
        {"link": LINK, "title": "t", "link_status": "ok"},
        {"link": OTHER, "title": "u", "link_status": "ok"},
    ])
    monkeypatch.setattr(flag_dead_links, "classify", lambda link, timeout: ("dead", "HTTP 404"))

    flag_dead_links.main()

    assert _row_status(seed, LINK) == "ok"
    assert _row_status(seed, OTHER) == "ok"
    assert "DEAD" not in capsys.readouterr().out


def test_flag_dead_links_second_run_marks_dead(seed_files, monkeypatch, capsys):
    seed, _ = seed_files
    _write_seed(seed, [{"link": LINK, "title": "t", "link_status": "ok"}])
    monkeypatch.setattr(flag_dead_links, "classify", lambda link, timeout: ("dead", "HTTP 404"))

    flag_dead_links.main()
    flag_dead_links.main()

    assert _row_status(seed, LINK) == "dead"
    assert f"DEAD  {LINK}" in capsys.readouterr().out

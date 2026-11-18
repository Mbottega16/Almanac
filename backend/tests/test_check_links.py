"""The weekly link check (scripts/check_links.py) skips links it cannot fetch."""
import importlib.util
import pathlib

_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "check_links.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_links", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_only_web_links_are_checkable():
    cl = _load()
    assert cl._checkable("https://www.teachengineering.org/lessons/view/x")
    assert cl._checkable("http://example.org")
    assert not cl._checkable("almanac-original://prek/all-about-me/day-1")
    assert not cl._checkable("")
    assert not cl._checkable(None)


def test_seed_mode_skips_originals():
    cl = _load()
    links = [link for _, link, _ in cl._seed_rows(0)]
    assert links, "the seed has web links to check"
    assert all(cl._checkable(link) for link in links)

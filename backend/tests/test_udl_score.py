import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from udl_score import PRINCIPLES, problems, score  # noqa: E402


def test_counts_each_principle_and_format():
    rows = [
        {"link": "a", "resource_type": "video", "udl_principles": ["engagement", "representation"]},
        {"link": "b", "resource_type": "video", "udl_principles": ["representation"]},
        {"link": "c", "resource_type": "worksheet", "udl_principles": list(PRINCIPLES)},
    ]
    result = score(rows)
    assert result["total"] == 3
    assert result["per_principle"] == {"engagement": 2, "representation": 3, "action_expression": 1}
    assert result["formats"]["representation"]["video"] == 2
    assert problems(result) == []


def test_flags_missing_principle_untagged_rows_and_unknown_names():
    rows = [
        {"link": "a", "resource_type": "video", "udl_principles": ["representation"]},
        {"link": "b", "resource_type": "video", "udl_principles": ["made_up"]},
        {"link": "c", "resource_type": "video", "udl_principles": []},
    ]
    result = score(rows)
    found = problems(result)
    assert "no resources tagged engagement" in found
    assert "no resources tagged action_expression" in found
    assert "2 resources have no UDL principle" in found
    assert any("made_up" in p for p in found)


def test_seed_library_loads_and_scores():
    import json

    seed = pathlib.Path(__file__).resolve().parent.parent / "seed" / "almanac-seed.json"
    rows = json.loads(seed.read_text(encoding="utf-8"))
    result = score(rows)
    assert result["total"] == len(rows)
    assert all(result["per_principle"][p] > 0 for p in PRINCIPLES)

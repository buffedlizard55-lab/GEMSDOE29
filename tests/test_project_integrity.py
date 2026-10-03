from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_full_owner_brief_is_preserved_in_readme() -> None:
    readme = (ROOT / "README.md").read_text()
    original = (ROOT / "knowledge" / "owner_brief_verbatim.txt").read_text()
    marker = "````text\n"
    assert marker in readme
    embedded = readme.split(marker, 1)[1].rsplit("\n````", 1)[0]
    assert embedded.rstrip("\n") == original.rstrip("\n")


def test_three_hypotheses_have_frozen_ranked_statuses() -> None:
    registry = json.loads((ROOT / "registry" / "hypotheses.json").read_text())
    items = registry["items"]
    assert len(items) == 3
    assert [item["rank"] for item in items] == [1, 2, 3]
    assert [item["id"] for item in items] == ["H32", "H31", "H33"]
    assert "first candidate" in items[0]["status"]
    assert "no model fit" in items[1]["status"]
    assert "blocked" in items[2]["status"]
    assert all(item["planning_delta_dti"] for item in items)


def test_historical_download_is_not_slot_approved() -> None:
    registry = json.loads((ROOT / "registry" / "submissions.json").read_text())
    assert not any(item.get("slot_approved") is True for item in registry["files"])
    historical = next(item for item in registry["files"] if item["role"] == "historical_reference")
    assert historical["do_not_submit"] is True
    assert historical["score"] is None
    assert historical["format_ok_local"] is True
    assert historical["sha256"] == "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8"
    assert (ROOT / historical["path"]).is_file()
    assert (ROOT / historical["format_check_receipt"]).is_file()


def test_score_claims_remain_unverified_and_unused() -> None:
    registry = json.loads((ROOT / "registry" / "score_claims.json").read_text())
    assert registry["claims"]
    assert all(claim["used_for_modeling"] is False for claim in registry["claims"])
    assert all("unverified" in claim["verification"] for claim in registry["claims"])


def test_pages_include_submission_guide_and_caveats() -> None:
    pages = ["index.html", "executive-summary.html", "research.html", "status.html", "sources.html", "irregularities.html"]
    for name in pages:
        path = ROOT / "docs" / name
        assert path.is_file(), name
        text = path.read_text()
        assert "GEMSDOE29" in text
        assert "leaderboard" in text.lower() or name == "irregularities.html"


def test_public_pages_do_not_republish_score_claims_or_leaderboard_links() -> None:
    import re

    for path in (ROOT / "docs").glob("*.html"):
        text = path.read_text()
        assert not any(value in text for value in ("0.3195", "0.2941", "0.2477", "0.2600")), path.name
        assert not re.search(r'href=["\'][^"\']*leaderboard', text, flags=re.IGNORECASE), path.name

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


def test_hypothesis_slate_has_frozen_ranked_statuses() -> None:
    registry = json.loads((ROOT / "registry" / "hypotheses.json").read_text())
    items = registry["items"]
    ids = [item["id"] for item in items]
    assert ids == ["H32", "H31", "H33", "H34", "H35", "H36", "H37", "H38", "H39"]
    by_id = {item["id"]: item for item in items}
    assert "first candidate" in by_id["H32"]["status"]
    assert "screen ran and failed" in by_id["H31"]["status"]
    assert "no confirmation" in by_id["H31"]["status"]
    assert "blocked" in by_id["H33"]["status"]
    assert "FAIL" in by_id["H34"]["status"]
    assert all(item["planning_delta_dti"] for item in items)
    assert [by_id[f"H{i}"]["rank"] for i in (35, 36, 37, 38, 39)] == [1, 2, 3, 4, 5]


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


def test_current_candidate_does_not_clear_the_holdout_best() -> None:
    submissions = json.loads((ROOT / "registry" / "submissions.json").read_text())
    status = json.loads((ROOT / "registry" / "status_feed.json").read_text())["current"]
    candidate = next(item for item in submissions["files"] if item["id"] == "repo-c0-habitat")
    proxy = candidate["proxy_evidence"]
    assert proxy["candidate_method_mean_dti"] < proxy["current_holdout_best_method_dti"]
    assert proxy["beats_current_holdout_best"] is False
    assert candidate["do_not_submit"] is True
    assert candidate["slot_approved"] is False
    assert "0.14479" in status["holdout_best"]


def test_corrected_h29_screen_fails_without_confirmation_cells() -> None:
    evidence = json.loads((ROOT / "evidence" / "h29_holdout.json").read_text())
    gates = json.loads((ROOT / "evidence" / "h29_gate.json").read_text())
    assert {row["draw"] for row in evidence["rows"]} == {0, 1}
    assert len(evidence["rows"]) == 8
    assert "not_run_screen_failed" in evidence["confirmation_status"]
    assert all(gate["screen_pass"] is False and gate["PASS"] is False for gate in gates.values())


def test_score_claims_remain_unverified_and_unused() -> None:
    registry = json.loads((ROOT / "registry" / "score_claims.json").read_text())
    assert registry["claims"]
    assert all(claim["used_for_modeling"] is False for claim in registry["claims"])
    assert all("unverified" in claim["verification"] for claim in registry["claims"])


def test_legacy_pages_root_redirects_to_generated_site() -> None:
    root = (ROOT / "index.html").read_text()
    assert 'http-equiv="refresh" content="0; url=docs/index.html"' in root
    assert '<a href="docs/index.html">Open the GEMS Prize research site</a>' in root


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

    # Research/entry pages must not republish score claims. The irregularities and sources pages are
    # explicitly the place where flagged claims are documented, so those two may quote them.
    quoting_allowed = {"irregularities.html", "sources.html"}
    for path in (ROOT / "docs").glob("*.html"):
        text = path.read_text()
        if path.name not in quoting_allowed:
            assert not any(value in text for value in ("0.3195", "0.2941", "0.2477", "0.2600")), path.name
        assert not re.search(r'href=["\'][^"\']*leaderboard', text, flags=re.IGNORECASE), path.name

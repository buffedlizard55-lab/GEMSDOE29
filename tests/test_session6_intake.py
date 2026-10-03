"""Session-6 intake pins: v5 slate register, H43 status correction, new knowledge docs.

No heavy dependencies: JSON + text only, so this runs in a bare checkout.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v5_slate_register_is_complete_and_ranked() -> None:
    reg = json.loads((ROOT / "registry" / "hypotheses_v5_2026-10-03.json").read_text())
    items = reg["items"]
    assert [i["id"] for i in items] == ["H50", "H49", "H51", "H48"]
    assert [i["rank"] for i in items] == [1, 2, 3, 4]
    required = {"id", "rank", "title", "status", "layers", "signature", "why_unmapped",
                "difference", "planning_delta_dti", "cost", "external_data", "validation", "slate"}
    for item in items:
        assert set(item) >= required, item["id"]
        assert item["slate"].startswith("v5"), item["id"]
        assert "knowledge/35" in item["slate"], item["id"]
        assert item["layers"] and item["signature"] and item["why_unmapped"], item["id"]
    # obtainability: every v5 candidate states free/official provenance or names the blocked fetch
    ext = {i["id"]: i["external_data"].lower() for i in items}
    assert "none required" in ext["H50"] and "none required" in ext["H49"] and "none required" in ext["H51"]
    assert "gdr.openei.org" in ext["H48"] and "owner" in ext["H48"]


def test_h43_registry_status_matches_the_completed_evidence() -> None:
    reg = json.loads((ROOT / "registry" / "hypotheses.json").read_text())
    h43 = next(i for i in reg["items"] if i["id"] == "H43")
    assert "v4 slate" in h43["status"]  # frozen-test compatibility phrase retained
    assert "not implemented" not in h43["status"]
    for token in ("32/33", "34/35", "G3", "knowledge/30"):
        assert token in h43["status"], token
    # the evidence the status now claims must exist on disk
    base = ROOT / "evidence" / "h43_screen"
    for name in ("cells_screen.jsonl", "cells_confirm.jsonl", "summary_screen.json",
                 "summary_confirm.json", "analyzer_report.json"):
        assert (base / name).is_file(), name


def test_session6_irregularity_and_feed_event_are_registered() -> None:
    irregs = json.loads((ROOT / "registry" / "irregularities.json").read_text())["items"]
    entry = next(i for i in irregs if i["id"] == "IR-29-H43-REGISTRY-STALE")
    assert entry["status"] == "resolved"
    assert "registry/hypotheses.json" in entry["affected_artifacts"]
    feed = json.loads((ROOT / "registry" / "status_feed.json").read_text())
    assert any("Session-6 intake" in e["title"] for e in feed["events"])
    # the frozen no-slot decision still holds everywhere it is pinned
    subs = json.loads((ROOT / "registry" / "submissions.json").read_text())
    assert not any(f.get("slot_approved") is True for f in subs["files"])
    assert "no file is slot-approved" in feed["current"]["confirmation_status"]


def test_session6_knowledge_docs_exist_and_answer_the_brief() -> None:
    k34 = (ROOT / "knowledge" / "34_d28_why_it_won_and_path_past_03195_2026-10-03.md").read_text()
    for token in ("dot_thin(H19-5, 2.8)", "44,090", "marginal_inclusion_ratio", "H29", "H31", "H40",
                  "0.3195", "IR-SCORE-01", "verify_downloads.py"):
        assert token in k34, token
    k35 = (ROOT / "knowledge" / "35_candidates_v5_2026-10-03.md").read_text()
    for token in ("H50", "H49", "H51", "H48", "Why off-catalogue", "36/37", "0.14479"):
        assert token in k35, token
    k36 = (ROOT / "knowledge" / "36_session6_review_intake_2026-10-03.md").read_text()
    assert "Three-pass record" in k36 or "three-pass" in k36
    assert "Session 6 intake" in (ROOT / "README.md").read_text()

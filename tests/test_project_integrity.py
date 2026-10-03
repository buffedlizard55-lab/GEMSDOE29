from __future__ import annotations

import json

import pytest
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
    assert ids == ["H32", "H31", "H33", "H34", "H35", "H36", "H37", "H38", "H39", "H40", "H41", "H42",
                   "H43", "H44", "H45", "H46", "H47"]
    by_id = {item["id"]: item for item in items}
    assert "priority superseded" in by_id["H32"]["status"]
    assert "screen ran and failed" in by_id["H31"]["status"]
    assert "no confirmation" in by_id["H31"]["status"]
    assert "blocked" in by_id["H33"]["status"]
    assert "FAIL" in by_id["H34"]["status"]
    assert by_id["H35"]["rank"] == "screened" and "G1 FAIL" in by_id["H35"]["status"]
    assert by_id["H40"]["rank"] == "screened" and "G1 FAIL" in by_id["H40"]["status"]
    assert all(item["planning_delta_dti"] for item in items)
    assert [by_id[k]["rank"] for k in ("H41", "H36", "H37", "H42", "H38", "H39")] == [1, 2, 3, 4, 5, 5]
    # the v4 slate (session 4) ranks inside its own document, so ids are unique but ranks restart
    v4 = ["H43", "H44", "H45", "H46", "H47"]
    assert [by_id[k]["rank"] for k in v4] == [1, 2, 3, 4, 5]
    assert all("v4 slate" in by_id[k]["status"] for k in v4)
    assert all(by_id[k]["slate"].startswith("v4") for k in v4)
    required = {"id", "rank", "title", "status", "layers", "signature", "why_unmapped", "difference",
                "planning_delta_dti", "cost", "external_data", "validation"}
    assert all(set(item) >= required for item in items)  # every registered candidate answers the same questions
    # every v4 candidate must state obtainability: a free/public/CC marker plus where the fetch has to happen
    for k in v4:
        e = by_id[k]["external_data"].lower()
        assert any(t in e for t in ("free", "public", "cc by", "none required")), k
        assert any(t in e for t in ("owner-side", "unreachable from the sandbox", "none required")), k


def test_h41_screen_evidence_is_internally_consistent() -> None:
    """The session-4 H41 verdict must stay recomputable from raw cells, with its frozen gates pinned."""
    import hashlib

    base = ROOT / "evidence" / "h41_screen"
    cells = base / "cells_screen.jsonl"
    if not cells.is_file():
        pytest.skip("H41 screen evidence not present in this checkout")
    rows = [json.loads(line) for line in cells.read_text().splitlines() if line.strip()]
    summary = json.loads((base / "summary_screen.json").read_text())
    design = json.loads((base / "design_screen.json").read_text())
    analyzer = json.loads((base / "analyzer_report.json").read_text())
    assert len(rows) == 40, "the frozen screen is 4 folds x 2 draws x 5 arms"
    assert {r["arm"] for r in rows} == set(design["arms"])
    assert sorted({r["draw"] for r in rows}) == design["draws"] == [28, 29]
    assert summary["n_cells"] == len(rows) and summary["draws"] == [28, 29]
    # the gates are the frozen ones, and the independent auditor read the same values as the design record
    gates = design["gates"]
    # the auditor prints its own key names, so compare the numbers it audited against the frozen record
    ag = analyzer["gates"]
    assert (ag["mean_gain"], ag["min_positive_folds"]) == (gates["mean_gain"], gates["min_positive_folds"])
    assert ag["worst_floor"] == gates["max_fold_loss"], "the auditor must use the frozen worst-fold floor"
    assert list(ag["budget_band"]) == list(gates["budget_ratio_band"])
    assert ag["holdout_best"] == gates["holdout_best"] and ag["min_nonzero_fraction"] == gates["min_nonzero_fraction"]
    # (the SGMC fold criterion is applied in the runner/summary, not duplicated by the auditor)
    assert (gates["mean_gain"], gates["min_positive_folds"], gates["max_fold_loss"]) == (0.005, 3, -0.01)
    assert tuple(gates["budget_ratio_band"]) == (0.75, 1.25) and gates["min_nonzero_fraction"] == 0.002
    assert gates["sgmc_min_positive_folds"] == 3
    assert gates["holdout_best"] == 0.14479018210246675
    # the arm plan is the frozen column sets, in the frozen order
    assert design["h41_names"] == ["H41_SUPP", "H41_OFF", "H41_CORR", "H41_OFF_SCARP", "H41_PURITY"]
    assert design["arm_columns"]["A1_h41_off"] == ["H41_OFF", "H41_PURITY"]
    assert design["arm_columns"]["A4_h41_union"] == design["h41_names"]
    assert {a: len(c) for a, c in design["arm_columns"].items()} == {
        "C0_base": 0, "A1_h41_off": 2, "A2_h41_support": 4, "A3_h41_corridor": 4, "A4_h41_union": 5}
    # recompute every gate statistic from raw cells and compare with the recorded verdicts
    folds, draws = [0, 1, 2, 3], [28, 29]

    def dti(arm, fold, draw):
        return next(r["dti"] for r in rows if r["arm"] == arm and r["fold"] == fold and r["draw"] == draw)

    for arm, entry in summary["arms"].items():
        if arm == "C0_base":
            continue
        gains = [sum(dti(arm, f, d) for d in draws) / len(draws) - sum(dti("C0_base", f, d) for d in draws) / len(draws)
                 for f in folds]
        assert abs(sum(gains) / len(gains) - entry["mean_gain"]) < 1e-12, arm
        assert all(abs(x - y) < 1e-12 for x, y in zip(gains, entry["fold_gains"])), arm
        pos = [sum(1 for f in folds if dti(arm, f, d) - dti("C0_base", f, d) > 0) for d in draws]
        assert pos == entry["positive_folds_per_draw"], arm
        assert abs(min(gains) - entry["worst_fold_gain"]) < 1e-12, arm
        want = (entry["mean_gain"] >= gates["mean_gain"] and min(pos) >= gates["min_positive_folds"]
                and min(gains) >= gates["max_fold_loss"])
        assert want == entry["G1_SCREEN_PASS"], arm
        assert entry["cells_present"] == 8 and entry["budget_ok"] is True, arm
    assert summary["arms"]["A1_h41_off"]["G1_SCREEN_PASS"] is True
    assert summary["arms"]["A4_h41_union"]["G1_SCREEN_PASS"] is True
    assert summary["arms"]["A2_h41_support"]["G1_SCREEN_PASS"] is False
    assert summary["arms"]["A3_h41_corridor"]["G1_SCREEN_PASS"] is False
    # the SGMC second proxy moved the wrong way on every arm: the pass is a primary-proxy pass only
    assert all(summary["arms"][a]["sgmc_mean_gain"] < 0 for a in summary["arms"] if a != "C0_base")
    assert all(summary["arms"][a]["sgmc_positive_folds"] < gates["sgmc_min_positive_folds"]
               for a in summary["arms"] if a != "C0_base")
    # the pre-declared degeneracy guard passed, so this verdict is not the H31 sparsity artifact
    guard = summary["viability_guard"]
    assert guard["passed"] is True and guard["problems"] == [] and guard["min_nonzero_fraction"] == 0.002
    assert all(r["viability_guard"] == [] for r in rows if r["arm"] == "C0_base"), "per-cell guard reports"
    assert len({r["arm"] for r in rows if r["arm"] == "C0_base"}) == 1
    # only the control rows carry the field diagnostics (the arms reuse the same fitted rasters)
    diag = [r for r in rows if "h41_diag" in r]
    assert {r["arm"] for r in diag} == {"C0_base"} and len(diag) == 8
    fractions = [v for r in diag for v in r["h41_diag"]["nonzero_fraction"].values()]
    assert len(fractions) == 8 * len(design["h41_names"])
    assert min(fractions) >= 0.002 and max(fractions) <= 1.0
    n_off = [r["h41_diag"]["n_centroids_off_catalogue"] for r in diag]
    assert min(n_off) == 160 and max(n_off) == 178
    assert all(r["h41_diag"]["n_centroids_total"] == r["h41_diag"]["n_centroids_off_catalogue"]
               + r["h41_diag"]["n_centroids_near_catalogue"] for r in diag)
    # the frozen document is hash-pinned and the independent audit found nothing
    pre = ROOT / "knowledge" / "24_preregistered_h41_screen_2026-10-03.md"
    digest = hashlib.sha256(pre.read_bytes()).hexdigest()
    assert digest == design["preregistration"]["sha256"], "the frozen preregistration must not be edited after the run"
    assert analyzer["integrity_problems"] == []
    assert analyzer["design_check"]["gates_match"] is True
    assert analyzer["design_check"]["arm_columns_frozen"] is True
    assert analyzer["design_check"]["prereg_hash_matches_current_file"] is True
    assert all(v == 1.0 for v in analyzer["report"]["screen"]["summary_cross_check"].values())
    # the qfaults input is the pinned mirror, read exactly as documented
    q = design["qfaults"]
    assert (q["n_rows_read"], q["n_in_footprint"], q["n_rows_unparsable"], q["n_recency_unmapped"]) == (1126, 376, 0, 1)
    assert q["n_dropped_out_of_grid"] == 0 and q["n_slip_rate_missing"] == 0 and q["slip_rate_max_seen"] == 4.5
    assert abs(q["support_scale"] - 1.0249980688095093) < 1e-9
    # the run happened on a clean tree at the recorded commit
    assert design["git"]["dirty_worktree"] is False and design["git"]["revision"].startswith("a9d880e")


def test_h35_h40_screen_evidence_is_internally_consistent() -> None:
    base = ROOT / "evidence" / "h35_h40_screen"
    summary = json.loads((base / "summary_screen.json").read_text())
    design = json.loads((base / "design_screen.json").read_text())
    analyzer = json.loads((base / "analyzer_report.json").read_text())
    assert analyzer["integrity_problems"] == []
    assert analyzer["design_gate_match"] is True
    # every frozen gate from the preregistration is echoed unchanged in the design
    assert design["gates"] == summary["gates"]
    assert summary["gates"]["mean_gain"] == 0.005 and summary["gates"]["min_positive_folds"] == 3
    assert summary["gates"]["max_fold_loss"] == -0.01 and tuple(summary["gates"]["budget_ratio_band"]) == (0.75, 1.25)
    assert summary["gates"]["holdout_best"] == 0.14479018210246675
    # the frozen decision: all four arms failed G1; no confirmation exists
    arms = summary["arms"]
    assert all(arms[a]["G1_SCREEN_PASS"] is False for a in ("A1_h35_struct", "A2_h35_corrob", "A3_h40_persist", "A4_union"))
    assert all(arms[a]["cells_present"] == 8 and arms[a]["budget_ok"] for a in arms if a != "C0_base")
    assert not (base / "summary_confirm.json").exists()
    # gains match the analyzer recomputation to the bit
    for arm in ("A1_h35_struct", "A2_h35_corrob", "A3_h40_persist", "A4_union"):
        assert arms[arm]["mean_gain"] == analyzer["report"]["screen"]["arms"][arm]["mean_gain"]
    # no arm degenerated to the control emission in any cell (the H31 pathology)
    rows = [json.loads(line) for line in (base / "cells_screen.jsonl").read_text().splitlines()]
    from collections import defaultdict
    cell = defaultdict(dict)
    for r in rows:
        cell[(r["fold"], r["draw"])][r["arm"]] = r
    assert len(cell) == 8 and len(rows) == 40
    for d in cell.values():
        for arm in ("A1_h35_struct", "A2_h35_corrob", "A3_h40_persist", "A4_union"):
            assert d[arm]["emitted"] != d["C0_base"]["emitted"]


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

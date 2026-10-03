from __future__ import annotations

import hashlib
import json
from pathlib import Path

from run_holdout_screen import summarize_gate

ROOT = Path(__file__).resolve().parents[1]


def make_rows(draw_values: dict[int, list[float]]) -> list[dict]:
    rows = []
    for draw, values in draw_values.items():
        for fold, delta in enumerate(values):
            rows.append(
                {
                    "draw": draw,
                    "fold": fold,
                    "A": {arm: {"paired_delta": delta} for arm in ("A1", "A2")},
                    "B": {arm: {"paired_delta": delta} for arm in ("B1", "B2")},
                }
            )
    return rows


def test_confirmation_draw_is_counted_only_after_complete_screen_passes() -> None:
    passing = [0.008, 0.007, 0.006, -0.001]  # mean +0.005, three positive quadrants
    rows = make_rows({0: passing, 1: passing, 2: passing, 3: [-0.001] * 4})

    gate = summarize_gate(rows)

    for arm in ("A1", "A2", "B1", "B2"):
        assert gate[arm]["screen_pass"] is True
        assert gate[arm]["confirmation_eligible"] is True
        assert gate[arm]["confirm_draw"] == "draw2"
        assert gate[arm]["PASS"] is True
        assert gate[arm]["per_draw"]["draw2"]["n_folds"] == 4


def test_extra_draw_cannot_rescue_failed_screen() -> None:
    failing_screen = [0.004, 0.004, 0.004, 0.004]
    passing_extra = [0.008, 0.007, 0.006, -0.001]
    rows = make_rows({0: failing_screen, 1: failing_screen, 2: passing_extra})

    gate = summarize_gate(rows)

    for arm in ("A1", "A2", "B1", "B2"):
        assert gate[arm]["screen_pass"] is False
        assert gate[arm]["confirmation_eligible"] is False
        assert gate[arm]["confirm_draw"] is None
        assert gate[arm]["PASS"] is False
        assert 0.00499 < gate[arm]["per_draw"]["draw2"]["mean_delta"] <= 0.005


def test_incomplete_spatial_draw_fails_closed() -> None:
    passing = [0.008, 0.007, 0.006, -0.001]
    rows = make_rows({0: passing, 1: passing, 2: passing})
    rows = [row for row in rows if not (row["draw"] == 1 and row["fold"] == 3)]

    gate = summarize_gate(rows)

    assert gate["B2"]["screen_pass"] is False
    assert gate["B2"]["confirmation_eligible"] is False
    assert gate["B2"]["confirm_draw"] is None
    assert gate["B2"]["PASS"] is False


def test_quick_mode_never_passes_or_claims_confirmation() -> None:
    rows = make_rows({0: [0.01] * 4})

    gate = summarize_gate(rows, quick=True)

    for arm in ("A1", "A2", "B1", "B2"):
        assert gate[arm]["screen_pass"] == "quick-mode"
        assert gate[arm]["confirmation_eligible"] is False
        assert gate[arm]["confirm_draw"] is None
        assert gate[arm]["PASS"] is None


def test_reconciled_h29_gate_matches_preserved_raw_evidence() -> None:
    raw_path = ROOT / "evidence" / "history" / "h29_holdout_pre_correction_2026-10-03.json"
    audit_path = ROOT / "evidence" / "h29_gate_reconciled.json"
    raw = json.loads(raw_path.read_text())
    audit = json.loads(audit_path.read_text())

    assert audit["raw_row_count"] == 16
    assert audit["raw_draws"] == [0, 1, 2, 3]
    assert audit["source_sha256"] == hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert audit["reconciled_gate"] == summarize_gate(raw["rows"])
    assert all(not item["screen_pass"] and item["confirm_draw"] is None
               and not item["PASS"] for item in audit["reconciled_gate"].values())

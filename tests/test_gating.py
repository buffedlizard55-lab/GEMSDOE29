import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems29.gating import gate_from_rows  # noqa: E402


def rows_for(deltas_by_draw):
    rows = []
    for draw, deltas in deltas_by_draw.items():
        for fold, delta in enumerate(deltas):
            rows.append({"draw": draw, "fold": fold, "B": {"B3": {"paired_delta_best_control": delta}}})
    return rows


def test_full_gate_reads_confirmation_draw_two_or_three():
    rows = rows_for({
        0: [0.008, 0.008, 0.008, -0.001],
        1: [0.006, 0.006, 0.006, 0.006],
        2: [0.008, 0.008, 0.008, -0.001],
        3: [0.0, 0.0, 0.0, 0.0],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is True
    assert gate["confirm_draw"] == "draw2"
    assert gate["PASS"] is True
    assert gate["per_draw"]["draw2"]["complete"]


def test_gate_fails_when_confirmation_draws_fail():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006, 0.006],
        2: [0.004, 0.004, 0.004, 0.004],
        3: [0.0, 0.0, 0.0, 0.0],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is True
    assert gate["confirm_draw"] is None
    assert gate["PASS"] is False


def test_screen_failure_is_final_without_wasting_confirmation_fits():
    rows = rows_for({
        0: [-0.01, -0.01, -0.01, -0.01],
        1: [-0.01, -0.01, -0.01, -0.01],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is False
    assert gate["PASS"] is False
    assert gate["per_draw"]["draw2"]["complete"] is False


def test_one_complete_passing_confirmation_is_sufficient():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006, 0.006],
        2: [0.006, 0.006, 0.006, 0.006],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is True
    assert gate["confirm_draw"] == "draw2"
    assert gate["PASS"] is True
    assert gate["complete_confirmation_draws"] == ["draw2"]
    assert not gate["per_draw"]["draw3"]["complete"]


def test_failed_confirmation_with_another_missing_is_indeterminate():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006, 0.006],
        2: [0.004, 0.004, 0.004, 0.004],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is True
    assert gate["confirm_draw"] is None
    assert gate["PASS"] is None
    assert gate["complete_confirmation_draws"] == ["draw2"]


def test_draw_three_can_be_the_single_passing_confirmation():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006, 0.006],
        3: [0.007, 0.007, 0.007, 0.007],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is True
    assert gate["confirm_draw"] == "draw3"
    assert gate["PASS"] is True


def test_gate_requires_four_unique_folds_and_both_screen_draws():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006],
        2: [0.006, 0.006, 0.006, 0.006],
        3: [0.006, 0.006, 0.006, 0.006],
    })
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is None
    assert gate["PASS"] is None


def test_wrong_fold_ids_cannot_complete_a_draw():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006, 0.006],
        2: [0.006, 0.006, 0.006, 0.006],
    })
    for row in rows:
        if row["draw"] == 0:
            row["fold"] += 1
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is None
    assert not gate["per_draw"]["draw0"]["fold_ids_valid"]
    assert gate["PASS"] is None


def test_nonfinite_delta_cannot_complete_a_draw():
    rows = rows_for({
        0: [0.006, 0.006, 0.006, 0.006],
        1: [0.006, 0.006, 0.006, 0.006],
        2: [0.006, 0.006, 0.006, 0.006],
    })
    rows[0]["B"]["B3"]["paired_delta_best_control"] = float("nan")
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["screen_pass"] is None
    assert not gate["per_draw"]["draw0"]["all_deltas_finite"]
    assert gate["per_draw"]["draw0"]["mean_delta"] is None
    assert gate["PASS"] is None


def test_quick_style_rows_cannot_pass_or_fail_full_gate():
    rows = rows_for({0: [0.2], 1: [0.2]})
    gate = gate_from_rows(rows, family="B", arm="B3", delta_key="paired_delta_best_control")
    assert gate["PASS"] is None

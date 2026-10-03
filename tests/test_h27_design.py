import pytest

from gemsdoe.design import factorial_2x2_effects, h27_promotion_gate


def test_two_by_two_contrasts_recover_coded_main_and_interaction_effects():
    # y = 10 + 2T + 3S + 4(T*S), with T,S coded -1/+1.
    y = {
        "BASE": 10 - 2 - 3 + 4,
        "T": 10 + 2 - 3 - 4,
        "S": 10 - 2 + 3 - 4,
        "TS": 10 + 2 + 3 + 4,
    }
    assert factorial_2x2_effects(y) == {"T": 4.0, "S": 6.0, "T_x_S": 8.0}


def test_h27_gate_requires_absolute_holdout_win_and_paired_gain():
    passed = h27_promotion_gate([0.160, 0.161, 0.159, 0.162], [0.158, 0.159, 0.158, 0.160], 0.02)
    assert passed["historical_comparator_passed"]
    assert passed["paired_gate_passed"]
    assert passed["passed"]

    absolute_fail = h27_promotion_gate([0.150, 0.151, 0.149, 0.151], [0.147, 0.148, 0.147, 0.148], 0.01)
    assert absolute_fail["paired_gate_passed"]
    assert not absolute_fail["historical_comparator_passed"]
    assert not absolute_fail["passed"]

    paired_fail = h27_promotion_gate([0.160, 0.160, 0.160, 0.160], [0.159, 0.159, 0.159, 0.159], 0.11)
    assert paired_fail["historical_comparator_passed"]
    assert not paired_fail["paired_gate_passed"]
    assert not paired_fail["passed"]


def test_factorial_analysis_rejects_missing_or_nonfinite_arms():
    with pytest.raises(ValueError):
        factorial_2x2_effects({"BASE": 0.1})
    with pytest.raises(ValueError):
        factorial_2x2_effects({"BASE": 0.1, "T": 0.2, "S": 0.3, "TS": float("nan")})

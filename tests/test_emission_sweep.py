"""Synthetic tests for the frozen emission sweep (knowledge/27) and the shared proxy module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.proxies import ProxyContext, paired_catalogue_hidden, score_mask  # noqa: E402
from gemsdoe.thinning import dot_thin  # noqa: E402

spec = importlib.util.spec_from_file_location("run_emission_sweep", ROOT / "scripts" / "run_emission_sweep.py")
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)


def synthetic_ctx(h=64, w=64) -> ProxyContext:
    foot = np.zeros((h, w), bool)
    foot[4:-4, 4:-4] = True
    labels = np.zeros((h, w), bool)
    labels[h // 2, 8 : w - 8] = True  # one long catalogue component through the middle
    sgmc = np.zeros((h, w), bool)
    sgmc[6, 6 : w - 6] = True
    from gemsdoe.holdout import Holdout

    return ProxyContext(foot=foot, labels=labels, sgmc_off=sgmc,
                        near_visible=np.zeros((h, w), bool), holdout=Holdout(foot, labels, 0.2))


def test_build_rows_matches_the_frozen_set():
    parent = np.zeros((32, 32), bool)
    parent[10, 5:27] = True
    rows = sweep.build_rows(parent, parent.astype(np.float32))
    ids = [r["id"] for r in rows]
    assert len(ids) == 15
    assert ids[0] == "cal_solid"
    assert [i for i in ids if i.startswith("thin_")] == [f"thin_{d:g}" for d in sweep.THIN_SPACINGS]
    assert [i for i in ids if i.startswith("aware_")] == [f"aware_{d:g}" for d in sweep.AWARE_SPACINGS]
    assert ids[-2:] == ["cal_d1_5", "cal_d2_8"]
    # calibration slots are placeholders filled from the pinned files, never constructed
    assert all(r["mask"] is None for r in rows if r["id"] in ("cal_d1_5", "cal_d2_8"))
    # the sweep must contain its own determinism control
    thin28 = next(r for r in rows if r["id"] == "thin_2.8")
    assert np.array_equal(thin28["mask"], dot_thin(parent, 2.8))


def test_score_mask_is_bounded_and_deterministic_on_synthetic_grid():
    ctx = synthetic_ctx()
    mask = np.zeros(ctx.foot.shape, bool)
    mask[8, 10:20] = True
    a = score_mask(mask, ctx, "m")
    b = score_mask(mask, ctx, "m")
    assert a == b  # no randomness anywhere in the fixed-file proxy
    assert 0.0 <= a["catalogue_hidden_mean"] <= 1.0
    assert 0.0 <= a["sgmc_off_catalogue"]["dti"] <= 1.0
    assert a["emitted_pixels"] == 10
    assert a["catalogue_hidden_folds_positive_vs_zero"] == 0.0  # nothing emitted inside the hidden quadrant


def test_paired_delta_is_zero_for_the_same_mask():
    ctx = synthetic_ctx()
    mask = np.zeros(ctx.foot.shape, bool)
    mask[8, 10:20] = True
    paired = paired_catalogue_hidden(mask, mask, ctx)
    assert set(paired["cells"]) == {f"draw{d}_fold{f}" for d in (20, 21) for f in range(4)}
    assert paired["mean"] == 0.0


def _row(family, spacing, cat, sgmc, delta):
    return dict(family=family, spacing=spacing, catalogue_hidden_mean=cat,
                sgmc_off_catalogue=dict(dti=sgmc), paired_vs_reference=dict(mean=delta))


def test_decide_keeps_the_reference_when_nothing_is_admissible():
    rows = {
        "cal_solid": _row("calibration", 1.0, 0.05, 0.10, -0.03),
        "cal_d1_5": _row("calibration", 1.5, 0.07, 0.10, -0.01),
        "cal_d2_8": _row("calibration", 2.8, 0.098, 0.0953, 0.0),
        "thin_4.8": _row("thin", 4.8, 0.094, 0.0950, -0.004),
        "aware_3.6": _row("aware", 3.6, 0.090, 0.0990, -0.008),
    }
    d = sweep.decide(rows, rows["cal_d2_8"])
    assert d["proxy_calibration_check"]["calibrated"] is True
    assert d["recommendation"] == "cal_d2_8 (keep the pinned artifact)"
    assert d["slot_implication"].startswith("none")


def test_decide_requires_the_second_proxy_to_hold():
    rows = {
        "cal_solid": _row("calibration", 1.0, 0.05, 0.10, -0.03),
        "cal_d1_5": _row("calibration", 1.5, 0.07, 0.10, -0.01),
        "cal_d2_8": _row("calibration", 2.8, 0.098, 0.0953, 0.0),
        # wins the primary proxy but loses >2 % relative on the second -> NOT admissible
        "thin_4.8": _row("thin", 4.8, 0.110, 0.0900, +0.012),
        # admissible and positive on both
        "thin_3.6": _row("thin", 3.6, 0.104, 0.0951, +0.006),
    }
    d = sweep.decide(rows, rows["cal_d2_8"])
    assert d["admissible"] == ["thin_3.6"]
    assert d["recommendation"] == "thin_3.6"
    assert d["recommendation_is_boundary"] is False


def test_decide_flags_the_boundary_and_an_uncalibrated_proxy():
    rows = {
        "cal_solid": _row("calibration", 1.0, 0.20, 0.10, +0.10),  # proxy prefers the solid parent
        "cal_d1_5": _row("calibration", 1.5, 0.09, 0.10, -0.01),
        "cal_d2_8": _row("calibration", 2.8, 0.098, 0.0953, 0.0),
        "thin_6.4": _row("thin", 6.4, 0.150, 0.0990, +0.030),
    }
    d = sweep.decide(rows, rows["cal_d2_8"])
    assert d["proxy_calibration_check"]["calibrated"] is False
    assert d["selection_labelled_measurement_only"] is True
    assert d["recommendation"] == "thin_6.4"
    assert d["recommendation_is_boundary"] is True

from types import SimpleNamespace

import numpy as np

from gemsdoe.experiment import gather_columns
from gemsdoe.h30 import build_paired_tip_bridge, build_scarp_persistence


def test_paired_bridge_recognizes_cross_strike_subparallel_tips_and_is_bounded():
    h = w = 160
    foot = np.ones((h, w), bool)
    visible = np.zeros((h, w), bool)
    visible[40, 20:51] = True
    visible[48, 47:78] = True  # separate, parallel component with a cross-strike step
    original = visible.copy()

    field, diag = build_paired_tip_bridge(visible, foot, np.flatnonzero(foot.ravel()))
    raster = field.reshape(h, w)

    assert diag["visible_tip_count"] == 4
    assert diag["nearby_pair_count"] >= 1
    assert diag["accepted_pair_count"] >= 1
    assert 0.0 < raster[44, 49] <= 1.0
    assert np.isfinite(field).all() and field.min() >= 0.0 and field.max() <= 1.0
    assert np.array_equal(visible, original)  # must not mutate the visible-only input


def test_paired_bridge_rejects_collinear_single_tip_continuation():
    h = w = 100
    foot = np.ones((h, w), bool)
    visible = np.zeros((h, w), bool)
    visible[50, 15:45] = True
    visible[50, 51:82] = True  # 6-px collinear gap; not a cross-strike relay bridge

    field, diag = build_paired_tip_bridge(visible, foot, np.flatnonzero(foot.ravel()))

    assert diag["visible_tip_count"] == 4
    assert diag["accepted_pair_count"] == 0
    assert not np.any(field)


def test_paired_bridge_never_connects_tips_from_the_same_component():
    h = w = 110
    foot = np.ones((h, w), bool)
    visible = np.zeros((h, w), bool)
    visible[30:61, 30] = True
    visible[30:61, 38] = True
    visible[60, 30:39] = True  # U-shaped trace joins the two nearby endpoints

    field, diag = build_paired_tip_bridge(visible, foot, np.flatnonzero(foot.ravel()))

    assert diag["visible_tip_count"] == 2
    assert diag["nearby_pair_count"] == 1
    assert diag["accepted_pair_count"] == 0
    assert not np.any(field)


def test_paired_bridge_empty_and_invalid_footprint_indices():
    foot = np.ones((20, 20), bool)
    empty = np.zeros_like(foot)
    field, diag = build_paired_tip_bridge(empty, foot, np.flatnonzero(foot.ravel()))
    assert not np.any(field) and diag["visible_tip_count"] == 0

    foot[0, 0] = False
    with np.testing.assert_raises(ValueError):
        build_paired_tip_bridge(empty, foot, np.array([0]))
    with np.testing.assert_raises(ValueError):
        build_paired_tip_bridge(empty, np.ones((19, 20), bool), np.array([], dtype=np.int64))
    with np.testing.assert_raises(ValueError):
        build_paired_tip_bridge(empty, np.ones_like(empty), np.arange(400), min_strike_cos2=1.0)


def test_gather_columns_fills_a_preallocated_matrix_without_touching_appended_columns():
    static = np.arange(3 * 5, dtype=np.float32).reshape(3, 5)
    e = np.arange(7 * 5, dtype=np.float32).reshape(7, 5) + 100.0
    ctx = SimpleNamespace(static=static, extra_names=[], addon=None)
    idx = np.array([1, 4], dtype=np.int64)
    out = np.full((2, 12), -7.0, dtype=np.float32)

    got = gather_columns(ctx, e, idx, extras=False, out=out)

    assert got is out
    assert np.array_equal(got[:, :3], static[:, idx].T)
    assert np.array_equal(got[:, 3:10], e[:, idx].T)
    assert np.all(got[:, 10:] == -7.0)  # caller-owned H27/H30 columns remain for the caller to fill


def test_scarp_persistence_uses_fixed_scales_and_reports_nonfinite_inputs():
    names = ["L_step_max", "L_cross_max", "L_coh100"]
    values = np.array(
        [
            [0.0, 0.5, 1.0, np.nan],
            [0.0, 0.5, 1.0, 1.0],
            [0.0, 0.5, 1.0, 1.0],
        ],
        dtype=np.float32,
    )
    scales = {name: (0.0, 1.0) for name in names}
    feature, diag = build_scarp_persistence(values, names, scales)

    assert np.allclose(feature, [0.0, 0.125, 1.0, 0.0])
    assert diag["source_nonfinite_counts"] == {"L_step_max": 1, "L_cross_max": 0, "L_coh100": 0}
    assert diag["nonzero_fraction"] == 0.5
    assert np.isfinite(feature).all() and feature.min() >= 0.0 and feature.max() <= 1.0

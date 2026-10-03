"""Unit tests for the H52 worming filter fields (survival-with-height, azimuth, convergence).

The physics assertions below are the ones that matter: upward continuation attenuates a potential field
by ``exp(-k h)``, so a short-wavelength (shallow) pattern must *lose* its gradient through the ladder
while a long-wavelength (deep) pattern keeps it. The geometric persistence used by the four earlier
formulations does not discriminate between those two cases, and that is asserted here too.
"""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe.wormfilter import (
    WF_NAMES,
    WormFilterConfig,
    azimuth_veto,
    build_worm_fields,
    shallow_veto,
    veto_rate,
)
from gemsdoe.worms import WormConfig

LADDER = WormConfig(cell_size_m=100.0, heights_m=(0, 100, 200, 400, 800, 1200), taper_px=8, pad_px=16,
                    boundary_guard_px=8, edge_percentile=90.0)
CFG = WormFilterConfig(smooth_sigma_px=0.0)
INTERIOR = (slice(20, 76), slice(20, 76))


def _fields(tmp_path, field: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray], dict]:
    n = field.shape[0]
    foot = np.ones((n, n), bool)
    fi = np.flatnonzero(foot.ravel())
    np.save(tmp_path / "02_rtp.npy", field)
    np.save(tmp_path / "13_iso_grav_anom.npy", field)
    return build_worm_fields(tmp_path, foot, fi, ladder=LADDER, config=CFG)


def _ripple(n: int, wavelength_px: float) -> np.ndarray:
    x = np.arange(n, dtype=np.float32)
    return np.tile(np.sin(2.0 * np.pi * x / wavelength_px), (n, 1)).astype(np.float32)


def test_shallow_ripple_loses_its_gradient_and_deep_structure_keeps_it(tmp_path) -> None:
    n = 96
    _, shallow, ds = _fields(tmp_path, _ripple(n, 4.0))    # 400 m wavelength: shallow by construction
    _, deep, dd = _fields(tmp_path, _ripple(n, 48.0))      # 4800 m wavelength: survives continuation
    surv_s = shallow["WF_SURV_JOINT"][INTERIOR].mean()
    surv_d = deep["WF_SURV_JOINT"][INTERIOR].mean()
    assert surv_s < 0.05, f"a 400 m ripple must not survive continuation (got {surv_s})"
    assert surv_d > 0.5, f"a 4800 m ripple must survive continuation (got {surv_d})"
    # The ridge population collapses under continuation for the shallow pattern only.
    assert ds["magnetic"]["edge_counts"][-1] < 0.1 * ds["magnetic"]["edge_counts"][0]
    assert dd["magnetic"]["edge_counts"][-1] > 0.4 * dd["magnetic"]["edge_counts"][0]
    # Geometric persistence does NOT separate the two: the documented defect of the earlier arms.
    p_s = shallow["WF_P_JOINT"][INTERIOR].mean()
    p_d = deep["WF_P_JOINT"][INTERIOR].mean()
    assert abs(p_s - p_d) < 0.1, f"geometric persistence is near-blind here ({p_s} vs {p_d})"


def test_survival_increases_with_contact_width_and_columns_stay_bounded(tmp_path) -> None:
    """A broader (deeper-equivalent) contact keeps its gradient longer than a mathematically sharp one."""
    from scipy.ndimage import gaussian_filter

    n = 96
    step = np.zeros((n, n), np.float32)
    step[:, n // 2 :] = 10.0
    _, sharp, _ = _fields(tmp_path, step)
    vectors, broad, diag = _fields(tmp_path, gaussian_filter(step, 4.0).astype(np.float32))
    assert vectors.shape == (len(WF_NAMES), 96 * 96)
    assert np.isfinite(vectors).all()
    assert ((vectors >= 0.0) & (vectors <= 1.0)).all()
    surv_sharp = float(sharp["WF_SURV_JOINT"][n // 2, n // 2])
    surv_broad = float(broad["WF_SURV_JOINT"][n // 2, n // 2])
    assert surv_broad >= 0.5, f"a 400 m-wide contact must survive the ladder (got {surv_broad})"
    assert surv_broad > surv_sharp, f"the broad contact must out-survive the sharp one ({surv_broad} vs {surv_sharp})"
    assert broad["WF_SHALLOW_ONLY"][n // 2, n // 2] == 0.0
    assert diag["nonzero_fraction"]["WF_SHALLOW_ONLY"] < 0.2
    assert 0.0 <= broad["WF_CONV"].min() and broad["WF_CONV"].max() <= 1.0
    assert diag["magnetic"]["edge_counts"][0] > 0


def test_columns_are_bounded_and_the_shallow_flag_is_a_minority(tmp_path) -> None:
    n = 96
    mixed = _ripple(n, 4.0) + 0.5 * _ripple(n, 40.0)
    vectors, grids, diag = _fields(tmp_path, mixed)
    assert ((vectors >= 0.0) & (vectors <= 1.0)).all()
    frac = diag["nonzero_fraction"]["WF_SHALLOW_ONLY"]
    assert 0.0 < frac < 0.95, f"the shallow flag must be neither empty nor everything (got {frac})"
    for name in WF_NAMES:
        assert np.isfinite(grids[name]).all(), name


def test_azimuth_agreement_is_one_for_parallel_fields_and_zero_for_perpendicular(tmp_path) -> None:
    n = 64
    foot = np.ones((n, n), bool)
    fi = np.flatnonzero(foot.ravel())
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    mag = (xx * 0.5 + 3.0 * np.sin(xx / 6.0)).astype(np.float32)
    grav_parallel = (xx * 0.25 - 2.0 * np.sin(xx / 6.0 + 0.4)).astype(np.float32)
    grav_perp = (yy * 0.25 - 2.0 * np.sin(yy / 6.0 + 0.4)).astype(np.float32)
    np.save(tmp_path / "02_rtp.npy", mag)
    np.save(tmp_path / "13_iso_grav_anom.npy", grav_parallel)
    _, par, _ = build_worm_fields(tmp_path, foot, fi, ladder=LADDER, config=CFG)
    np.save(tmp_path / "13_iso_grav_anom.npy", grav_perp)
    _, rot, diag = build_worm_fields(tmp_path, foot, fi, ladder=LADDER, config=CFG)
    sel = par["WF_AZ_DEFINED"] > 0.5
    assert sel.sum() > 100, "the synthetic grids must produce a defined azimuth population"
    assert par["WF_AZ_AGREE"][sel].mean() > 0.9, "parallel edges must agree"
    sel_r = rot["WF_AZ_DEFINED"] > 0.5
    assert rot["WF_AZ_AGREE"][sel_r].mean() < 0.1, "perpendicular edges must not agree"
    assert diag["azimuth_defined_pixels"] > 0


def test_emission_filters_remove_only_defined_candidates() -> None:
    cand = np.zeros((9, 9), bool)
    cand[2, 2] = cand[4, 4] = cand[6, 6] = True
    shallow = np.zeros((9, 9), np.float32)
    shallow[4, 4] = 1.0
    assert shallow_veto(cand, shallow).sum() == 1
    assert shallow_veto(cand, shallow)[4, 4]

    az = np.full((9, 9), 0.5, np.float32)
    az[6, 6] = 0.1
    defined = np.zeros((9, 9), np.float32)
    defined[2, 2] = 1.0  # defined but agreeing -> kept
    defined[6, 6] = 1.0  # defined and disagreeing -> vetoed
    veto = azimuth_veto(cand, az, defined, 0.5)
    assert veto.sum() == 1 and veto[6, 6]
    # An undefined azimuth never vetoes, even when the value is low (the H29 A1 convention).
    assert azimuth_veto(cand, az, np.zeros((9, 9), np.float32), 0.5).sum() == 0
    assert veto_rate(cand, veto) == pytest.approx(1 / 3)
    assert veto_rate(np.zeros((9, 9), bool), veto) == 0.0


def test_filter_and_config_validation() -> None:
    cand = np.zeros((5, 5), bool)
    with pytest.raises(ValueError):
        shallow_veto(cand, np.zeros((6, 6), np.float32))
    with pytest.raises(ValueError):
        azimuth_veto(cand, np.zeros((5, 5), np.float32), np.zeros((5, 5), np.float32), 1.5)
    for bad in (WormFilterConfig(tau_survival=1.4), WormFilterConfig(tol_px=0.0),
                WormFilterConfig(convergence_radius_px=-1.0), WormFilterConfig(rho_retention=0.0),
                WormFilterConfig(min_contrast_fraction=2.0)):
        with pytest.raises(ValueError):
            bad.validate()


def test_build_worm_fields_validates_alignment(tmp_path) -> None:
    foot = np.ones((16, 16), bool)
    np.save(tmp_path / "02_rtp.npy", np.zeros((16, 16), np.float32))
    np.save(tmp_path / "13_iso_grav_anom.npy", np.zeros((17, 16), np.float32))
    with pytest.raises(ValueError):
        build_worm_fields(tmp_path, foot, np.flatnonzero(foot.ravel()), ladder=LADDER)
    np.save(tmp_path / "13_iso_grav_anom.npy", np.zeros((16, 16), np.float32))
    with pytest.raises(ValueError):
        build_worm_fields(tmp_path, foot, np.array([3, 1, 2]), ladder=LADDER)  # non-monotone indices

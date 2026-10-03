from __future__ import annotations

import numpy as np
import pytest
from scipy.ndimage import maximum_filter

from gemsdoe.worms import (
    H31_NAMES,
    WormConfig,
    _prepare_spectrum,
    build_edge_persistence,
    build_h31_features,
)


def _step_grid(size: int = 160) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[:size, :size]
    footprint = np.zeros((size, size), dtype=bool)
    footprint[16:-16, 16:-16] = True
    field = np.tanh((x - size / 2) / 2.5).astype(np.float32)
    field += (y.astype(np.float32) - size / 2) * 0.0002
    field[~footprint] = np.nan
    return field, footprint


def _test_config(**overrides) -> WormConfig:
    values = dict(
        cell_size_m=100.0,
        heights_m=(0, 100, 200),
        taper_px=16,
        pad_px=16,
        boundary_guard_px=16,
        edge_percentile=90.0,
        max_match_px=2.0,
    )
    values.update(overrides)
    return WormConfig(**values)


def test_worm_config_defaults_match_preregistered_scale_settings() -> None:
    config = WormConfig()
    config.validate()
    assert config.cell_size_m == 100.0
    assert config.heights_m == (0, 100, 200, 400, 800, 1200)
    assert config.taper_px == 64 and config.pad_px == 128 and config.boundary_guard_px == 16
    assert config.edge_percentile == 90.0 and config.max_match_px == 2.0


def test_worm_config_rejects_nonincreasing_heights_and_noninteger_padding() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        WormConfig(heights_m=(0, 200, 100)).validate()
    with pytest.raises(ValueError, match="pad_px must be an integer"):
        WormConfig(pad_px=2.5).validate()


def test_prepare_spectrum_regularizes_rtp_pseudogravity_and_sets_dc_zero() -> None:
    field, footprint = _step_grid()
    fi = np.flatnonzero(footprint.ravel())
    config = _test_config(pseudogravity_vertical_integration=True)
    spectrum, radial_k, safe, returned_foot, diag = _prepare_spectrum(field, footprint, config=config)
    assert spectrum.shape == radial_k.shape
    assert spectrum[0, 0] == 0
    assert safe.shape == field.shape and returned_foot.shape == field.shape
    assert diag["vertical_integration_proxy"] is True
    assert diag["safe_edge_pixels"] > 0
    assert fi.size == footprint.sum()
    assert np.isfinite(spectrum).all()


def test_scale_persistence_tracks_a_synthetic_edge_and_masks_boundary() -> None:
    field, footprint = _step_grid()
    fi = np.flatnonzero(footprint.ravel())
    persist, drift, diag = build_edge_persistence(
        field,
        footprint,
        fi,
        config=_test_config(),
    )
    assert persist.shape == drift.shape == (fi.size,)
    assert np.isfinite(persist).all() and np.isfinite(drift).all()
    assert np.all((persist >= 0) & (persist <= 1))
    assert np.all((drift >= 0) & (drift <= 1))
    # The synthetic edge is vertical and should contain a persistent local-maximum path.
    line_flat = np.arange(field.shape[0]) * field.shape[1] + field.shape[1] // 2
    loc = np.searchsorted(fi, line_flat)
    loc = loc[(loc < fi.size) & (fi[np.minimum(loc, fi.size - 1)] == line_flat)]
    assert persist[loc].max(initial=0) > 0.5
    assert diag["zero_height_seed_count"] > 0
    assert diag["tracks_matched_by_height"][0] >= diag["tracks_matched_by_height"][-1]


def test_nonfinite_input_is_filled_only_for_fft_and_zeroed_in_feature_output() -> None:
    field, footprint = _step_grid()
    hole = (field.shape[0] // 2, field.shape[1] // 2 + 20)
    field[hole] = np.nan
    fi = np.flatnonzero(footprint.ravel())
    persist, drift, diag = build_edge_persistence(field, footprint, fi, config=_test_config())
    hole_flat = hole[0] * field.shape[1] + hole[1]
    hole_loc = np.searchsorted(fi, hole_flat)
    assert persist[hole_loc] == 0 and drift[hole_loc] == 0
    assert diag["input_nonfinite_inside_footprint"] == 1


def test_joint_feature_uses_preregistered_cross_grid_tolerance() -> None:
    rtp, footprint = _step_grid()
    gravity, _ = _step_grid()
    fi = np.flatnonzero(footprint.ravel())
    config = _test_config()
    features, diag = build_h31_features(rtp, gravity, footprint, fi, config=config)
    assert features.shape == (len(H31_NAMES), fi.size)
    assert diag["feature_names"] == H31_NAMES
    assert np.isfinite(features).all()
    assert np.all((features >= 0) & (features <= 1))
    mag = np.zeros(footprint.shape, dtype=np.float32)
    grav = np.zeros(footprint.shape, dtype=np.float32)
    mag.ravel()[fi] = features[0]
    grav.ravel()[fi] = features[2]
    row_offset, col_offset = np.ogrid[-2:3, -2:3]
    joint_window = (row_offset**2 + col_offset**2) <= 4
    mag_near = maximum_filter(mag, footprint=joint_window, mode="constant", cval=0.0)
    grav_near = maximum_filter(grav, footprint=joint_window, mode="constant", cval=0.0)
    expected_joint = np.maximum(
        np.sqrt(features[0] * grav_near.ravel()[fi]),
        np.sqrt(features[2] * mag_near.ravel()[fi]),
    )
    assert np.allclose(features[4], expected_joint)
    assert diag["joint_persistence_nonzero_fraction"] > 0


def test_empty_finite_footprint_fails_closed() -> None:
    values = np.full((32, 32), np.nan, dtype=np.float32)
    footprint = np.ones((32, 32), dtype=bool)
    fi = np.flatnonzero(footprint.ravel())
    with pytest.raises(ValueError, match="no finite field values"):
        build_edge_persistence(values, footprint, fi, config=_test_config(taper_px=4, pad_px=4, boundary_guard_px=0))


def test_constant_field_has_no_false_local_maxima() -> None:
    footprint = np.ones((48, 52), dtype=bool)
    values = np.full(footprint.shape, 37.5, dtype=np.float32)
    fi = np.flatnonzero(footprint.ravel())
    persistence, drift, diag = build_edge_persistence(values, footprint, fi, config=_test_config())
    assert np.count_nonzero(persistence) == 0
    assert np.count_nonzero(drift) == 0
    assert diag["zero_height_seed_count"] == 0

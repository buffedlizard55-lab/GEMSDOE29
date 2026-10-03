"""Preregistered H31 worming-like scale-space edge-persistence features.

This module intentionally stops short of a full Poisson-wavelet worm inversion. It builds a documented,
regularized vertical-integration pseudogravity proxy from an RTP grid, upward-continues that spectrum, and tracks
thresholded horizontal-gradient maxima through a finite set of heights. No labels or catalogue geometry enter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import fft
from scipy.ndimage import distance_transform_edt, maximum_filter


H31_NAMES = [
    "H31_PSG_PERSIST",
    "H31_PSG_DRIFT",
    "H31_GRAV_PERSIST",
    "H31_GRAV_DRIFT",
    "H31_JOINT_PERSIST",
]
H31_HEIGHTS_M = (0, 100, 200, 400, 800, 1_200)


@dataclass(frozen=True)
class WormConfig:
    cell_size_m: float = 100.0
    heights_m: tuple[int, ...] = H31_HEIGHTS_M
    taper_px: int = 64
    pad_px: int = 128
    boundary_guard_px: int = 16
    edge_percentile: float = 90.0
    max_match_px: float = 2.0
    pseudogravity_vertical_integration: bool = False

    def validate(self) -> None:
        if not np.isfinite(self.cell_size_m) or self.cell_size_m <= 0:
            raise ValueError("cell_size_m must be finite and positive")
        if len(self.heights_m) < 2 or self.heights_m[0] != 0:
            raise ValueError("heights_m must contain at least two values and start at zero")
        if any((not isinstance(h, (int, np.integer)) or h < 0) for h in self.heights_m):
            raise ValueError("heights_m must be nonnegative integer metres")
        if tuple(sorted(set(self.heights_m))) != tuple(self.heights_m):
            raise ValueError("heights_m must be strictly increasing")
        for name, value in (("taper_px", self.taper_px), ("pad_px", self.pad_px), ("boundary_guard_px", self.boundary_guard_px)):
            if not isinstance(value, (int, np.integer)):
                raise ValueError(f"{name} must be an integer")
        if self.taper_px < 1 or self.pad_px < 1 or self.boundary_guard_px < 0:
            raise ValueError("taper/pad must be positive and the boundary guard nonnegative")
        if not np.isfinite(self.edge_percentile) or not 0 < self.edge_percentile < 100:
            raise ValueError("edge_percentile must lie strictly between 0 and 100")
        if not np.isfinite(self.max_match_px) or self.max_match_px <= 0:
            raise ValueError("max_match_px must be finite and positive")


def _nearest_finite_fill(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill invalid cells from their nearest valid cell for FFT boundary preparation only."""
    if not valid.any():
        raise ValueError("no finite field values inside the footprint")
    if valid.all():
        return np.asarray(values, dtype=np.float32).copy()
    index = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return np.asarray(values, dtype=np.float32)[tuple(index)].astype(np.float32, copy=False)


def _prepare_spectrum(
    values: np.ndarray,
    footprint: np.ndarray,
    *,
    config: WormConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Mean-center, cosine-taper, pad, FFT, and optionally vertically integrate an aligned field."""
    config.validate()
    field = np.asarray(values)
    foot = np.asarray(footprint, dtype=bool)
    if field.ndim != 2 or field.shape != foot.shape:
        raise ValueError("values and footprint must be aligned two-dimensional arrays")
    valid = foot & np.isfinite(field)
    n_valid = int(valid.sum())
    if n_valid == 0:
        raise ValueError("no finite field values inside the footprint")
    if n_valid < 100:
        raise ValueError(f"too few finite in-footprint samples: {n_valid}")

    # Distance to the footprint boundary, treating the outer raster edge as outside too.
    padded_foot = np.pad(foot, 1, mode="constant", constant_values=False)
    edge_distance = distance_transform_edt(padded_foot)[1:-1, 1:-1]
    safe = valid & (edge_distance >= config.boundary_guard_px)
    n_safe = int(safe.sum())
    if n_safe < 100:
        raise ValueError(f"too few finite pixels remain after the {config.boundary_guard_px}-px edge guard: {n_safe}")

    # This interpolation is used only to make a finite FFT boundary condition. The final features are masked
    # back to original finite pixels well inside the valid footprint.
    filled = _nearest_finite_fill(np.where(valid, field, np.nan), valid)
    mean = float(np.mean(np.asarray(field, dtype=np.float32)[valid], dtype=np.float64))
    work = np.zeros(field.shape, dtype=np.float32)
    work[foot] = filled[foot] - np.float32(mean)

    taper = np.zeros(field.shape, dtype=np.float32)
    ratio = np.clip(edge_distance / np.float32(config.taper_px), 0.0, 1.0).astype(np.float32)
    taper[foot] = (0.5 - 0.5 * np.cos(np.pi * ratio[foot])).astype(np.float32)
    work *= taper
    del filled, taper, ratio, edge_distance, padded_foot

    p = config.pad_px
    padded = np.pad(work, ((p, p), (p, p)), mode="reflect")
    del work
    spectrum = fft.rfft2(padded, workers=1)
    rows, cols = padded.shape
    ky = fft.fftfreq(rows, d=config.cell_size_m).astype(np.float32)
    kx = fft.rfftfreq(cols, d=config.cell_size_m).astype(np.float32)
    radial_k = (np.float32(2.0 * np.pi) * np.hypot(ky[:, None], kx[None, :])).astype(np.float32)
    k_floor = np.float32(2.0 * np.pi / (min(field.shape) * config.cell_size_m))

    if config.pseudogravity_vertical_integration:
        # Regularized vertical integration in the Fourier domain. The physical scale factor is immaterial for
        # edge locations; this is documented as a proxy, not as a vendor-exact GPSD filter.
        denom = np.maximum(radial_k, k_floor)
        spectrum /= denom
        spectrum[0, 0] = 0.0
        del denom

    diag = {
        "input_shape": [int(field.shape[0]), int(field.shape[1])],
        "cell_size_m": float(config.cell_size_m),
        "input_valid_pixels": n_valid,
        "safe_edge_pixels": n_safe,
        "boundary_guard_removed_pixels": int(n_valid - n_safe),
        "input_nonfinite_inside_footprint": int(foot.sum() - n_valid),
        "mean_removed": mean,
        "taper_px": int(config.taper_px),
        "padding_px": int(config.pad_px),
        "low_wavenumber_floor_rad_per_m": float(k_floor),
        "vertical_integration_proxy": bool(config.pseudogravity_vertical_integration),
    }
    return spectrum, radial_k, safe, foot, diag


def _edge_maxima(
    spectrum: np.ndarray,
    radial_k: np.ndarray,
    safe: np.ndarray,
    *,
    original_shape: tuple[int, int],
    config: WormConfig,
    height_m: int,
) -> tuple[np.ndarray, float]:
    """Local maxima of horizontal-gradient modulus at one upward-continuation height."""
    transfer = np.exp(-np.float32(height_m) * radial_k).astype(np.float32, copy=False)
    continued_spectrum = spectrum * transfer
    del transfer
    p = config.pad_px
    padded_shape = (original_shape[0] + 2 * p, original_shape[1] + 2 * p)
    continued = fft.irfft2(continued_spectrum, s=padded_shape, workers=1).astype(np.float32, copy=False)
    del continued_spectrum
    crop = continued[p : p + original_shape[0], p : p + original_shape[1]]
    gy, gx = np.gradient(crop, config.cell_size_m, config.cell_size_m)
    modulus = np.hypot(gx, gy).astype(np.float32, copy=False)
    del continued, crop, gx, gy

    safe_modulus = modulus[safe]
    threshold = float(np.percentile(safe_modulus, config.edge_percentile))
    grad_max = float(safe_modulus.max())
    grad_min = float(safe_modulus.min())
    contrast = grad_max - grad_min
    scale = max(grad_max, np.finfo(np.float32).tiny)
    if scale <= np.finfo(np.float32).tiny or contrast <= np.finfo(np.float32).eps * scale:
        # A constant/flat field has no edge even though every pixel equals its local maximum.
        del modulus, safe_modulus
        return np.zeros_like(safe, dtype=bool), threshold
    local_max = maximum_filter(modulus, size=3, mode="nearest")
    mask = safe & (modulus >= local_max) & (modulus >= threshold)
    del local_max, modulus, safe_modulus
    return mask, threshold


def build_edge_persistence(
    values: np.ndarray,
    footprint: np.ndarray,
    footprint_idx: np.ndarray,
    *,
    config: WormConfig | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Compute footprint-vector persistence/drift features and diagnostics for one scalar potential field.

    ``values`` and ``footprint`` are full-grid arrays. Output vectors follow sorted flat ``footprint_idx`` and
    are zero outside finite pixels at least ``boundary_guard_px`` from the footprint edge. Paths start at local
    maxima on the zero-height grid and follow the nearest local maximum within ``max_match_px`` at each height.
    """
    cfg = config or WormConfig()
    cfg.validate()
    field = np.asarray(values)
    foot = np.asarray(footprint, bool)
    fi = np.asarray(footprint_idx)
    if fi.ndim != 1 or (fi.size and not np.issubdtype(fi.dtype, np.integer)):
        raise ValueError("footprint_idx must be a one-dimensional integer array")
    fi = fi.astype(np.int64, copy=False)
    if fi.size and (np.diff(fi) <= 0).any():
        raise ValueError("footprint_idx must be strictly increasing and unique")
    if field.ndim != 2 or field.shape != foot.shape:
        raise ValueError("field/footprint grid mismatch")
    if fi.size and ((fi < 0).any() or (fi >= field.size).any() or not foot.ravel()[fi].all()):
        raise ValueError("footprint_idx must contain only in-footprint flat indices")

    spectrum, radial_k, safe, _, diag = _prepare_spectrum(field, foot, config=cfg)
    thresholds: list[float] = []
    edge_counts: list[int] = []
    match_counts: list[int] = []
    base_y: np.ndarray | None = None
    base_x: np.ndarray | None = None
    track_y: np.ndarray | None = None
    track_x: np.ndarray | None = None
    active: np.ndarray | None = None
    visits: np.ndarray | None = None
    drift: np.ndarray | None = None

    for level, height in enumerate(cfg.heights_m):
        edges, threshold = _edge_maxima(
            spectrum,
            radial_k,
            safe,
            original_shape=field.shape,
            config=cfg,
            height_m=height,
        )
        thresholds.append(threshold)
        edge_counts.append(int(edges.sum()))
        if level == 0:
            base_y, base_x = np.nonzero(edges)
            track_y = base_y.astype(np.int32, copy=True)
            track_x = base_x.astype(np.int32, copy=True)
            active = np.ones(base_y.size, dtype=bool)
            visits = np.ones(base_y.size, dtype=np.uint8)
            drift = np.zeros(base_y.size, dtype=np.float32)
            match_counts.append(int(base_y.size))
            del edges
            continue

        assert track_y is not None and track_x is not None and active is not None and visits is not None and drift is not None
        if not active.any() or not edges.any():
            active[:] = False
            match_counts.append(0)
            del edges
            continue

        distance, nearest = distance_transform_edt(~edges, return_indices=True)
        active_idx = np.flatnonzero(active)
        old_y = track_y[active_idx]
        old_x = track_x[active_idx]
        d = distance[old_y, old_x]
        matched = d <= cfg.max_match_px
        lost_idx = active_idx[~matched]
        active[lost_idx] = False
        kept = active_idx[matched]
        new_y = nearest[0, old_y[matched], old_x[matched]]
        new_x = nearest[1, old_y[matched], old_x[matched]]
        if kept.size:
            step = np.hypot(new_y.astype(np.float32) - old_y[matched], new_x.astype(np.float32) - old_x[matched])
            drift[kept] += step
            visits[kept] += 1
            track_y[kept] = new_y
            track_x[kept] = new_x
        match_counts.append(int(kept.size))
        del distance, nearest, active_idx, old_y, old_x, d, matched, lost_idx, kept, new_y, new_x, edges

    assert base_y is not None and base_x is not None and visits is not None and drift is not None
    persist_vec = np.zeros(fi.size, dtype=np.float32)
    drift_vec = np.zeros(fi.size, dtype=np.float32)
    if base_y.size:
        flat = base_y.astype(np.int64) * field.shape[1] + base_x.astype(np.int64)
        loc = np.searchsorted(fi, flat)
        if np.any(loc >= fi.size) or not np.array_equal(fi[loc], flat):
            raise RuntimeError("edge seed index does not map back to the requested footprint vector")
        persist_vec[loc] = visits.astype(np.float32) / np.float32(len(cfg.heights_m))
        max_path_px = cfg.max_match_px * max(1, len(cfg.heights_m) - 1)
        drift_vec[loc] = np.clip(drift / np.float32(max_path_px), 0.0, 1.0)

    if not (np.isfinite(persist_vec).all() and np.isfinite(drift_vec).all()):
        raise FloatingPointError("H31 persistence/drift output contains NaN/Inf")
    if (persist_vec < 0).any() or (persist_vec > 1).any() or (drift_vec < 0).any() or (drift_vec > 1).any():
        raise FloatingPointError("H31 persistence/drift escaped [0,1]")

    diag.update(
        {
            "height_sequence_m": list(cfg.heights_m),
            "edge_percentile": float(cfg.edge_percentile),
            "max_match_px": float(cfg.max_match_px),
            "height_thresholds_gradient_modulus": thresholds,
            "local_maxima_count_by_height": edge_counts,
            "tracks_matched_by_height": match_counts,
            "zero_height_seed_count": int(base_y.size),
            "persistent_fraction_at_last_height": float(np.mean(visits == len(cfg.heights_m))) if visits.size else 0.0,
            "output_nonzero_fraction_persistence": float(np.count_nonzero(persist_vec) / max(1, persist_vec.size)),
            "output_nonzero_fraction_drift": float(np.count_nonzero(drift_vec) / max(1, drift_vec.size)),
            "persistence_max": float(persist_vec.max(initial=0.0)),
            "drift_max": float(drift_vec.max(initial=0.0)),
        }
    )
    return persist_vec, drift_vec, diag


def build_h31_features(
    rtp: np.ndarray,
    gravity: np.ndarray,
    footprint: np.ndarray,
    footprint_idx: np.ndarray,
    *,
    config: WormConfig | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build the five preregistered H31 predictors from RTP and isostatic gravity grids."""
    cfg = config or WormConfig()
    cfg.validate()
    psg_cfg = WormConfig(
        cell_size_m=cfg.cell_size_m,
        heights_m=cfg.heights_m,
        taper_px=cfg.taper_px,
        pad_px=cfg.pad_px,
        boundary_guard_px=cfg.boundary_guard_px,
        edge_percentile=cfg.edge_percentile,
        max_match_px=cfg.max_match_px,
        pseudogravity_vertical_integration=True,
    )
    grav_cfg = WormConfig(
        cell_size_m=cfg.cell_size_m,
        heights_m=cfg.heights_m,
        taper_px=cfg.taper_px,
        pad_px=cfg.pad_px,
        boundary_guard_px=cfg.boundary_guard_px,
        edge_percentile=cfg.edge_percentile,
        max_match_px=cfg.max_match_px,
        pseudogravity_vertical_integration=False,
    )

    mag_persist, mag_drift, mag_diag = build_edge_persistence(
        rtp, footprint, footprint_idx, config=psg_cfg
    )
    grav_persist, grav_drift, grav_diag = build_edge_persistence(
        gravity, footprint, footprint_idx, config=grav_cfg
    )
    fi = np.asarray(footprint_idx, dtype=np.int64)
    mag_grid = np.zeros(np.asarray(footprint).shape, dtype=np.float32)
    grav_grid = np.zeros(np.asarray(footprint).shape, dtype=np.float32)
    mag_grid.ravel()[fi] = mag_persist
    grav_grid.ravel()[fi] = grav_persist
    row_offset, col_offset = np.ogrid[-2:3, -2:3]
    joint_window = (row_offset**2 + col_offset**2) <= 4
    mag_near = maximum_filter(mag_grid, footprint=joint_window, mode="constant", cval=0.0)
    grav_near = maximum_filter(grav_grid, footprint=joint_window, mode="constant", cval=0.0)
    joint = np.maximum(
        np.sqrt(mag_persist * grav_near.ravel()[fi]),
        np.sqrt(grav_persist * mag_near.ravel()[fi]),
    ).astype(np.float32, copy=False)
    del mag_grid, grav_grid, mag_near, grav_near
    features = np.vstack((mag_persist, mag_drift, grav_persist, grav_drift, joint)).astype(np.float32, copy=False)
    if features.shape != (len(H31_NAMES), len(footprint_idx)):
        raise RuntimeError(f"unexpected H31 feature matrix shape: {features.shape}")
    if not np.isfinite(features).all() or (features < 0).any() or (features > 1).any():
        raise FloatingPointError("H31 feature matrix must be finite and in [0,1]")
    diagnostics = {
        "config": {
            "cell_size_m": cfg.cell_size_m,
            "height_sequence_m": list(cfg.heights_m),
            "taper_px": cfg.taper_px,
            "pad_px": cfg.pad_px,
            "boundary_guard_px": cfg.boundary_guard_px,
            "edge_percentile": cfg.edge_percentile,
            "max_match_px": cfg.max_match_px,
            "pseudogravity_filter": "RTP Fourier coefficients divided by max(radial_wavenumber, 2*pi/(min(original_shape)*cell_size_m)); DC=0",
            "continuation_filter": "exp(-height_m * radial_wavenumber), radial_wavenumber in radians/metre",
            "edge_definition": "3x3 local maxima of horizontal-gradient modulus above per-height 90th percentile",
            "track_definition": "nearest edge maximum within 2 px at each height; stop on first unmatched scale",
            "joint_persistence_definition": "symmetric max of the two geometric means using the opposite-field persistence maximum within Euclidean radius 2 px (5x5 bounding window; corners excluded)",
        },
        "psg": mag_diag,
        "isostatic_gravity": grav_diag,
        "joint_persistence_nonzero_fraction": float(np.count_nonzero(joint) / max(1, joint.size)),
        "joint_persistence_max": float(joint.max(initial=0.0)),
        "n_features": len(H31_NAMES),
        "feature_names": H31_NAMES,
    }
    return features, diagnostics

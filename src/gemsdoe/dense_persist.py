"""H40 dense continuation-persistence fields (the corrected "worming" surface after the H31 failure).

The H31 screen failed because its persistence features were *seed-track* features: binary peak sets that
were nonzero on only 0.001-0.084 % of the footprint, so the emission arms were indistinguishable
(``knowledge/16_h31_screen_results_2026-10-03.md``). This module keeps the same multiscale physics -
edge detection on upward-continued copies of the same grid (Hornby, Boschetti & Horowitz 1999,
doi:10.1111/j.1365-2478.1999.ggg031.x; GGA "worming" tradition) - but emits a *continuous surface*: for
every footprint pixel, the weighted fraction of continuation heights at which a thresholded horizontal-
gradient ridge lies within a small tolerance, smoothed over the grid. No binarisation, no seeding, and no
tracking, so no sparsity pathology is possible. Persistence with HEIGHT is the explicit feature:
edges that survive progressive smoothing are attributed to deeper equivalent sources; edges that vanish
immediately are treated as shallow (and are distrusted by construction, per the project brief).

Columns (frozen, all float32 in [0, 1], footprint-vector order):

* ``HP_MAG``   - persistence fraction of the reduced-to-the-pole magnetic field (band 2, ``rtp``).
* ``HP_GRAV``  - persistence fraction of the isostatic residual gravity (band 13, ``iso_grav_anom``).
* ``HP_MIN``   - pixelwise minimum of the two (cross-field joint persistence).
* ``HP_DEEP``  - fraction over heights >= 400 m only for the magnetic field, i.e. survival deep into the
  ladder (the explicit "genuinely deep source" contrast).

Upward continuation is applied in the Fourier domain with the H31 spectrum preparation
(mean centring, cosine taper, reflect padding, 16-px boundary guard) so the continuation operator matches
the frozen H29/H31 machinery exactly; ``WormConfig`` parameters are re-used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from .worms import WormConfig, _edge_maxima, _prepare_spectrum

HP_NAMES = ["HP_MAG", "HP_GRAV", "HP_MIN", "HP_DEEP"]
DEEP_FIRST_LEVEL = 3  # heights_m[3] = 400 m in the frozen ladder (0, 100, 200, 400, 800, 1200)


def _persistence_grid(values: np.ndarray, foot: np.ndarray, cfg: WormConfig,
                      tol_px: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Weighted fraction of continuation heights with a ridge edge within ``tol_px`` of each safe pixel."""
    spectrum, radial_k, safe, _, diag = _prepare_spectrum(values, foot, config=cfg)
    n_levels = len(cfg.heights_m)
    acc = np.zeros(foot.shape, np.float32)
    deep = np.zeros(foot.shape, np.float32)
    counts: list[int] = []
    thresholds: list[float] = []
    for level, height in enumerate(cfg.heights_m):
        edges, thr = _edge_maxima(spectrum, radial_k, safe, original_shape=foot.shape, config=cfg, height_m=height)
        counts.append(int(edges.sum()))
        thresholds.append(float(thr))
        if edges.any():
            d = distance_transform_edt(~edges)
            near = (d <= float(tol_px)) & safe
            del d
            acc[near] += 1.0
            if level >= DEEP_FIRST_LEVEL:
                deep[near] += 1.0
            del near, edges
        else:
            del edges
        del thr
    persist = np.zeros(foot.shape, np.float32)
    persist[safe] = acc[safe] / float(n_levels)
    pdeep = np.zeros(foot.shape, np.float32)
    n_deep = n_levels - DEEP_FIRST_LEVEL
    pdeep[safe] = deep[safe] / float(n_deep)
    del acc, deep
    diag2 = dict(diag)
    diag2.update(
        edge_counts=counts,
        thresholds=thresholds,
        tolerance_px=float(tol_px),
        persistence_mean_inside_safe=float(persist[safe].mean()) if safe.any() else 0.0,
    )
    return persist, pdeep, diag2


def build_dense_persistence(band_dir: Path, footprint: np.ndarray, footprint_idx: np.ndarray,
                            *, config: WormConfig | None = None, tol_px: float = 2.0,
                            smooth_sigma_px: float = 1.0) -> tuple[np.ndarray, dict[str, Any]]:
    """Return ``(fields, diagnostics)``; ``fields`` is ``(4, n_footprint)`` float32 with rows ``HP_NAMES``.

    ``band_dir`` is the prepared ``work/bands`` directory (``02_rtp.npy`` and ``13_iso_grav_anom.npy``).
    The grids are Gaussian-smoothed by ``smooth_sigma_px`` and re-clipped to [0, 1]; values are zero
    outside the footprint.
    """
    cfg = config or WormConfig()
    cfg.validate()
    if not np.isfinite(tol_px) or tol_px < 0:
        raise ValueError("tol_px must be finite and non-negative")
    if smooth_sigma_px < 0:
        raise ValueError("smooth_sigma_px must be non-negative")
    foot = np.asarray(footprint, bool)
    fi = np.asarray(footprint_idx).astype(np.int64, copy=False)
    mag = np.load(Path(band_dir) / "02_rtp.npy")
    grav = np.load(Path(band_dir) / "13_iso_grav_anom.npy")

    pmag, pdeep_mag, d_mag = _persistence_grid(mag, foot, cfg, tol_px)
    pgrav, _, d_grav = _persistence_grid(grav, foot, cfg, tol_px)
    del mag, grav

    if smooth_sigma_px > 0:
        pmag = gaussian_filter(pmag, smooth_sigma_px, mode="constant")
        pgrav = gaussian_filter(pgrav, smooth_sigma_px, mode="constant")
        pdeep_mag = gaussian_filter(pdeep_mag, smooth_sigma_px, mode="constant")
    pmag = np.clip(pmag, 0.0, 1.0)
    pgrav = np.clip(pgrav, 0.0, 1.0)
    pdeep_mag = np.clip(pdeep_mag, 0.0, 1.0)
    pmin = np.minimum(pmag, pgrav)

    out = np.zeros((4, fi.size), np.float32)
    out[0] = pmag.ravel()[fi]
    out[1] = pgrav.ravel()[fi]
    out[2] = pmin.ravel()[fi]
    out[3] = pdeep_mag.ravel()[fi]
    out[~np.isfinite(out)] = 0.0
    diag = dict(
        heights_m=list(cfg.heights_m),
        edge_percentile=float(cfg.edge_percentile),
        boundary_guard_px=int(cfg.boundary_guard_px),
        tolerance_px=float(tol_px),
        smooth_sigma_px=float(smooth_sigma_px),
        deep_first_height_m=int(cfg.heights_m[DEEP_FIRST_LEVEL]),
        magnetic=d_mag,
        gravity=d_grav,
        nonzero_fraction={
            "HP_MAG": float(np.mean(out[0] > 0)),
            "HP_GRAV": float(np.mean(out[1] > 0)),
            "HP_MIN": float(np.mean(out[2] > 0)),
            "HP_DEEP": float(np.mean(out[3] > 0)),
        },
        mean={
            "HP_MAG": float(out[0].mean()), "HP_GRAV": float(out[1].mean()),
            "HP_MIN": float(out[2].mean()), "HP_DEEP": float(out[3].mean()),
        },
        max={
            "HP_MAG": float(out[0].max()), "HP_GRAV": float(out[1].max()),
            "HP_MIN": float(out[2].max()), "HP_DEEP": float(out[3].max()),
        },
    )
    return out, diag

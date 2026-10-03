"""H52 worming in its *filter* role: survival-with-height as an artifact-reliability number.

The standing owner brief asks for Hornby, Boschetti & Horowitz (1999) multiscale "worming" across the
magnetic and gravity layers with **persistence-with-height as an explicit feature or filter**, and for
the acquisition-artifact audit to be given "a number instead of a hunch": a candidate that exists only
at zero upward continuation is shallow and must be distrusted.

Four earlier formulations of this physics were screened here and all failed their frozen gates
(``knowledge/34`` §4). Reading their level detector against the physics shows why, and the measurement
is reproducible in ``tests/test_wormfilter.py``:

* ``worms._edge_maxima`` marks an edge where the horizontal-gradient modulus is an *isotropic 3x3 local
  maximum*. On a straight contact that keeps a handful of isolated **points** (a 64-px synthetic contact
  yields 37 level-0 pixels), so the earlier screens measured the persistence of points, not of lines -
  the documented cause of H31's sparsity failure.
* The per-level threshold is a **percentile of that level's own** gradient modulus. Upward continuation
  is a low-pass filter (attenuation ``exp(-k h)``), so it shrinks every amplitude by the same relative
  rule and a percentile cut always keeps ~10 % of the pixels: **nothing ever vanishes**. On a synthetic
  400 m-wavelength ripple - unambiguously shallow - the level-0 ridge count is 3,362 and the geometric
  persistence is 0.80, because the ridge positions are set by the wavelength and do not move while the
  amplitude collapses. A geometry-only persistence therefore calls quasi-periodic shallow noise (flight
  lineation, cultural lineaments) "deep", which is exactly the H29 observation that survey-line-parallel
  edges were the most persistent on this grid.

This module fixes both and measures what the brief actually describes:

1. **across-strike ridge levels** (a worm is a line), quantized to 45 degrees exactly as
   ``thinning.ridge_nms`` does, with a contrast floor so a quiet field cannot mark round-off as an edge;
2. **survival with height** - at each continuation height, an edge *survives* where the continued
   gradient modulus retains at least ``rho_retention`` of its own level-0 modulus in the local
   neighbourhood. Deep equivalent sources keep their gradient through the ladder; shallow ones decay as
   ``exp(-k h)`` and drop out. This is the explicit number behind "exists only at zero continuation".

Columns (frozen order, all float32 in [0, 1], footprint-vector order):

* ``WF_SURV_MAG``   - magnetic survival: fraction of continuation heights (h > 0) that retain the edge.
* ``WF_SURV_GRAV``  - the same for the isostatic residual gravity field.
* ``WF_SURV_JOINT`` - ``min`` of the two: the edge must survive in **both** independent fields.
* ``WF_SURV_DEEP``  - magnetic survival restricted to heights >= 400 m ("genuinely deep" contrast).
* ``WF_P_JOINT``    - geometric persistence (fraction of levels with a ridge within ``tol_px``), kept
  because it is the statistic the earlier screens used and the two are not interchangeable.
* ``WF_CONV``       - normalized convergence size: level-0 ridge pixels collapsing into one deep edge.
* ``WF_AZ_AGREE``   - ``(1 + cos 2(theta_mag - theta_grav)) / 2`` from level-0 structure tensors;
  1 = parallel edges, 0 = perpendicular, 0.5 = 45 degrees or undefined (see ``WF_AZ_DEFINED``).
* ``WF_SHALLOW_ONLY`` - 1 where a level-0 edge exists in either field but ``WF_SURV_JOINT < tau_survival``.

``WF_AZ_DEFINED`` (grid only, not a model column) marks where the azimuth comparison is meaningful.

References (``registry/sources.json``): Hornby, Boschetti & Horowitz (1999)
https://doi.org/10.1046/j.1365-246X.1999.00788.x; Horowitz (2018)
https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf. Upward continuation is not a
generic Gaussian scale-space and does not give a unique depth; survival is a reliability proxy only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import fft
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter
from scipy.spatial import cKDTree

from .worms import WormConfig, _prepare_spectrum

WF_NAMES = [
    "WF_SURV_MAG",
    "WF_SURV_GRAV",
    "WF_SURV_JOINT",
    "WF_SURV_DEEP",
    "WF_P_JOINT",
    "WF_CONV",
    "WF_AZ_AGREE",
    "WF_SHALLOW_ONLY",
]
DEEP_FIRST_LEVEL = 3  # heights_m[3] = 400 m in the frozen ladder (0, 100, 200, 400, 800, 1200)
_RIDGE_OFFSETS = {0: (0, 1), 1: (1, 1), 2: (1, 0), 3: (1, -1)}


@dataclass(frozen=True)
class WormFilterConfig:
    """Frozen filter parameters. Every value is declared before any fit (see the stage preregistration)."""

    tol_px: float = 2.0
    smooth_sigma_px: float = 1.0
    rho_retention: float = 0.25  # an edge survives a height if it keeps >= 25 % of its level-0 modulus
    tau_survival: float = 0.5  # below this share of heights surviving, the edge is called shallow
    tau_azimuth: float = 0.5  # agreement below 0.5 <=> the two fields' edges cross at more than 45 degrees
    coherence_min: float = 0.2  # structure-tensor coherence floor for a defined azimuth
    convergence_radius_px: float = 6.0  # basin-of-attraction radius (600 m) around a deep edge
    azimuth_sigma_px: float = 1.5  # structure-tensor smoothing scale
    min_contrast_fraction: float = 1e-3  # ridge floor as a fraction of the level's own max HGM

    def validate(self) -> None:
        for name, value in (("tol_px", self.tol_px), ("convergence_radius_px", self.convergence_radius_px),
                            ("azimuth_sigma_px", self.azimuth_sigma_px), ("smooth_sigma_px", self.smooth_sigma_px)):
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.tol_px <= 0 or self.convergence_radius_px <= 0 or self.azimuth_sigma_px <= 0:
            raise ValueError("tol_px, convergence_radius_px and azimuth_sigma_px must be positive")
        for name, value in (("rho_retention", self.rho_retention), ("tau_survival", self.tau_survival),
                            ("tau_azimuth", self.tau_azimuth), ("coherence_min", self.coherence_min),
                            ("min_contrast_fraction", self.min_contrast_fraction)):
            if not np.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1]")
        if self.rho_retention <= 0:
            raise ValueError("rho_retention must be positive: a zero retention threshold never drops an edge")


def _continued_modulus(spectrum: np.ndarray, radial_k: np.ndarray, *, original_shape: tuple[int, int],
                       cell_size_m: float, pad_px: int, height_m: int) -> tuple[np.ndarray, np.ndarray]:
    """Horizontal-gradient modulus and its across-strike direction (45-degree bins) at ``height_m``.

    The direction is the *field* gradient direction, which is perpendicular to the edge; comparing the
    modulus along it is an across-strike non-maximum suppression, the same convention as
    ``thinning.ridge_nms``.
    """
    transfer = np.exp(-np.float32(height_m) * radial_k).astype(np.float32, copy=False)
    continued_spectrum = spectrum * transfer
    del transfer
    padded_shape = (original_shape[0] + 2 * pad_px, original_shape[1] + 2 * pad_px)
    continued = fft.irfft2(continued_spectrum, s=padded_shape, workers=1).astype(np.float32, copy=False)
    del continued_spectrum
    crop = continued[pad_px : pad_px + original_shape[0], pad_px : pad_px + original_shape[1]]
    gy, gx = np.gradient(crop, cell_size_m, cell_size_m)
    modulus = np.hypot(gx, gy).astype(np.float32, copy=False)
    ang = np.mod(np.degrees(np.arctan2(gy, gx)), 180.0)
    direction = (np.round(ang / 45.0).astype(np.int8)) % 4
    del continued, crop, gy, gx, ang
    return modulus, direction


def _across_strike_ridge(modulus: np.ndarray, safe: np.ndarray, threshold: float, q: np.ndarray) -> np.ndarray:
    """Pixels that maximize the gradient modulus across strike (a line, not a point)."""
    if not np.isfinite(threshold):
        return np.zeros(safe.shape, bool)
    pad = np.pad(modulus, 1, mode="edge")
    h, w = modulus.shape
    keep = np.zeros((h, w), bool)
    for k, (dy, dx) in _RIDGE_OFFSETS.items():
        a = pad[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        b = pad[1 - dy : 1 - dy + h, 1 - dx : 1 - dx + w]
        # Strict on at least one side (the ``thinning.ridge_nms`` convention) so a constant plateau is
        # never read as a ridge.
        keep |= (q == k) & (modulus >= a) & (modulus >= b) & ((modulus > a) | (modulus > b))
    del pad
    return keep & safe & (modulus >= threshold)


def _field_ladder(values: np.ndarray, foot: np.ndarray, cfg: WormConfig, tol_px: float,
                  *, rho: float, min_contrast_fraction: float) -> dict[str, Any]:
    """Per-field continuation ladder: ridge sets, geometric persistence and amplitude survival."""
    spectrum, radial_k, safe, _, diag = _prepare_spectrum(values, foot, config=cfg)
    n_levels = len(cfg.heights_m)
    shape = foot.shape

    m0, q0 = _continued_modulus(spectrum, radial_k, original_shape=shape, cell_size_m=cfg.cell_size_m,
                                pad_px=cfg.pad_px, height_m=0)
    safe_m0 = m0[safe]
    threshold0 = float(np.percentile(safe_m0, cfg.edge_percentile))
    grad_max0 = float(safe_m0.max())
    if min_contrast_fraction > 0:
        # In a nearly constant field the percentile cut is float round-off; a fixed fraction of the
        # level's own maximum keeps the frozen percentile rule on real data and stays inert there.
        threshold0 = max(threshold0, float(min_contrast_fraction) * grad_max0)
    width = int(2 * int(np.ceil(tol_px)) + 1)
    m0_local = maximum_filter(m0, size=width, mode="nearest")  # reference amplitude for the survival test
    del safe_m0

    acc = np.zeros(shape, np.float32)
    survived = np.zeros(shape, np.float32)
    survived_deep = np.zeros(shape, np.float32)
    deep_edges = np.zeros(shape, bool)
    level0_edges = _across_strike_ridge(m0, safe, threshold0, q0)
    near0 = (distance_transform_edt(~level0_edges) <= float(tol_px)) & safe if level0_edges.any() \
        else np.zeros(shape, bool)
    counts = [int(level0_edges.sum())]
    thresholds = [threshold0]
    for level, height in enumerate(cfg.heights_m):
        if level == 0:
            if level0_edges.any():
                acc[near0] += 1.0
            continue
        mh, qh = _continued_modulus(spectrum, radial_k, original_shape=shape, cell_size_m=cfg.cell_size_m,
                                    pad_px=cfg.pad_px, height_m=int(height))
        safe_mh = mh[safe]
        thr_h = float(np.percentile(safe_mh, cfg.edge_percentile))
        grad_max_h = float(safe_mh.max())
        if min_contrast_fraction > 0:
            thr_h = max(thr_h, float(min_contrast_fraction) * grad_max_h)
        edges = _across_strike_ridge(mh, safe, thr_h, qh)
        counts.append(int(edges.sum()))
        thresholds.append(thr_h)
        del safe_mh
        # Geometric persistence: a ridge of this level lies within tol_px.
        if edges.any():
            near = (distance_transform_edt(~edges) <= float(tol_px)) & safe
            acc[near] += 1.0
            if level >= DEEP_FIRST_LEVEL:
                deep_edges |= edges
            del near
        # Amplitude survival: the continued modulus still holds rho of its own level-0 modulus.
        live = safe & (mh >= np.float32(rho) * m0_local) & (m0_local > 0)
        survived[live] += 1.0
        if level >= DEEP_FIRST_LEVEL:
            survived_deep[live] += 1.0
        del mh, qh, edges, live
    n_up = max(n_levels - 1, 1)
    n_deep = n_levels - DEEP_FIRST_LEVEL
    surv = np.zeros(shape, np.float32)
    surv[safe] = survived[safe] / float(n_up)
    surv_deep = np.zeros(shape, np.float32)
    surv_deep[safe] = survived_deep[safe] / float(n_deep)
    persist = np.zeros(shape, np.float32)
    persist[safe] = acc[safe] / float(n_levels)
    out = dict(
        survival=surv, survival_deep=surv_deep, persist=persist, safe=safe,
        near_level0=near0, level0_edges=level0_edges, deep_edges=deep_edges,
        diag=dict(diag, edge_counts=counts, thresholds=thresholds, tolerance_px=float(tol_px),
                  level0_threshold=float(threshold0), rho_retention=float(rho)),
    )
    del acc, survived, survived_deep, m0, q0, m0_local
    return out


def _convergence_grid(level0_edges: np.ndarray, deep_edges: np.ndarray, safe: np.ndarray,
                      radius_px: float, tol_px: float) -> np.ndarray:
    """Normalized basin-of-attraction size: level-0 ridge pixels near each deep edge, spread over ``tol_px``."""
    out = np.zeros(deep_edges.shape, np.float32)
    idx0 = np.flatnonzero(level0_edges.ravel())
    idx_deep = np.flatnonzero(deep_edges.ravel())
    if idx0.size == 0 or idx_deep.size == 0:
        return out
    width = level0_edges.shape[1]
    y0, x0 = np.divmod(idx0, width)
    yd, xd = np.divmod(idx_deep, width)
    tree = cKDTree(np.column_stack([y0, x0]).astype(np.float64))
    counts = tree.query_ball_point(np.column_stack([yd, xd]).astype(np.float64), r=float(radius_px), workers=1)
    sizes = np.fromiter((len(c) for c in counts), dtype=np.float64, count=idx_deep.size)
    denom = float(np.percentile(sizes, 99.0)) if sizes.size else 0.0
    if not np.isfinite(denom) or denom <= 0:
        denom = max(float(sizes.max()), 1.0)
    values = (np.log1p(sizes) / np.log1p(denom)).astype(np.float32)
    spread = np.zeros(deep_edges.shape, np.float32)
    np.put(spread, idx_deep, values)  # flat-index assignment on a 2-D grid
    if tol_px > 0:
        d = distance_transform_edt(~deep_edges)
        near = (d <= float(tol_px)) & safe
        # A halo pixel inherits the largest basin touching it, so one extensive deep source is not
        # diluted by a neighbouring shallow swarm.
        spread = maximum_filter(spread, size=int(2 * int(np.ceil(tol_px)) + 1), mode="constant")
        out[near] = spread[near]
        del d, near
    else:
        out = spread
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _structure_orientation(values: np.ndarray, foot: np.ndarray, sigma_px: float) -> tuple[np.ndarray, np.ndarray]:
    """Level-0 structure-tensor azimuth (radians, mod pi) and coherence in [0, 1]."""
    v = np.asarray(values, np.float32)
    work = np.where(foot, np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0), 0.0).astype(np.float32)
    smooth = gaussian_filter(work, sigma_px, mode="nearest")
    gy, gx = np.gradient(smooth)
    jxx = gaussian_filter(gx * gx, sigma_px, mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma_px, mode="nearest")
    jxy = gaussian_filter(gx * gy, sigma_px, mode="nearest")
    del smooth, gy, gx
    trace = jxx + jyy
    diff = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy)
    coherence = np.zeros(trace.shape, np.float32)
    ok = trace > np.finfo(np.float32).tiny
    coherence[ok] = (diff[ok] / trace[ok]).astype(np.float32)
    theta = (0.5 * np.arctan2(2.0 * jxy, jxx - jyy)).astype(np.float32)
    return theta, np.clip(coherence, 0.0, 1.0).astype(np.float32)


def build_worm_fields(
    band_dir: Path,
    footprint: np.ndarray,
    footprint_idx: np.ndarray,
    *,
    ladder: WormConfig | None = None,
    config: WormFilterConfig | None = None,
    mag_band: str = "02_rtp.npy",
    grav_band: str = "13_iso_grav_anom.npy",
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, Any]]:
    """Return ``(vectors, grids, diagnostics)``.

    ``vectors`` is ``(len(WF_NAMES), n_footprint)`` float32; ``grids`` holds the same fields on the full
    raster grid (plus ``WF_AZ_DEFINED``) so an emission step can crop them to a cell bounding box.
    No label, catalogue or holdout information is read anywhere in this function.
    """
    cfg = config or WormFilterConfig()
    cfg.validate()
    ladder = ladder or WormConfig()
    ladder.validate()
    foot = np.asarray(footprint, bool)
    fi = np.asarray(footprint_idx).astype(np.int64, copy=False)
    if fi.ndim != 1 or (fi.size and (np.diff(fi) <= 0).any()):
        raise ValueError("footprint_idx must be strictly increasing and unique")
    if fi.size and ((fi < 0).any() or (fi >= foot.size).any() or not foot.ravel()[fi].all()):
        raise ValueError("footprint_idx must contain only in-footprint flat indices")

    mag = np.load(Path(band_dir) / mag_band)
    grav = np.load(Path(band_dir) / grav_band)
    if mag.shape != foot.shape or grav.shape != foot.shape:
        raise ValueError("magnetic and gravity bands must align with the footprint grid")

    m = _field_ladder(mag, foot, ladder, cfg.tol_px, rho=cfg.rho_retention,
                      min_contrast_fraction=cfg.min_contrast_fraction)
    g = _field_ladder(grav, foot, ladder, cfg.tol_px, rho=cfg.rho_retention,
                      min_contrast_fraction=cfg.min_contrast_fraction)

    surv_joint = np.minimum(m["survival"], g["survival"])
    persist_joint = np.minimum(m["persist"], g["persist"])
    if cfg.smooth_sigma_px > 0:
        surv_mag = gaussian_filter(m["survival"], cfg.smooth_sigma_px, mode="constant")
        surv_grav = gaussian_filter(g["survival"], cfg.smooth_sigma_px, mode="constant")
        surv_joint = gaussian_filter(surv_joint, cfg.smooth_sigma_px, mode="constant")
        surv_deep = gaussian_filter(m["survival_deep"], cfg.smooth_sigma_px, mode="constant")
        persist_joint = gaussian_filter(persist_joint, cfg.smooth_sigma_px, mode="constant")
    else:
        surv_mag, surv_grav, surv_deep = m["survival"], g["survival"], m["survival_deep"]
    surv_mag = np.clip(surv_mag, 0.0, 1.0).astype(np.float32)
    surv_grav = np.clip(surv_grav, 0.0, 1.0).astype(np.float32)
    surv_joint = np.clip(surv_joint, 0.0, 1.0).astype(np.float32)
    surv_deep = np.clip(surv_deep, 0.0, 1.0).astype(np.float32)
    persist_joint = np.clip(persist_joint, 0.0, 1.0).astype(np.float32)

    near0 = m["near_level0"] | g["near_level0"]
    shallow = (near0 & (surv_joint < np.float32(cfg.tau_survival))).astype(np.float32)

    conv = np.maximum(
        _convergence_grid(m["level0_edges"], m["deep_edges"], m["safe"], cfg.convergence_radius_px, cfg.tol_px),
        _convergence_grid(g["level0_edges"], g["deep_edges"], g["safe"], cfg.convergence_radius_px, cfg.tol_px),
    )

    theta_m, coh_m = _structure_orientation(mag, foot, cfg.azimuth_sigma_px)
    theta_g, coh_g = _structure_orientation(grav, foot, cfg.azimuth_sigma_px)
    # Signed cos 2(dtheta) is the correct agreement statistic for directions defined mod 180 degrees:
    # +1 when the two edges are parallel, -1 when they are perpendicular. The absolute value would
    # identify those two cases; it is mapped to [0, 1] instead, with 0.5 at 45 degrees.
    cos2d = np.cos(2.0 * (theta_m.astype(np.float64) - theta_g.astype(np.float64)))
    az = (0.5 * (1.0 + cos2d)).astype(np.float32)
    defined = (coh_m >= cfg.coherence_min) & (coh_g >= cfg.coherence_min) & near0 & m["safe"] & g["safe"]
    # Neutral (0.5) where the comparison is not defined, so the model column cannot read "undefined" as
    # "perpendicular". The emission filter uses WF_AZ_DEFINED explicitly instead of this value.
    az_grid = np.where(defined, az, np.float32(0.5)).astype(np.float32)
    del mag, grav, theta_m, theta_g

    grids: dict[str, np.ndarray] = {
        "WF_SURV_MAG": surv_mag,
        "WF_SURV_GRAV": surv_grav,
        "WF_SURV_JOINT": surv_joint,
        "WF_SURV_DEEP": surv_deep,
        "WF_P_JOINT": persist_joint,
        "WF_CONV": conv,
        "WF_AZ_AGREE": az_grid,
        "WF_SHALLOW_ONLY": shallow,
        "WF_AZ_DEFINED": defined.astype(np.float32),
    }
    vectors = np.zeros((len(WF_NAMES), fi.size), np.float32)
    for row, name in enumerate(WF_NAMES):
        vectors[row] = grids[name].ravel()[fi]
        vectors[row][~np.isfinite(vectors[row])] = 0.0

    diag: dict[str, Any] = dict(
        heights_m=list(ladder.heights_m),
        edge_percentile=float(ladder.edge_percentile),
        boundary_guard_px=int(ladder.boundary_guard_px),
        tol_px=float(cfg.tol_px),
        smooth_sigma_px=float(cfg.smooth_sigma_px),
        rho_retention=float(cfg.rho_retention),
        tau_survival=float(cfg.tau_survival),
        tau_azimuth=float(cfg.tau_azimuth),
        coherence_min=float(cfg.coherence_min),
        convergence_radius_px=float(cfg.convergence_radius_px),
        azimuth_sigma_px=float(cfg.azimuth_sigma_px),
        min_contrast_fraction=float(cfg.min_contrast_fraction),
        deep_first_height_m=int(ladder.heights_m[DEEP_FIRST_LEVEL]),
        level_detector="across-strike gradient-modulus ridge (45-degree quantized), not an isotropic point maximum",
        survival_rule="continued modulus >= rho_retention x local level-0 modulus",
        magnetic=m["diag"],
        gravity=g["diag"],
        safe_pixels=int(m["safe"].sum()),
        azimuth_defined_pixels=int(defined.sum()),
        mean={n: float(grids[n].ravel()[fi].mean()) for n in grids},
        max={n: float(grids[n].ravel()[fi].max()) for n in grids},
        nonzero_fraction={n: float(np.mean(grids[n].ravel()[fi] > 0)) for n in grids},
    )
    return vectors, grids, diag


# -------------------------------------------------------------------------------------------
# Emission-time filters. These never see a score's provenance; they only read the worm fields.
# -------------------------------------------------------------------------------------------
def shallow_veto(candidates: np.ndarray, shallow_grid: np.ndarray) -> np.ndarray:
    """Boolean mask of candidates that exist only at zero continuation (to be removed)."""
    candidates = np.asarray(candidates, bool)
    shallow = np.asarray(shallow_grid)
    if candidates.shape != shallow.shape:
        raise ValueError("candidates and the shallow-only grid must be aligned crops")
    return candidates & (np.nan_to_num(shallow, nan=0.0) > 0.5)


def azimuth_veto(candidates: np.ndarray, az_grid: np.ndarray, defined_grid: np.ndarray,
                 tau_azimuth: float) -> np.ndarray:
    """Boolean mask of candidates whose magnetic/gravity edge azimuths disagree where that is defined.

    Mirrors the H29 A1 convention: a candidate is removed only where the statistic is *defined*;
    where the two fields give no coherent orientation the candidate is left untouched.
    """
    candidates = np.asarray(candidates, bool)
    az = np.asarray(az_grid)
    defined = np.asarray(defined_grid)
    if candidates.shape != az.shape or candidates.shape != defined.shape:
        raise ValueError("candidates, azimuth and defined grids must be aligned crops")
    if not np.isfinite(tau_azimuth) or not 0.0 <= tau_azimuth <= 1.0:
        raise ValueError("tau_azimuth must lie in [0, 1]")
    return candidates & (np.nan_to_num(defined, nan=0.0) > 0.5) & (np.nan_to_num(az, nan=1.0) < tau_azimuth)


def veto_rate(emitted: np.ndarray, veto: np.ndarray) -> float:
    """Share of an emission removed by a veto (0 when nothing was emitted)."""
    n = int(np.asarray(emitted, bool).sum())
    if n == 0:
        return 0.0
    return float(np.asarray(veto, bool).sum()) / float(n)

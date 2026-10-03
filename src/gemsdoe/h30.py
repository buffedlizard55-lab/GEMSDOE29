"""H30-1 paired fault-tip bridge and terrain-support features.

Paired geometry is built from the per-cell *visible* catalogue only. It is deliberately separate from H27's
single-tip directed continuation. The small helpers here also provide the frozen 2x2 factorial contrasts and
promotion gate used by the H30 runner/analyzer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy.ndimage import convolve, gaussian_filter, label, maximum_filter
from scipy.spatial import cKDTree

H30_PAIR_NAMES = ["H30_pair_bridge", "H30_scarp_persistence"]
H30_BASE_EXTRAS = ["X1_K", "X1_ThK", "X1_UK", "X2_compat", "X2_compat_coh", "X3_gm", "X3_gd"]
H30_ARMS = {
    "T_BASE": (0, 0),
    "T_PLUS_P": (1, 0),
    "T_PLUS_S": (0, 1),
    "T_PLUS_P_S": (1, 1),
}
H30_CONTROL = "BASE_NO_TIP"
H30_HISTORICAL_TIP_SCREEN_DTI = 0.15288182411967066
H30_HISTORICAL_H28_COMPARATOR_DTI = 0.15200338908786984


def _coarse_density(mask: np.ndarray, sigma_px: float, factor: int = 4) -> np.ndarray:
    """Match family E's block-average then Gaussian interpolation without holding extra full grids."""
    h, w = mask.shape
    hc, wc = h // factor, w // factor
    coarse = np.asarray(mask[: hc * factor, : wc * factor], np.float32).reshape(
        hc, factor, wc, factor
    ).mean(axis=(1, 3))
    coarse = gaussian_filter(coarse, sigma_px / factor)
    # scipy.ndimage.zoom can return one pixel short when dimensions are not divisible by factor.
    from scipy.ndimage import zoom

    up = zoom(coarse, factor, order=1)
    out = np.zeros((h, w), np.float32)
    out[: min(h, up.shape[0]), : min(w, up.shape[1])] = up[:h, :w]
    return out


def build_paired_tip_bridge(
    visible: np.ndarray,
    footprint: np.ndarray,
    footprint_idx: np.ndarray,
    *,
    min_distance_px: float = 2.0,
    max_distance_px: float = 15.0,
    min_coherence: float = 0.25,
    min_strike_cos2: float = 0.5,
    min_cross_strike: float = 0.35,
    buffer_px: int = 2,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return a [0,1] paired-tip bridge field as a footprint vector, plus diagnostics.

    Candidate pairs join distinct 8-connected components. Their separation must be short, approximately
    subparallel, and cross-strike rather than a simple collinear single-tip extension. Segments are rasterized at
    no more than 0.5 px spacing, weighted, then expanded by a 2-px disk via a local maximum. All geometry is
    computed from ``visible``; no hidden labels or full-catalogue geometry is accepted by this function.
    """
    vis = np.asarray(visible, dtype=bool)
    foot = np.asarray(footprint, dtype=bool)
    raw_idx = np.asarray(footprint_idx)
    if vis.ndim != 2 or foot.ndim != 2 or vis.shape != foot.shape:
        raise ValueError("visible and footprint must be aligned 2-D arrays")
    if raw_idx.ndim != 1 or (raw_idx.size and not np.issubdtype(raw_idx.dtype, np.integer)):
        raise ValueError("footprint_idx must be a 1-D integer array")
    fi = raw_idx.astype(np.int64, copy=False)
    h, w = foot.shape
    if fi.size and ((fi < 0).any() or (fi >= h * w).any() or not foot.ravel()[fi].all()):
        raise ValueError("footprint_idx must contain only valid flat indices inside the footprint")
    if (not np.isfinite(min_distance_px) or not np.isfinite(max_distance_px)
            or min_distance_px <= 0 or max_distance_px <= min_distance_px):
        raise ValueError("tip-pair distances must be finite, positive, and increasing")
    if not 0.0 <= min_coherence <= 1.0 or not -1.0 <= min_strike_cos2 < 1.0:
        raise ValueError("coherence and doubled-angle thresholds are out of range")
    if not 0.0 <= min_cross_strike <= 1.0:
        raise ValueError("cross-strike threshold must be in [0,1]")
    if isinstance(buffer_px, (bool, np.bool_)) or not isinstance(buffer_px, (int, np.integer)) or buffer_px < 0:
        raise ValueError("buffer_px must be a nonnegative integer")

    v = vis & foot
    result = np.zeros(fi.size, np.float32)
    empty_diag = {
        "visible_tip_count": 0,
        "nearby_pair_count": 0,
        "accepted_pair_count": 0,
        "seed_pixel_count": 0,
        "nonzero_fraction": 0.0,
        "max_value": 0.0,
    }
    if not v.any() or not fi.size:
        return result, empty_diag

    full_3x3 = np.zeros_like(foot)
    full_3x3[1:-1, 1:-1] = (
        foot[:-2, :-2] & foot[:-2, 1:-1] & foot[:-2, 2:]
        & foot[1:-1, :-2] & foot[1:-1, 1:-1] & foot[1:-1, 2:]
        & foot[2:, :-2] & foot[2:, 1:-1] & foot[2:, 2:]
    )
    kernel = np.ones((3, 3), np.uint8)
    kernel[1, 1] = 0
    degree = convolve(v.astype(np.uint8), kernel, mode="constant", cval=0)
    tip_r, tip_c = np.nonzero(v & (degree == 1) & full_3x3)
    n_tips = int(tip_r.size)
    if n_tips < 2:
        empty_diag["visible_tip_count"] = n_tips
        return result, empty_diag

    # Same doubled-angle structure-tensor convention as family E / H27.
    smooth = gaussian_filter(v.astype(np.float32), 2.0)
    gy, gx = np.gradient(smooth)
    jxx = gaussian_filter(gx * gx, 2.0)
    jyy = gaussian_filter(gy * gy, 2.0)
    jxy = gaussian_filter(gx * gy, 2.0)
    phi2 = np.arctan2(2.0 * jxy, jxx - jyy)
    line_c2 = -np.cos(phi2).astype(np.float32)
    line_s2 = -np.sin(phi2).astype(np.float32)
    vv = v.astype(np.float32)
    sc = _coarse_density(vv * line_c2, 20.0)
    ss = _coarse_density(vv * line_s2, 20.0)
    sw = _coarse_density(vv, 20.0)
    coherence = np.sqrt(sc * sc + ss * ss) / np.maximum(sw, 1e-6)
    coherence = np.where(sw > 1e-5, np.minimum(coherence, 1.0), 0.0).astype(np.float32)
    tip_c2 = line_c2[tip_r, tip_c]
    tip_s2 = line_s2[tip_r, tip_c]
    tip_coh = coherence[tip_r, tip_c]
    del smooth, gy, gx, jxx, jyy, jxy, phi2, line_c2, line_s2, vv, sc, ss, sw, coherence, degree, full_3x3

    components, _ = label(v, structure=np.ones((3, 3), np.uint8))
    tip_component = components[tip_r, tip_c]
    coords = np.column_stack((tip_r, tip_c)).astype(np.float64, copy=False)
    pairs = cKDTree(coords).query_pairs(max_distance_px, output_type="ndarray")
    if pairs.size == 0:
        empty_diag["visible_tip_count"] = n_tips
        return result, empty_diag
    pairs = pairs[np.lexsort((pairs[:, 1], pairs[:, 0]))]
    i, j = pairs[:, 0], pairs[:, 1]
    dr = tip_r[j].astype(np.float32) - tip_r[i].astype(np.float32)
    dc = tip_c[j].astype(np.float32) - tip_c[i].astype(np.float32)
    dist = np.hypot(dr, dc)
    strike_cos2 = tip_c2[i] * tip_c2[j] + tip_s2[i] * tip_s2[j]
    mean_c2 = tip_c2[i] + tip_c2[j]
    mean_s2 = tip_s2[i] + tip_s2[j]
    mean_theta = 0.5 * np.arctan2(mean_s2, mean_c2)
    tx, ty = np.cos(mean_theta), np.sin(mean_theta)
    parallel_fraction = np.abs((dc / np.maximum(dist, 1e-12)) * tx + (dr / np.maximum(dist, 1e-12)) * ty)
    cross_strike = np.sqrt(np.maximum(0.0, 1.0 - parallel_fraction * parallel_fraction))
    pair_coherence = np.sqrt(np.maximum(0.0, tip_coh[i] * tip_coh[j]))
    valid = (
        (tip_component[i] != tip_component[j])
        & (dist >= min_distance_px)
        & (dist <= max_distance_px)
        & (tip_coh[i] >= min_coherence)
        & (tip_coh[j] >= min_coherence)
        & (strike_cos2 >= min_strike_cos2)
        & (cross_strike >= min_cross_strike)
    )
    accepted = pairs[valid]
    if not accepted.size:
        return result, {
            "visible_tip_count": n_tips,
            "nearby_pair_count": int(pairs.shape[0]),
            "accepted_pair_count": 0,
            "seed_pixel_count": 0,
            "nonzero_fraction": 0.0,
            "max_value": 0.0,
        }

    ii, jj = i[valid], j[valid]
    compatibility = np.clip((strike_cos2[valid] - min_strike_cos2) / (1.0 - min_strike_cos2), 0.0, 1.0)
    weights = (
        np.exp(-dist[valid] / 8.0)
        * compatibility
        * pair_coherence[valid]
        * cross_strike[valid]
    ).astype(np.float32)

    seed = np.zeros((h, w), np.float32)
    flat_indices: list[np.ndarray] = []
    flat_values: list[np.ndarray] = []
    for a, b, weight in zip(ii.tolist(), jj.tolist(), weights.tolist(), strict=True):
        r0, c0 = int(tip_r[a]), int(tip_c[a])
        r1, c1 = int(tip_r[b]), int(tip_c[b])
        length = float(np.hypot(r1 - r0, c1 - c0))
        n_step = max(1, int(np.ceil(length * 2.0)))
        t = np.linspace(0.0, 1.0, n_step + 1, dtype=np.float32)
        rr = np.rint(r0 + t * (r1 - r0)).astype(np.int32)
        cc = np.rint(c0 + t * (c1 - c0)).astype(np.int32)
        in_bounds = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
        rr, cc = rr[in_bounds], cc[in_bounds]
        inside = foot[rr, cc]
        if inside.any():
            ids = rr[inside].astype(np.int64) * w + cc[inside].astype(np.int64)
            flat_indices.append(ids)
            flat_values.append(np.full(ids.size, weight, np.float32))
    if flat_indices:
        np.maximum.at(seed.ravel(), np.concatenate(flat_indices), np.concatenate(flat_values))
    seed_count = int(np.count_nonzero(seed))
    if buffer_px:
        yy, xx = np.mgrid[-buffer_px : buffer_px + 1, -buffer_px : buffer_px + 1]
        disk = (yy * yy + xx * xx) <= buffer_px * buffer_px
        field = maximum_filter(seed, footprint=disk, mode="constant", cval=0.0)
    else:
        field = seed
    field = np.clip(np.nan_to_num(field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    result[:] = field.ravel()[fi]
    diag = {
        "visible_tip_count": n_tips,
        "nearby_pair_count": int(pairs.shape[0]),
        "accepted_pair_count": int(accepted.shape[0]),
        "seed_pixel_count": seed_count,
        "nonzero_fraction": float(np.count_nonzero(result) / max(1, result.size)),
        "max_value": float(result.max(initial=0.0)),
    }
    return result, diag


def build_scarp_persistence(
    static: np.ndarray,
    names: Sequence[str],
    scales: Mapping[str, tuple[float, float]],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build H30's fixed LiDAR scarp-persistence composite and report source nodata counts."""
    required = ("L_step_max", "L_cross_max", "L_coh100")
    if np.asarray(static).ndim != 2 or np.asarray(static).shape[0] != len(names):
        raise ValueError("static must be a (feature, footprint-pixel) matrix aligned with names")
    name_to_i = {str(name): i for i, name in enumerate(names)}
    missing = [name for name in required if name not in name_to_i or name not in scales]
    if missing:
        raise ValueError(f"static cache lacks H30 scarp inputs/scales: {missing}")
    scaled: list[np.ndarray] = []
    nonfinite: dict[str, int] = {}
    n = np.asarray(static).shape[1]
    for name in required:
        lo, hi = map(float, scales[name])
        if not np.isfinite([lo, hi]).all() or hi <= lo:
            raise ValueError(f"invalid percentile scale for {name}: {(lo, hi)}")
        raw = np.asarray(static[name_to_i[name]], dtype=np.float32)
        finite = np.isfinite(raw)
        nonfinite[name] = int(raw.size - np.count_nonzero(finite))
        vals = np.zeros(raw.size, np.float32)
        vals[finite] = np.clip((raw[finite] - lo) / (hi - lo), 0.0, 1.0)
        scaled.append(vals)
    out = np.clip(scaled[0] * scaled[1] * scaled[2], 0.0, 1.0).astype(np.float32, copy=False)
    diag = {
        "source_nonfinite_counts": nonfinite,
        "n_footprint_pixels": int(n),
        "nonzero_fraction": float(np.count_nonzero(out) / max(1, out.size)),
        "max_value": float(out.max(initial=0.0)),
    }
    return out, diag


def factorial_2x2_effects(responses: Mapping[str, float]) -> dict[str, float]:
    """Return coded H30 P/S main effects and interaction (half the difference-in-differences)."""
    if set(responses) != set(H30_ARMS):
        raise ValueError(f"responses must have exactly these arms: {sorted(H30_ARMS)}")
    y00, y10, y01, y11 = (float(responses[k]) for k in ("T_BASE", "T_PLUS_P", "T_PLUS_S", "T_PLUS_P_S"))
    if not np.isfinite([y00, y10, y01, y11]).all():
        raise ValueError("all four 2x2 design responses must be finite")
    return {
        "P": (y10 + y11 - y00 - y01) / 2.0,
        "S": (y01 + y11 - y00 - y10) / 2.0,
        "P_x_S": (y00 - y10 - y01 + y11) / 2.0,
        "P_x_S_difference_in_differences": y00 - y10 - y01 + y11,
    }


def h30_promotion_gate(
    candidate_by_fold: Sequence[float],
    controls_by_fold: Mapping[str, Sequence[float]],
    candidate_hug_by_fold: Sequence[float],
    controls_hug_by_fold: Mapping[str, Sequence[float]],
    *,
    min_gain: float = 0.001,
    max_fold_loss: float = 0.01,
    max_hug_increase: float = 0.10,
) -> dict[str, Any]:
    """Compare P+S to the per-fold best same-run control; historical cross-draw numbers are context only."""
    candidate = np.asarray(candidate_by_fold, dtype=float)
    candidate_hug = np.asarray(candidate_hug_by_fold, dtype=float)
    if candidate.shape != (4,) or candidate_hug.shape != (4,) or not np.isfinite(candidate).all() or not np.isfinite(candidate_hug).all():
        raise ValueError("candidate DTI and hug arrays must contain four finite fold means")
    if set(controls_by_fold) != {H30_CONTROL, "T_BASE"} or set(controls_hug_by_fold) != set(controls_by_fold):
        raise ValueError("controls must be BASE_NO_TIP and T_BASE, with matching hug arrays")
    controls = {k: np.asarray(v, dtype=float) for k, v in controls_by_fold.items()}
    control_hug = {k: np.asarray(v, dtype=float) for k, v in controls_hug_by_fold.items()}
    if any(v.shape != (4,) or not np.isfinite(v).all() for v in controls.values()):
        raise ValueError("each control DTI array must contain four finite fold means")
    if any(v.shape != (4,) or not np.isfinite(v).all() for v in control_hug.values()):
        raise ValueError("each control hug array must contain four finite fold means")

    thresholds = np.asarray([min_gain, max_fold_loss, max_hug_increase], dtype=float)
    if not np.isfinite(thresholds).all() or min_gain < 0.0 or max_fold_loss < 0.0 or max_hug_increase < 0.0:
        raise ValueError("promotion-gate thresholds must be finite and nonnegative")
    if ((candidate < 0.0) | (candidate > 1.0)).any() or any(
        ((values < 0.0) | (values > 1.0)).any() for values in controls.values()
    ):
        raise ValueError("promotion-gate DTI values must be in [0,1]")
    if ((candidate_hug < 0.0) | (candidate_hug > 1.0)).any() or any(
        ((values < 0.0) | (values > 1.0)).any() for values in control_hug.values()
    ):
        raise ValueError("promotion-gate hug shares must be in [0,1]")

    names = (H30_CONTROL, "T_BASE")
    chosen = np.argmax(np.vstack([controls[n] for n in names]), axis=0)
    reference = np.array([controls[names[idx]][fold] for fold, idx in enumerate(chosen)])
    reference_hug = np.array([control_hug[names[idx]][fold] for fold, idx in enumerate(chosen)])
    delta = candidate - reference
    hug_delta = candidate_hug - reference_hug
    mean_gain = float(delta.mean())
    positive_folds = int(np.count_nonzero(delta > 0.0))
    worst_fold = float(delta.min())
    mean_hug_delta = float(hug_delta.mean())
    passed = bool(
        mean_gain > min_gain
        and positive_folds >= 3
        and worst_fold >= -max_fold_loss
        and mean_hug_delta <= max_hug_increase
    )
    return {
        "candidate_mean_dti": float(candidate.mean()),
        "reference_mean_dti": float(reference.mean()),
        "reference_arm_by_fold": [names[int(i)] for i in chosen],
        "mean_gain_vs_best_paired_control": mean_gain,
        "folds_positive": positive_folds,
        "worst_fold_gain": worst_fold,
        "mean_hug_share_delta": mean_hug_delta,
        "hug_share_delta_by_fold": [float(x) for x in hug_delta],
        "paired_gate_passed": passed,
        "per_fold_gain": [float(x) for x in delta],
    }

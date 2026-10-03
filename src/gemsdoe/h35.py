"""H35 structural-interaction-zone fields: relay-ramp pairing, junctions, tip-cluster density.

Pure-geometry add-on for the hide-and-recover screens. Every field is computed from the *visible*
catalogue only (never hidden labels), on the 100 m competition grid, and is returned as a footprint-vector
``float32`` array in ``[0, 1]``. Frozen in
``knowledge/19_preregistered_h35_h40_screen_2026-10-03.md``.

Objects:

* ``H35_RELAY``     - facing sub-parallel trace tips inside a relay window (step width 0.3-2.5 km,
  tip separation 0.4-3.0 km), geometric corridor score only (exponential decay along the bridge).
* ``H35_RELAY_TD``  - the same corridor score multiplied by the Andersonian **dilation tendency** of the
  bridge strike under regional normal-faulting stress. Extension (sigma-3h) azimuth from Bellier & Zoback
  1995 (doi:10.1029/94TC00596): Walker Lane mean normal-faulting sigma-3 axis N85 +/- 9 deg W (strike-line
  azimuth 95 deg mod 180) and young strike-slip regime N65-70 deg W (110-115 mod 180); the frozen
  constant is the midpoint 105 deg. A single regional azimuth across the footprint is a documented
  approximation; Siler 2022 (DOI 10.5066/P9YL58W6) reports normal-vs-strike-slip dilation tendency is
  nearly identical in this region, which bounds how much this weighting can add.
* ``H35_JUNCTION``  - smoothed density of catalogue pixels whose local trace orientation changes by more
  than ~45 deg within 3 px: transverse junctions, sharp bends, and facing tip pairs (an honest
  orientation-disturbance field: bends and tip convergences qualify by design and are recorded as such -
  near tips the structure tensor also rotates where two strands merge within the smoothing scale).
* ``H35_TIPDENS``   - Gaussian kernel density of degree-1 trace tips (clusters of short overlapping strands).

Angle conventions are pinned once, here: a "trace angle" ``t`` is measured from east toward south (the
raster row axis) in degrees mod 180, so a pixel step ``(dr, dc)`` has ``t = degrees(atan2(dr, dc)) % 180``
and unit strike vector ``(dr, dc) = (sin t, cos t)``. The geographic strike azimuth (clockwise from north)
is ``phi = t + 90 (mod 180)``. Structure-tensor strikes and bridge steps share these formulas exactly.

Boundary vs. predecessor work: ``H27_tip`` is single-tip directed continuation; ``H30-1`` is a cross-strike
paired-tip bridge x scarp product (failed fresh-draw confirmation). H35 differs by (i) the wider relay
window with an explicit offset step-width requirement, (ii) stress-favourability weighting, and (iii) the
junction and tip-cluster objects. It reuses no H30 code path.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import convolve, gaussian_filter, maximum_filter
from scipy.spatial import cKDTree

H35_NAMES = ["H35_RELAY", "H35_RELAY_TD", "H35_JUNCTION", "H35_TIPDENS"]

# Frozen physical constants for the dilation-tendency weight (sources in the module docstring).
SIGMA3_AZIMUTH_DEG = 105.0  # geographic strike azimuth (deg CW from north, mod 180) of the sigma_3h trend
DIP_DEG = 60.0              # steep normal-fault convention
STRESS_R2 = 0.85            # sigma_2h / sigma_v proxy (ordering 1 > r2 >= r3 for normal faulting)
STRESS_R3 = 0.60            # sigma_3h / sigma_v proxy
RELAY_PARAMS = dict(
    min_step_px=3.0, max_step_px=25.0,        # relay step width 0.3-2.5 km
    min_tip_gap_px=4.0, max_tip_gap_px=30.0,  # tip-to-tip separation 0.4-3.0 km
    max_strike_diff_deg=25.0,                 # sub-parallel strands
    facing_cos=0.5,                           # outward tip vectors point at each other within 60 deg
    decay_px=20.0,                            # corridor weight exp(-distance/decay)
    buffer_px=2.0,                            # 2-px disk spreading of the corridor
)


def dilation_tendency(phi_deg: np.ndarray, *,
                      sigma3_azimuth_deg: float = SIGMA3_AZIMUTH_DEG,
                      dip_deg: float = DIP_DEG,
                      r2: float = STRESS_R2, r3: float = STRESS_R3) -> np.ndarray:
    """Andersonian normal-faulting dilation tendency ``Td = (sigma_n - sigma_3)/(sigma_1 - sigma_3)``.

    ``phi_deg`` is the trace strike azimuth (deg clockwise from north, mod 180) and
    ``sigma3_azimuth_deg`` the sigma_3h trend azimuth in the same convention. With sigma_1 vertical,
    ``sigma_n = cos^2(dip) + sin^2(dip) * [r2*cos^2(phi - A3) + r3*sin^2(phi - A3)]``: a plane striking
    PARALLEL to the extension trend carries the full horizontal compression difference and opens most
    easily at a shallow dip; dip-direction ambiguity cancels through the doubled-angle form. Clipped to
    [0, 1].
    """
    th = np.deg2rad(np.asarray(phi_deg, dtype=np.float64))
    a3 = np.deg2rad(float(sigma3_azimuth_deg))
    dip = np.deg2rad(float(dip_deg))
    c2 = np.cos(th - a3) ** 2
    sigma_n = np.cos(dip) ** 2 + np.sin(dip) ** 2 * (r2 * c2 + r3 * (1.0 - c2))
    return np.clip((sigma_n - r3) / (1.0 - r3), 0.0, 1.0).astype(np.float32)


def find_trace_tips(visible: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, ...]:
    """Degree-1 pixels with full 3x3 footprint support plus their outward unit vectors (dr, dc)."""
    vis = np.asarray(visible, bool)
    foot = np.asarray(footprint, bool)
    if vis.ndim != 2 or vis.shape != foot.shape:
        raise ValueError("visible and footprint must be aligned 2-D grids")
    vis = vis & foot
    if not vis.any():
        e = np.zeros(0, np.int32)
        return e, e, e.astype(np.float32), e.astype(np.float32)
    ker = np.ones((3, 3), np.uint8)
    ker[1, 1] = 0
    degree = convolve(vis.astype(np.uint8), ker, mode="constant", cval=0)
    supp = np.zeros_like(foot)
    supp[1:-1, 1:-1] = (
        foot[:-2, :-2] & foot[:-2, 1:-1] & foot[:-2, 2:]
        & foot[1:-1, :-2] & foot[1:-1, 1:-1] & foot[1:-1, 2:]
        & foot[2:, :-2] & foot[2:, 1:-1] & foot[2:, 2:]
    )
    tip = vis & (degree == 1) & supp
    tr, tc = np.nonzero(tip)
    out_r = np.zeros(tr.size, np.float64)
    out_c = np.zeros(tr.size, np.float64)
    flat = tr.astype(np.int64) * vis.shape[1] + tc.astype(np.int64)
    vis_flat = vis.ravel()
    H, W = vis.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nr, nc = tr + dy, tc + dx
            ok = (nr >= 0) & (nr < H) & (nc >= 0) & (nc < W)
            has = np.zeros(tr.size, bool)
            has[ok] = vis_flat[flat[ok] + dy * W + dx]
            out_r[has] -= dy
            out_c[has] -= dx
    n = np.hypot(out_r, out_c)
    n[n == 0] = 1.0
    return tr.astype(np.int32), tc.astype(np.int32), (out_r / n).astype(np.float32), (out_c / n).astype(np.float32)


def _trace_grids(visible_foot: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Structure-tensor trace angle fields.

    Returns ``(cos2t, sin2t, t_deg)`` grids with t = trace angle from east toward south (deg, mod 180),
    built from the gradient's doubled angle: with rho the gradient angle in the (east, south) basis,
    ``t = rho + 90`` and therefore ``2t = 2rho + 180``, i.e. ``(cos2t, sin2t) = -(cos2rho, sin2rho)``.
    """
    s = gaussian_filter(np.asarray(visible_foot, np.float32), 2.0)
    gy, gx = np.gradient(s)  # gy: derivative toward increasing row (south); gx: toward increasing col (east)
    jxx = gaussian_filter(gx * gx, 2.0)
    jyy = gaussian_filter(gy * gy, 2.0)
    jxy = gaussian_filter(gx * gy, 2.0)
    cos2t = -(jxx - jyy)
    sin2t = -2.0 * jxy
    nrm = np.hypot(cos2t, sin2t)
    ok = nrm > 1e-12
    cos2t = np.where(ok, cos2t / np.maximum(nrm, 1e-12), 0.0)
    sin2t = np.where(ok, sin2t / np.maximum(nrm, 1e-12), 0.0)
    t_deg = (np.degrees(0.5 * np.arctan2(sin2t, cos2t)) % 180.0).astype(np.float32)
    return cos2t.astype(np.float32), sin2t.astype(np.float32), t_deg


def build_interaction_zone_fields(
    visible: np.ndarray,
    footprint: np.ndarray,
    footprint_idx: np.ndarray,
    *,
    sigma3_azimuth_deg: float = SIGMA3_AZIMUTH_DEG,
    params: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return ``(fields, diagnostics)``; ``fields`` is ``(4, n_footprint)`` float32 with rows ``H35_NAMES``.

    All rows are in [0, 1], zero outside the footprint, and use only ``visible`` geometry. The pair search
    is a KD-tree over tip pixels, so cost is governed by the number of tips (~10^3-10^4 on the grid).
    """
    p = dict(RELAY_PARAMS)
    if params:
        unknown = set(params) - set(RELAY_PARAMS)
        if unknown:
            raise ValueError(f"unknown relay parameters: {sorted(unknown)}")
        p.update(params)
    vis = np.asarray(visible, bool)
    foot = np.asarray(footprint, bool)
    raw = np.asarray(footprint_idx)
    if vis.ndim != 2 or vis.shape != foot.shape:
        raise ValueError("visible and footprint must be aligned 2-D grids")
    if raw.ndim != 1 or (raw.size and not np.issubdtype(raw.dtype, np.integer)):
        raise ValueError("footprint_idx must be a 1-D integer array")
    fi = raw.astype(np.int64, copy=False)
    H, W = foot.shape
    if fi.size and ((fi < 0).any() or (fi >= H * W).any() or not foot.ravel()[fi].all()):
        raise ValueError("footprint_idx must contain only valid flat indices inside the footprint")

    out = np.zeros((4, fi.size), np.float32)
    diag: dict[str, Any] = {
        "sigma3_azimuth_deg": float(sigma3_azimuth_deg),
        "dip_deg": DIP_DEG, "r2": STRESS_R2, "r3": STRESS_R3,
        "relay_params": {k: float(v) for k, v in p.items()},
        "n_tips": 0, "n_candidate_pairs": 0, "n_accepted_pairs": 0,
        "junction_seed_pixels": 0, "relay_nonzero_fraction": 0.0, "tip_nonzero_fraction": 0.0,
    }
    v = vis & foot
    if not v.any() or not fi.size:
        return out, diag

    cos2t, sin2t, tdeg = _trace_grids(v)

    # ---- relay pairing ----------------------------------------------------------------------------
    # Local strand azimuth at a tip is taken from the tip's single neighbour (the outward vector runs
    # along the trace), NOT from a structure tensor: end-of-line intensity gradients bias tensor strike
    # exactly at the tip pixels this detector depends on.
    tr, tc, ur, uc = find_trace_tips(v, foot)
    diag["n_tips"] = int(tr.size)
    raw_relay = np.zeros((H, W), np.float32)
    td_relay = np.zeros((H, W), np.float32)
    n_cand = 0
    if tr.size >= 2:
        pts = np.stack([tr.astype(np.float64), tc.astype(np.float64)], axis=1)
        pairs = cKDTree(pts).query_pairs(r=float(p["max_tip_gap_px"]), output_type="ndarray")
        n_cand = int(pairs.shape[0])
        n_acc = 0
        for a, b in pairs.tolist():
            i1, j1 = int(tr[a]), int(tc[a])
            i2, j2 = int(tr[b]), int(tc[b])
            d_r, d_c = float(i2 - i1), float(j2 - j1)
            dist = float(np.hypot(d_r, d_c))
            if not (p["min_tip_gap_px"] <= dist <= p["max_tip_gap_px"]):
                continue
            # Facing tips: each outward unit vector points toward the partner tip.
            if (float(ur[a]) * d_r + float(uc[a]) * d_c) / dist < p["facing_cos"]:
                continue
            if (-float(ur[b]) * d_r - float(uc[b]) * d_c) / dist < p["facing_cos"]:
                continue
            # Strand strikes from the tip neighbour vectors (mod 180). Sub-parallel check on |cos dt|:
            # out_a runs from neighbour to tip 1 (against the bridge), out_b from neighbour to tip 2, so
            # the two line directions are +-out_a and +-out_b and |out_a . out_b| = |cos(az1 - az2)|.
            dot_ab = float(ur[a]) * float(ur[b]) + float(uc[a]) * float(uc[b])
            if abs(dot_ab) < np.cos(np.deg2rad(p["max_strike_diff_deg"])):
                continue
            # Mean strike direction of the two strands in (row, col) space.
            ux_r = float(ur[a]) - float(ur[b])
            ux_c = float(uc[a]) - float(uc[b])
            un = float(np.hypot(ux_r, ux_c))
            if un < 1e-9:
                continue
            u = np.array([ux_r / un, ux_c / un])
            # orient u to agree with the bridge direction (tip 1 -> tip 2 ahead along the strike)
            dvec = np.array([d_r, d_c])
            if float(dvec @ u) < 0.0:
                u = -u
            if float(dvec @ u) <= 0.0:
                continue
            nrm = np.array([-u[1], u[0]])
            step = abs(float(dvec @ nrm))
            if not (p["min_step_px"] <= step <= p["max_step_px"]):
                continue
            n_acc += 1
            w_raw = float(np.exp(-dist / p["decay_px"]))
            bridge_phi = (float(np.degrees(np.arctan2(d_r, d_c))) + 90.0) % 180.0
            td = float(dilation_tendency(np.float64(bridge_phi), sigma3_azimuth_deg=sigma3_azimuth_deg))
            n_steps = max(int(np.ceil(dist * 2.0)), 1)
            rr = np.rint(np.linspace(i1, i2, n_steps + 1)).astype(np.int64)
            cc = np.rint(np.linspace(j1, j2, n_steps + 1)).astype(np.int64)
            inside = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
            rr, cc = rr[inside], cc[inside]
            ok = foot[rr, cc]
            rr, cc = rr[ok], cc[ok]
            np.maximum.at(raw_relay, (rr, cc), np.float32(w_raw))
            np.maximum.at(td_relay, (rr, cc), np.float32(w_raw * td))
        diag["n_accepted_pairs"] = int(n_acc)
    diag["n_candidate_pairs"] = int(n_cand)
    buf = int(2 * np.ceil(p["buffer_px"]) + 1)
    if raw_relay.any():
        raw_relay = maximum_filter(raw_relay, size=buf, mode="nearest")
    if td_relay.any():
        td_relay = maximum_filter(td_relay, size=buf, mode="nearest")
    out[0] = np.clip(raw_relay, 0.0, 1.0).ravel()[fi]
    out[1] = np.clip(td_relay, 0.0, 1.0).ravel()[fi]
    diag["relay_nonzero_fraction"] = float(np.mean(out[0] > 0))

    # ---- junctions: >~45 deg local orientation change within 3 px ---------------------------------
    idx = np.flatnonzero(v.ravel())
    fc2, fs2 = cos2t.ravel(), sin2t.ravel()
    seed = np.zeros(idx.size, bool)
    offs = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if (dy or dx) and max(abs(dy), abs(dx)) <= 2]
    for dy, dx in offs:
        off = dy * W + dx
        ny = idx // W + dy
        nx = idx % W + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        nb = idx[ok] + off
        dotp = fc2[idx[ok]] * fc2[nb] + fs2[idx[ok]] * fs2[nb]
        hit = np.asarray(v.ravel()[nb], bool) & (dotp < -0.05)
        acc = np.zeros(idx.size, bool)
        acc[ok] = hit
        seed |= acc
    seed_grid = np.zeros((H, W), np.float32)
    seed_grid.ravel()[idx[seed]] = 1.0
    seed_grid = gaussian_filter(seed_grid, 1.0)
    if foot.any():
        hi = float(np.percentile(seed_grid[foot], 99.9))
        if hi > 0:
            out[2] = np.clip(seed_grid / hi, 0.0, 1.0).ravel()[fi]
    diag["junction_seed_pixels"] = int(seed.sum())

    # ---- tip-cluster density ------------------------------------------------------------------------
    if tr.size:
        tipg = np.zeros((H, W), np.float32)
        np.add.at(tipg, (tr, tc), 1.0)
        tipg = gaussian_filter(tipg, 10.0)
        hi = float(np.percentile(tipg[foot], 99.5))
        if hi > 0:
            out[3] = np.clip(tipg / hi, 0.0, 1.0).ravel()[fi]
        diag["tip_nonzero_fraction"] = float(np.mean(out[3] > 1e-6))
    out[~np.isfinite(out)] = 0.0
    return out, diag

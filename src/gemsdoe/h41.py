"""H41: slip-rate-weighted INGENIOUS Quaternary-fault centroid corridors, off-catalogue aware.

Frozen in ``knowledge/24_preregistered_h41_screen_2026-10-03.md``.

Object
------
GDR 1391 publishes the INGENIOUS Quaternary fault-trace inventory that underpins the USGS QFault data
(<https://gdr.openei.org/submissions/1391>). The hash-pinned mirror this repository holds is the
**attributes-only** extract (1,126 trace rows; per-trace ``slip_rate`` in mm/yr, a ``recency`` age bin,
``map_scale``, clipped length, and a grid centroid in rows/columns; no polyline geometry). The GEMSDOE
family has never used this file for prediction (verified by a session-4 ``grep`` over ``src/``,
``scripts/`` and ``tests/``); ``registry/data_manifest.json`` pins it as ``ext_gdr_qfaults_traces``.

Per pixel we build an exponential-support field over trace centroids, weighted by slip rate and recency,
restricted (for the off-catalogue columns) to centroids more than 500 m from every pixel of the *visible*
catalogue, plus an anisotropic version smeared along the local scarp strike (a corridor, not a blob), a
scarp product, and a "purity" ratio stating how much of the local young-fault support is *not* explained
by the supplied catalogue. The hypothesis: a young, actively slipping trace mapped by INGENIOUS but absent
from the supplied raster is label-side evidence of exactly the class of fault the organizer labels contain
("newly mapped geometry of an existing fault system", second-hand staff statements registered in
``knowledge/07_metric_emission_analysis_2026-10-03.md`` section 1).

Ceiling and honesty
-------------------
A centroid is a single point with a 2.5-km-scale kernel: it cannot place a 300-m-kernel credit dot on a
fault trace, only raise the prior around it. That ceiling is declared, not discovered later. Everything
here derives from the *visible* catalogue and the static attribute table - never from hidden labels.
Rows are validated against the grid shape and the ``centroid_in_footprint`` flag; a ``recency`` string
outside the frozen table receives the fallback weight and is counted in the diagnostics, and rows whose
field count cannot be repaired by quote handling are dropped and counted (the mirrored CSV contains one
malformed age bin, registered as an irregularity).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt

H41_NAMES = ["H41_SUPP", "H41_OFF", "H41_CORR", "H41_OFF_SCARP", "H41_PURITY"]

# Frozen parameters (knowledge/24 section 2). Grid spacing is 100 m, so 1 px = 100 m.
H41_PARAMS: dict[str, float] = dict(
    decay_px=25.0,              # 2.5 km exponential decay length (v3 spec: exp(-d / 2.5 km))
    cutoff_px=50.0,             # 5.0 km support radius = 2 * decay; beyond it the kernel is dropped
    off_catalogue_min_px=5.0,   # a centroid is off-catalogue at >= 500 m from every visible pixel
    corridor_half_len_px=12.0,  # +/- 1.2 km anisotropic smear along the local strike
    n_orientations=8,           # orientations sampled every 22.5 deg (mod 180)
    purity_eps=1e-6,
)

# Frozen recency -> weight table (INGENIOUS age bins; younger = higher). These are judgement weights, not
# measured physical quantities; the mapping is published in the preregistration and never re-tuned.
RECENCY_WEIGHTS: dict[str, float] = {
    "<150": 1.00,
    "<15,000": 0.80,
    "<130,000": 0.60,
    "<750,000": 0.40,
    "<1,600,000": 0.25,
}
RECENCY_FALLBACK_WEIGHT = 0.15  # unparsable / unlisted bins (counted in diagnostics)


@dataclass
class CentroidField:
    """Draw-independent H41 inputs rebuilt once per run from the pinned attribute table."""

    rows: np.ndarray             # int32 centroid row (grid row index)
    cols: np.ndarray             # int32 centroid col
    weights: np.ndarray          # float64 slip-rate x recency weight, in (0, 1]
    off_flag: np.ndarray         # bool per-centroid off-catalogue flag, set per draw by the builder
    scale: float                 # normalization constant (99.9th pct of the all-centroid support field)
    diagnostics: dict[str, Any]

    @property
    def n(self) -> int:
        return int(self.rows.size)


def _split_csv_line(line: str, header: list[str]) -> list[str] | None:
    """Split one CSV row honouring double quotes; return exactly ``len(header)`` fields or None."""
    out: list[str] = []
    cur, in_q = "", False
    for ch in line:
        if ch == '"':
            in_q = not in_q
        elif ch == "," and not in_q:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out if len(out) == len(header) else None


def parse_centroids(csv_path: Path | str, *, shape: tuple[int, int]) -> CentroidField:
    """Read the pinned qfaults attribute CSV and return in-footprint centroids with frozen weights.

    ``shape`` is the competition grid ``(height, width)``. A row is used only when its
    ``centroid_in_footprint`` flag is truthy and its centroid lands inside the grid; every exclusion is
    counted in the diagnostics rather than silently dropped.
    """
    p = Path(csv_path)
    text = p.read_text(encoding="utf-8").splitlines()
    if not text:
        raise ValueError(f"empty centroid table: {p}")
    header = [h.strip() for h in text[0].split(",")]
    need = ["slip_rate", "recency", "centroid_row", "centroid_col", "centroid_in_footprint"]
    missing = [k for k in need if k not in header]
    if missing:
        raise ValueError(f"qfaults CSV missing columns {missing}; header={header}")
    idx = {k: header.index(k) for k in header}

    rows: list[int] = []
    cols: list[int] = []
    pairs: list[tuple[float, float]] = []
    diag = dict(
        file=str(p), n_rows_read=0, n_in_footprint=0, n_dropped_out_of_grid=0, n_rows_unparsable=0,
        n_slip_rate_missing=0, n_recency_unmapped=0, recency_counts={}, slip_rate_max_seen=0.0,
    )
    for line in text[1:]:
        if not line.strip():
            continue
        diag["n_rows_read"] += 1
        parts = _split_csv_line(line, header)
        if parts is None:
            # field count cannot be repaired by quote handling: drop and count, never guess
            diag["n_rows_unparsable"] += 1
            continue

        def get(key: str, _parts=parts) -> str:
            return _parts[idx[key]].strip().strip('"')

        if get("centroid_in_footprint") not in ("1", "1.0", "True", "true"):
            continue
        diag["n_in_footprint"] += 1
        try:
            r = int(float(get("centroid_row")))
            c = int(float(get("centroid_col")))
        except ValueError:
            diag["n_dropped_out_of_grid"] += 1
            continue
        if not (0 <= r < shape[0] and 0 <= c < shape[1]):
            diag["n_dropped_out_of_grid"] += 1
            continue
        try:
            slip = float(get("slip_rate"))
            if not np.isfinite(slip) or slip <= 0.0:
                raise ValueError
        except ValueError:
            slip = float("nan")
            diag["n_slip_rate_missing"] += 1
        rec = get("recency")
        w_rec = RECENCY_WEIGHTS.get(rec)
        if w_rec is None:
            w_rec = RECENCY_FALLBACK_WEIGHT
            diag["n_recency_unmapped"] += 1
        diag["recency_counts"][rec] = diag["recency_counts"].get(rec, 0) + 1
        rows.append(r)
        cols.append(c)
        pairs.append((slip, w_rec))
    if not rows:
        raise ValueError(f"no usable centroids inside the {shape} grid in {p}")

    slip_max = max((s for s, _ in pairs if np.isfinite(s)), default=0.0)
    if slip_max <= 0.0:
        raise ValueError("no positive slip rates in the in-footprint subset")
    diag["slip_rate_max_seen"] = float(slip_max)
    # Slip-rate term is log-scaled against the file-wide maximum so weights are draw-independent, bounded
    # and monotone in slip rate; the recency bin multiplies it. Weights are in (0, 1].
    w = np.empty(len(pairs), np.float64)
    for i, (slip, w_rec) in enumerate(pairs):
        slip_term = np.log1p(slip) / np.log1p(slip_max) if np.isfinite(slip) and slip > 0 else 0.25
        w[i] = float(np.clip(slip_term * w_rec / max(RECENCY_WEIGHTS.values()), 1e-6, 1.0))
    diag["weight_summary"] = dict(
        min=float(w.min()), median=float(np.median(w)), max=float(w.max()),
        n_missing_slip_fallback=int(sum(1 for s, _ in pairs if not (np.isfinite(s) and s > 0))),
    )

    field = CentroidField(
        rows=np.asarray(rows, np.int32), cols=np.asarray(cols, np.int32), weights=w,
        off_flag=np.ones(len(rows), bool), scale=1.0, diagnostics=diag,
    )
    field.scale = support_scale(field, shape)
    return field


def support_raster(field: CentroidField, shape: tuple[int, int], *, mask: np.ndarray | None = None
                   ) -> np.ndarray:
    """Point raster of (optionally masked) centroid weights, summed per pixel, float32 grid."""
    grid = np.zeros(shape, np.float32)
    rows, cols, w = field.rows, field.cols, field.weights
    if mask is not None:
        keep = np.asarray(mask, bool)
        rows, cols, w = rows[keep], cols[keep], w[keep]
    np.add.at(grid, (rows, cols), w.astype(np.float32))
    return grid


def exponential_support(points: np.ndarray, *, decay_px: float, cutoff_px: float) -> np.ndarray:
    """Dense ``sum_i w_i * exp(-d / decay)`` field from a sparse point raster (exact Euclidean kernel).

    Implemented as a patch accumulation: cost is (occupied pixels) x (2 * cutoff + 1)^2, which on the real
    1,126-row table is ~10^7 operations - no FFT, no padding artefacts, and the kernel is exactly the one in
    the preregistration. Grid edges truncate the kernel (no wrap, no renormalisation), which is recorded in
    the preregistration as an accepted boundary effect.
    """
    pts = np.asarray(points, np.float32)
    if pts.ndim != 2:
        raise ValueError("point raster must be 2-D")
    if decay_px <= 0 or cutoff_px < decay_px:
        raise ValueError("need cutoff_px >= decay_px > 0")
    H, W = pts.shape
    out = np.zeros((H, W), np.float32)
    rr, cc = np.nonzero(pts)
    if rr.size == 0:
        return out
    rad = int(np.ceil(cutoff_px))
    dy, dx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    dist = np.hypot(dy, dx)
    kern = np.where(dist <= cutoff_px, np.exp(-dist / decay_px), 0.0).astype(np.float32)
    kh, kw = kern.shape
    for i in range(rr.size):
        y, x = int(rr[i]), int(cc[i])
        wgt = float(pts[y, x])
        if wgt == 0.0:
            continue
        y0, x0 = y - rad, x - rad
        sy0, sx0 = max(0, -y0), max(0, -x0)
        sy1 = min(kh, H - y0)
        sx1 = min(kw, W - x0)
        if sy1 <= sy0 or sx1 <= sx0:
            continue
        out[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1] += np.float32(wgt) * kern[sy0:sy1, sx0:sx1]
    return out


def support_scale(field: CentroidField, shape: tuple[int, int], *,
                  decay_px: float = H41_PARAMS["decay_px"], cutoff_px: float = H41_PARAMS["cutoff_px"],
                  percentile: float = 99.9) -> float:
    """Draw-independent normalization constant: the requested percentile of the all-centroid support field."""
    sup = exponential_support(support_raster(field, shape), decay_px=decay_px, cutoff_px=cutoff_px)
    v = sup[sup > 0]
    if v.size == 0:
        raise ValueError("support field is identically zero")
    return float(np.percentile(v, percentile))


def corridor_smear(points: np.ndarray, cos2t: np.ndarray, sin2t: np.ndarray, *,
                   fallback: np.ndarray, half_len_px: float, n_orientations: int) -> np.ndarray:
    """Anisotropic line smear of ``points`` steered by a local doubled-angle strike field.

    For each sampled orientation ``t_k`` the point field is accumulated along a straight line of
    ``+/- half_len_px`` pixels; per pixel the responses are combined with weights
    ``w_k = 0.5 * (1 + cos(2 (t_p - t_k)))`` built from ``(cos2t, sin2t)``, so the response whose line
    orientation matches the local strike dominates. Pixels without a local fabric (both components ~ 0)
    keep ``fallback``.
    """
    pts = np.asarray(points, np.float32)
    if pts.ndim != 2:
        raise ValueError("point raster must be 2-D")
    H, W = pts.shape
    c2 = np.asarray(cos2t, np.float32)
    s2 = np.asarray(sin2t, np.float32)
    if c2.shape != pts.shape or s2.shape != pts.shape:
        raise ValueError("strike fields must match the point raster shape")
    fb = np.asarray(fallback, np.float32)
    if fb.shape != pts.shape:
        raise ValueError("fallback must match the point raster shape")
    J = int(np.floor(half_len_px))
    if J < 1:
        return pts.copy()
    valid = (c2 ** 2 + s2 ** 2) > 1e-8
    num = np.zeros((H, W), np.float32)
    den = np.zeros((H, W), np.float32)
    for k in range(int(n_orientations)):
        t = 180.0 * k / n_orientations
        # trace angle t is measured from east toward south: unit step (dr, dc) = (sin t, cos t)
        ur, uc = float(np.sin(np.deg2rad(t))), float(np.cos(np.deg2rad(t)))
        resp = np.zeros((H, W), np.float32)
        for j in range(-J, J + 1):
            dr, dc = int(round(j * ur)), int(round(j * uc))
            if dr == 0 and dc == 0:
                resp += pts
                continue
            rs, cs = slice(max(0, -dr), H - max(0, dr)), slice(max(0, -dc), W - max(0, dc))
            rd, cd = slice(max(0, dr), H - max(0, -dr)), slice(max(0, dc), W - max(0, -dc))
            resp[rd, cd] += pts[rs, cs]
        # cos(2 (t_p - t_k)) = cos2t_p cos2t_k + sin2t_p sin2t_k
        wk = 0.5 * (1.0 + (c2 * np.float32(np.cos(np.deg2rad(2 * t)))
                           + s2 * np.float32(np.sin(np.deg2rad(2 * t)))))
        num += wk * resp
        den += wk
    out = np.where(valid & (den > 0), num / np.maximum(den, np.float32(1e-6)), fb)
    return np.asarray(out, np.float32)


def build_h41_fields(field: CentroidField, *, visible: np.ndarray, footprint: np.ndarray,
                     footprint_idx: np.ndarray, scarp_vec: np.ndarray, cos2t: np.ndarray,
                     sin2t: np.ndarray, params: dict[str, float] | None = None
                     ) -> tuple[np.ndarray, dict[str, Any]]:
    """Return ``(fields, diagnostics)``; ``fields`` is ``(5, n_footprint)`` float32 with rows ``H41_NAMES``.

    ``visible`` is the draw's visible catalogue grid, ``footprint`` the template footprint,
    ``footprint_idx`` its flat indices, ``scarp_vec`` the footprint-vector H27 scarp composite in [0, 1],
    and ``(cos2t, sin2t)`` the local doubled-angle strike grid derived from the scarp surface. All rows are
    finite, in [0, 1], and zero outside the footprint.
    """
    p = dict(H41_PARAMS)
    if params:
        unknown = set(params) - set(H41_PARAMS)
        if unknown:
            raise ValueError(f"unknown H41 parameters: {sorted(unknown)}")
        p.update(params)
    foot = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool) & foot
    H, W = foot.shape
    fi = np.asarray(footprint_idx, np.int64)
    if fi.size == 0:
        raise ValueError("empty footprint")
    if fi.size and ((fi < 0).any() or (fi >= H * W).any() or not foot.ravel()[fi].all()):
        raise ValueError("footprint_idx must contain only valid flat indices inside the footprint")
    scarp = np.asarray(scarp_vec, np.float32)
    if scarp.shape != (fi.size,):
        raise ValueError("scarp vector must align with footprint_idx")

    dist_cat = distance_transform_edt(~vis) if vis.any() else np.full((H, W), np.inf, np.float64)
    cd = dist_cat[field.rows, field.cols]
    off = cd >= float(p["off_catalogue_min_px"])
    field.off_flag = off

    pts_all = support_raster(field, (H, W))
    pts_off = support_raster(field, (H, W), mask=off)
    sup = exponential_support(pts_all, decay_px=p["decay_px"], cutoff_px=p["cutoff_px"]) / field.scale
    off_sup = exponential_support(pts_off, decay_px=p["decay_px"], cutoff_px=p["cutoff_px"]) / field.scale
    corr = corridor_smear(pts_off, cos2t, sin2t, fallback=off_sup,
                          half_len_px=p["corridor_half_len_px"], n_orientations=int(p["n_orientations"]))
    corr = corr / field.scale

    sup = np.clip(sup, 0.0, 1.0)
    off_sup = np.clip(off_sup, 0.0, 1.0)
    corr = np.clip(corr, 0.0, 1.0)
    purity = np.clip(off_sup / (sup + np.float32(p["purity_eps"])), 0.0, 1.0)

    scarp_grid = np.zeros((H, W), np.float32)
    scarp_grid.ravel()[fi] = np.nan_to_num(scarp, nan=0.0, posinf=0.0, neginf=0.0)

    out = np.zeros((5, fi.size), np.float32)
    out[0] = sup.ravel()[fi]
    out[1] = off_sup.ravel()[fi]
    out[2] = corr.ravel()[fi]
    out[3] = (off_sup * scarp_grid).ravel()[fi]
    out[4] = purity.ravel()[fi]
    out = np.clip(out, 0.0, 1.0)

    diag = dict(
        params={k: float(v) for k, v in p.items()},
        n_centroids_total=int(field.n), n_centroids_off_catalogue=int(off.sum()),
        n_centroids_near_catalogue=int((~off).sum()), visible_pixels=int(vis.sum()),
        nonzero_fraction={n: float((out[i] > 1e-4).mean()) for i, n in enumerate(H41_NAMES)},
        max_value={n: float(out[i].max()) for i, n in enumerate(H41_NAMES)},
        mean_value={n: float(out[i].mean()) for i, n in enumerate(H41_NAMES)},
        support_scale=float(field.scale),
        scarp_nonzero_fraction=float((scarp_grid > 0).mean()),
    )
    diag.update({k: v for k, v in field.diagnostics.items() if k != "file"})
    return out, diag


def degenerate_fields(fields: np.ndarray, *, min_nonzero_fraction: float = 0.002) -> list[str]:
    """Names of H41 columns too sparse to move a boosted model (the H31 failure mode).

    Pre-declared viability guard: ``min_nonzero_fraction`` = 0.2 % of footprint pixels, ~10x the largest
    nonzero fraction measured for the H31 columns (0.084 %). Returned as a list so the caller decides
    whether to abort; it never edits the frozen gate.
    """
    problems: list[str] = []
    f = np.asarray(fields)
    if f.ndim != 2 or f.shape[0] != len(H41_NAMES):
        raise ValueError("fields must be (5, n_pixels)")
    for i, name in enumerate(H41_NAMES):
        frac = float((np.nan_to_num(f[i]) > 1e-4).mean())
        if frac < min_nonzero_fraction:
            problems.append(f"{name}: nonzero on {frac:.5%} of pixels (< {min_nonzero_fraction:.1%})")
    if not np.isfinite(f).all():
        problems.append("non-finite values in the H41 field block")
    if float(np.nanmin(f)) < -1e-6 or float(np.nanmax(f)) > 1.0 + 1e-6:
        problems.append("H41 fields violate [0, 1]")
    return problems

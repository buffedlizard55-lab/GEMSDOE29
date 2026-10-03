"""H31b dense continuous worming persistence features (family W).

Frozen design: ``knowledge/19_preregistered_h31b_dense_worming_2026-10-03.md``.

Unlike H31 (which recorded persistence only at 0-m local-maximum seed pixels and produced
0.001–0.084 %-nonzero columns), H31b evaluates the horizontal-gradient modulus at *every*
footprint pixel at each continuation height and aggregates across heights, so the resulting
columns are dense in space. Inputs are the two independent potential-field layers (reduced-to-pole
magnetics, isostatic gravity anomaly) plus the documented FFT/vertical-integration pseudogravity
proxy of the magnetic field. No labels or catalogue geometry enter.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import fft

from .worms import H31_HEIGHTS_M, WormConfig, _prepare_spectrum

W_NAMES = [
    "W_RTP_FRAC", "W_RTP_LAST", "W_RTP_E0", "W_RTP_DEEP",
    "W_PSG_FRAC", "W_PSG_LAST", "W_PSG_E0", "W_PSG_DEEP",
    "W_GRAV_FRAC", "W_GRAV_LAST", "W_GRAV_E0", "W_GRAV_DEEP",
]
W_BRANCHES = ("RTP", "PSG", "GRAV")
_PER_BRANCH = ("FRAC", "LAST", "E0", "DEEP")
EDGE_PERCENTILE = 90.0


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _height_grid(spectrum: np.ndarray, radial_k: np.ndarray, height_m: float,
                 cell_size_m: float, out_shape: tuple[int, int]) -> np.ndarray:
    """Inverse-transform the upward-continued spectrum back to a full (padded) grid."""
    if height_m > 0:
        filt = np.exp(-(radial_k * height_m) / cell_size_m)  # radial_k is 2*pi*k
        spectrum = spectrum * filt
    return fft.irfft2(spectrum, s=out_shape).real


def _hgm(grid: np.ndarray, cell_size_m: float) -> np.ndarray:
    gy, gx = np.gradient(grid, cell_size_m, edge_order=2)
    return np.hypot(gx, gy).astype(np.float32)


def _scale(a: np.ndarray, interior: np.ndarray) -> np.ndarray:
    """Percentile (1,99)-scale over the interior domain, clipped to [0,1]."""
    v = a[interior]
    lo, hi = float(np.percentile(v, 1)), float(np.percentile(v, 99))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        hi = lo + 1.0
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def build_branch(
    field: np.ndarray,
    footprint: np.ndarray,
    *,
    config: WormConfig,
    pseudogravity: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build the four dense per-branch columns (FRAC, LAST, E0, DEEP) for one input field.

    Returns a (4, H, W) float32 array (values on the finite footprint, zero elsewhere) and a
    diagnostics dict with the per-height scale thresholds.
    """
    cfg = WormConfig(
        cell_size_m=config.cell_size_m,
        heights_m=config.heights_m,
        taper_px=config.taper_px,
        pad_px=config.pad_px,
        boundary_guard_px=config.boundary_guard_px,
        edge_percentile=EDGE_PERCENTILE,
        max_match_px=config.max_match_px,
        pseudogravity_vertical_integration=pseudogravity,
    )
    from scipy.ndimage import distance_transform_edt

    field = np.asarray(field, np.float32)
    spectrum, radial_k, safe16, foot, diag = _prepare_spectrum(field, footprint, config=cfg)
    # Margin-zero band: the cosine taper used as an FFT boundary condition creates artificial
    # HGM rings up to `taper_px` from the footprint boundary, so outputs inside
    # `taper_px + 4` px of the boundary are zeroed and excluded from threshold statistics
    # (frozen in the preregistration, section 3).
    padded_foot = np.pad(foot, 1, mode="constant", constant_values=False)
    edge_distance = distance_transform_edt(padded_foot)[1:-1, 1:-1]
    margin = cfg.taper_px + 4
    finite = foot & np.isfinite(field)
    interior = finite & (edge_distance >= margin)  # statistics domain: observed data only
    out_dom = foot & (edge_distance >= margin)  # output domain (value/NaN); margin band -> 0
    if int(interior.sum()) < 100:
        raise ValueError(f"too few observed interior pixels after the {margin}-px margin-zero band")
    p = cfg.pad_px
    out_shape = (field.shape[0] + 2 * p, field.shape[1] + 2 * p)
    heights = cfg.heights_m
    upward = [h for h in heights if h > 0]
    max_h = max(heights)

    e0 = _hgm(_height_grid(spectrum, radial_k, 0.0, cfg.cell_size_m, out_shape)[p:-p, p:-p],
              cfg.cell_size_m)
    deep = _hgm(_height_grid(spectrum, radial_k, max_h, cfg.cell_size_m, out_shape)[p:-p, p:-p],
                cfg.cell_size_m)
    frac = np.zeros(field.shape, np.float32)
    last = np.zeros(field.shape, np.float32)
    thresholds: dict[str, float] = {}
    for h in upward:
        e_h = _hgm(_height_grid(spectrum, radial_k, float(h), cfg.cell_size_m, out_shape)[p:-p, p:-p],
                   cfg.cell_size_m)
        q = float(np.percentile(e_h[interior], EDGE_PERCENTILE))
        thresholds[f"h{h}"] = q
        sig = (e_h >= q) & interior
        frac += sig.astype(np.float32) / len(upward)
        last = np.maximum(last, np.where(sig, h / max_h, 0.0).astype(np.float32))
        del e_h, sig

    def place(v: np.ndarray) -> np.ndarray:
        """Value on the output domain; NaN where the input band is nodata; exactly 0 in the
        margin band and outside the footprint (A-family re-masking convention, HGB-native NaN)."""
        out = np.where(out_dom, np.asarray(v, np.float32), np.nan).astype(np.float32)
        out = np.where(foot & (edge_distance < margin), 0.0, out)
        return out

    cols = np.stack([
        place(frac),
        place(last),
        place(_scale(e0, interior)),
        place(_scale(deep, interior)),
    ])
    diag = {
        **diag,
        "pseudogravity_input": bool(pseudogravity),
        "upward_heights_m": upward,
        "edge_percentile": EDGE_PERCENTILE,
        "margin_zero_band_px": int(margin),
        "observed_interior_pixels": int(interior.sum()),
        "input_finite_fraction_in_footprint": float(finite.sum() / max(foot.sum(), 1)),
        "per_height_thresholds": thresholds,
    }
    return cols, diag


def build_w_features(
    band_dir: Path,
    footprint: np.ndarray,
    rtp: np.ndarray,
    grav: np.ndarray,
    *,
    config: WormConfig | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build the full 12-column family W cache.

    ``rtp`` and ``grav`` are the aligned float32 band arrays (NaN where invalid). Returns
    (12, H, W) float32 in ``W_NAMES`` order plus metadata.
    """
    cfg = config or WormConfig()
    cfg.validate()
    foot = np.asarray(footprint, bool)
    branches: dict[str, tuple[np.ndarray, dict]] = {
        "RTP": build_branch(rtp, foot, config=cfg, pseudogravity=False),
        "PSG": build_branch(rtp, foot, config=cfg, pseudogravity=True),
        "GRAV": build_branch(grav, foot, config=cfg, pseudogravity=False),
    }
    fi = np.flatnonzero(foot.ravel())
    out = np.empty((len(W_NAMES), fi.size), np.float32)
    for bi, b in enumerate(W_BRANCHES):
        cols, _ = branches[b]
        for ci in range(len(_PER_BRANCH)):
            out[bi * 4 + ci] = np.asarray(cols[ci], np.float32).ravel()[fi]
    stats = {}
    for i, n in enumerate(W_NAMES):
        v = out[i]
        fin = v[np.isfinite(v)]
        stats[n] = {
            "nonzero_fraction": float(np.sum(np.isfinite(v) & (v != 0.0)) / max(v.size, 1)),
            "nan_fraction": float(np.sum(~np.isfinite(v)) / max(v.size, 1)),
            "mean": float(fin.mean()) if fin.size else 0.0,
            "p50": float(np.percentile(fin, 50)) if fin.size else 0.0,
            "p95": float(np.percentile(fin, 95)) if fin.size else 0.0,
            "max": float(fin.max()) if fin.size else 0.0,
            "no_infinite": bool(not np.isinf(v).any()),
        }
    metadata = dict(
        names=list(W_NAMES),
        config=asdict(cfg),
        branch_diagnostics={b: branches[b][1] for b in W_BRANCHES},
        column_stats=stats,
    )
    return out, metadata


def write_cache(
    out_path: Path,
    meta_path: Path,
    features: np.ndarray,
    metadata: dict[str, Any],
    input_hashes: dict[str, str],
    code_revision: str,
) -> dict[str, Any]:
    """Write the float32 cache and a deterministic metadata receipt; record the output hash."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, features)
    meta = dict(
        schema_version=1,
        input_hashes=input_hashes,
        code_revision=code_revision,
        **metadata,
    )
    meta["output_sha256"] = _sha256_file(out_path)
    meta_path.write_text(_json_dumps(meta))
    return meta


def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"

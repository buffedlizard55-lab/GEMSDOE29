"""Write + independently verify a DrivenData #306 submission GeoTIFF.

Official format (problem page, read 2026-10-03): single-layer float32 GeoTIFF, EPSG:32611, same
resolution/bounds as training data, values between 0 and 1, data outside the bounds null or nan.

The portal error the owner reported ("Predicted values must be in range [0, 1]") is NOT fully
explained by any public document; the sibling forensics (GEMSDOE25 IR-25-NAN-FOOTPRINT) found the
failing file had NaN *inside* an invented footprint and NaN fails every range test. Defense in
depth, all enforced here and re-checked by the independent verifier:
  1. profile copied from the pinned sample_submission.tif (exact transform, shape, dtype);
  2. every in-footprint pixel finite and exactly in [0,1] (binary 0.0/1.0 by construction);
  3. outside the template footprint: NaN convention (matches the sample's own nodata=NaN) AND an
     all-finite fallback with 0.0 outside (both conventions scored historically — 12GEMSDOE pair);
  4. a .zip containing exactly one GeoTIFF (the form also accepts zip);
  5. read-back verification with independent tooling (fresh open, no shared handles).
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from . import paths


def sha256_file(p: Path | str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def write_submission(mask: np.ndarray, out_dir: Path, stem: str, *, note: str) -> dict:
    """mask: boolean pixels to emit at value 1.0. Writes -nan.tif, -zeros.tif, .zip + checks."""
    out_dir.mkdir(parents=True, exist_ok=True)
    template = paths.DATA / "bridge" / "sample_submission.tif"
    with rasterio.open(template) as t:
        prof = t.profile.copy()
        foot = np.isfinite(t.read(1))
    if prof["crs"].to_epsg() != 32611 or prof["height"] != 3730 or prof["width"] != 3292:
        raise ValueError("template grid mismatch")
    if mask.shape != foot.shape:
        raise ValueError("mask shape mismatch with template grid")
    if not (mask & ~foot).sum() == 0:
        raise ValueError("emission extends outside the template footprint")
    vals = np.where(mask, np.float32(1.0), np.float32(0.0))
    prof.update(dtype="float32", count=1)
    files = {}
    nan_arr = np.where(foot, vals, np.float32(np.nan))
    zero_arr = np.where(foot, vals, np.float32(0.0))
    p_nan = out_dir / f"{stem}-nan.tif"
    p_zero = out_dir / f"{stem}-zeros.tif"
    with rasterio.open(p_nan, "w", **prof, nodata=np.nan) as ds:
        ds.write(nan_arr, 1)
    p2 = dict(prof)
    p2["nodata"] = None
    with rasterio.open(p_zero, "w", **p2) as ds:
        ds.write(zero_arr, 1)
    p_zip = out_dir / f"{stem}-nan.zip"
    with zipfile.ZipFile(p_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(p_nan, arcname=p_nan.name)
    checks = verify_files(out_dir, stem, foot_mask=foot, expected_px=int(mask.sum()))
    (out_dir / f"checks-{stem}.json").write_text(json.dumps(
        {"stem": stem, "note_to_paste": note, "checks": checks,
         "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
                   for p in [p_nan, p_zero, p_zip]}}, indent=2))
    return checks


def verify_files(out_dir: Path, stem: str, foot_mask: np.ndarray | None = None,
                 expected_px: int | None = None) -> dict:
    """Independent read-back verification; returns a dict of check->pass/fail with details."""
    checks: dict[str, dict] = {}

    def rec(name, ok, detail=""):
        checks[name] = {"pass": bool(ok), "detail": str(detail)}

    p_nan = out_dir / f"{stem}-nan.tif"
    p_zero = out_dir / f"{stem}-zeros.tif"
    p_zip = out_dir / f"{stem}-nan.zip"
    for p in (p_nan, p_zero):
        with rasterio.open(p) as ds:
            a = ds.read(1)
            rec(f"{p.name}:single_float32_band", ds.count == 1 and ds.dtypes[0] == "float32",
                f"{ds.count} band(s) {ds.dtypes[0]}")
            rec(f"{p.name}:grid", (ds.height, ds.width) == (3730, 3292) and ds.crs.to_epsg() == 32611
                and tuple(ds.transform)[:6] == tuple(paths.GRID["transform"]),
                f"{(ds.height, ds.width)} {ds.crs}")
            fin = np.isfinite(a)
            v = a[fin]
            rec(f"{p.name}:values_in_01", np.all((v >= 0.0) & (v <= 1.0)), f"min={v.min()}, max={v.max()}")
            rec(f"{p.name}:no_nan_inside_template_footprint",
                (foot_mask is None) or not (np.isnan(a) & foot_mask).any())
            n_pos = int((a > 0.5).sum())
            if expected_px is not None:
                rec(f"{p.name}:pixel_count", n_pos == expected_px, f"{n_pos} vs {expected_px}")
            rec(f"{p.name}:binary", bool(np.all(np.isin(v[v > 0], [1.0]))), f"n_positive={n_pos}")
    with zipfile.ZipFile(p_zip) as z:
        names = z.namelist()
        rec("zip:exactly_one_geotiff", len(names) == 1 and names[0].endswith(".tif"), names)
        z.extract(p_zip.with_suffix("").name and Path(z.namelist()[0]).name, path=out_dir / "_zip_probe")
    probe = out_dir / "_zip_probe" / p_nan.name
    if probe.exists():
        with rasterio.open(probe) as ds:
            a = ds.read(1)
        with rasterio.open(p_nan) as ds:
            b = ds.read(1)
        rec("zip:content_identical", np.array_equal(np.nan_to_num(a), np.nan_to_num(b))
            and np.array_equal(np.isnan(a), np.isnan(b)))
        probe.unlink()
    else:
        rec("zip:content_identical", False, "probe missing")
    n_fails = sum(1 for c in checks.values() if not c["pass"])
    rec("__summary__", n_fails == 0, f"{len(checks)} checks, {n_fails} failures")
    return checks

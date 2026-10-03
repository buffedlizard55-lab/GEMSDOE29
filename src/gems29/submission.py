"""Write and independently verify DOE GEMS submission GeoTIFFs.

The official-format claims used here are the competition's single-band float32 GeoTIFF,
EPSG:32611, 100 m, exact template grid, in-footprint values in [0,1], and null/NaN outside the
footprint. This code can verify a local file against the pinned sample template; it cannot
authenticate the owner mirror or guarantee that the organizer portal accepts the file.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile

from . import paths


def sha256_file(p: Path | str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _template() -> tuple[dict, np.ndarray]:
    template = paths.template_path()
    with rasterio.open(template) as ds:
        return ds.profile.copy(), np.isfinite(ds.read(1))


def _check_dataset(ds, *, tag: str, foot: np.ndarray, expected_transform,
                   expected_crs, expected_px: int | None, outside_mode: str,
                   rec) -> np.ndarray:
    arr = ds.read(1)
    rec(f"{tag}:single_float32_band", ds.count == 1 and ds.dtypes[0] == "float32",
        f"{ds.count} band(s), dtype={ds.dtypes[0]}")
    grid_ok = (ds.height, ds.width) == foot.shape and ds.crs == expected_crs \
        and ds.transform == expected_transform
    rec(f"{tag}:exact_template_grid", grid_ok,
        f"shape={(ds.height, ds.width)}, CRS={ds.crs}, transform={tuple(ds.transform)[:6]}")

    inside = arr[foot]
    inside_ok = bool(inside.size and np.isfinite(inside).all()
                     and np.all((inside >= 0.0) & (inside <= 1.0)))
    rec(f"{tag}:in_footprint_finite_and_01", inside_ok,
        f"finite={int(np.isfinite(inside).sum())}/{inside.size}, "
        f"min={float(np.nanmin(inside)) if inside.size else 'n/a'}, "
        f"max={float(np.nanmax(inside)) if inside.size else 'n/a'}")

    outside = arr[~foot]
    if outside_mode == "nan":
        outside_ok = bool(np.isnan(outside).all())
    elif outside_mode == "zero":
        outside_ok = bool(np.isfinite(outside).all() and np.all(outside == 0.0))
    else:
        outside_ok = bool(np.isnan(outside).all() or np.all(outside == 0.0))
    rec(f"{tag}:outside_{outside_mode}_convention", outside_ok,
        f"outside_pixels={outside.size}")

    positives = int(np.count_nonzero(inside > 0.5))
    if expected_px is not None:
        rec(f"{tag}:pixel_count", positives == expected_px,
            f"{positives} positive pixels vs expected {expected_px}")
    binary_ok = bool(np.isin(inside, (0.0, 1.0)).all())
    rec(f"{tag}:binary_01", binary_ok, f"positive pixels={positives}")
    return arr


def write_submission(mask: np.ndarray, out_dir: Path, stem: str, *, note: str) -> dict:
    """Write NaN-outside, zero-outside and one-TIFF ZIP variants; locally read back and verify.

    ``mask`` is a boolean emission mask. ``stem`` is the unique submission/artifact name; ``note``
    is the short portal note (max 200 characters). Raises instead of packaging a failed check.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,119}", stem):
        raise ValueError("stem must be a safe, unique 1–120 character identifier")
    if not isinstance(note, str) or not note.strip() or len(note) > 200:
        raise ValueError("submission note must be non-empty and at most 200 characters")
    mask = np.asarray(mask)
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("mask must be a 2-D boolean array")

    out_dir.mkdir(parents=True, exist_ok=True)
    prof, foot = _template()
    if prof["crs"].to_epsg() != 32611 or prof["height"] != 3730 or prof["width"] != 3292:
        raise ValueError("pinned template grid mismatch")
    if tuple(prof["transform"])[:6] != tuple(paths.GRID["transform"]):
        raise ValueError("pinned template geotransform differs from the declared grid")
    if mask.shape != foot.shape:
        raise ValueError("mask shape mismatch with template grid")
    if np.any(mask & ~foot):
        raise ValueError("emission extends outside the template footprint")

    vals = np.where(mask, np.float32(1.0), np.float32(0.0))
    prof.update(dtype="float32", count=1, driver="GTiff")
    nan_arr = np.where(foot, vals, np.float32(np.nan))
    zero_arr = np.where(foot, vals, np.float32(0.0))
    p_nan = out_dir / f"{stem}-nan.tif"
    p_zero = out_dir / f"{stem}-zeros.tif"
    p_zip = out_dir / f"{stem}-nan.zip"
    prof["nodata"] = float("nan")
    with rasterio.open(p_nan, "w", **prof) as ds:
        ds.write(nan_arr.astype(np.float32), 1)
    p2 = dict(prof)
    p2["nodata"] = None
    with rasterio.open(p_zero, "w", **p2) as ds:
        ds.write(zero_arr.astype(np.float32), 1)
    with zipfile.ZipFile(p_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(p_nan, arcname=p_nan.name)

    checks = verify_files(out_dir, stem, foot_mask=foot, expected_px=int(mask.sum()))
    ok = bool(checks["__summary__"]["pass"])
    tr = prof["transform"]
    receipt = {
        "stem": stem,
        "note_to_paste": note,
        "grid": {
            "crs": prof["crs"].to_string(),
            "width": int(prof["width"]),
            "height": int(prof["height"]),
            "pixel_size_m": [abs(float(tr.a)), abs(float(tr.e))],
            "footprint_pixels": int(foot.sum()),
        },
        "format": {
            "driver": "GTiff",
            "bands": 1,
            "dtype": "float32",
            "inside_value_range": [0.0, 1.0],
            "outside": "NaN",
            "note_max_characters": 200,
        },
        "local_format_verified": ok,
        "organizer_portal_acceptance": "not verified; owner must upload manually",
        "checks": checks,
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
                  for p in (p_nan, p_zero, p_zip) if p.is_file()},
    }
    receipt_path = out_dir / f"checks-{stem}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    if not ok:
        raise RuntimeError(f"local submission checks failed for {stem}; see {receipt_path}")
    return checks


def verify_files(out_dir: Path, stem: str, foot_mask: np.ndarray | None = None,
                 expected_px: int | None = None) -> dict:
    """Read every file afresh and check the full local format contract and ZIP contents."""
    checks: dict[str, dict] = {}

    def rec(name, ok, detail=""):
        checks[name] = {"pass": bool(ok), "detail": str(detail)}

    template_profile, template_foot = _template()
    foot = template_foot if foot_mask is None else np.asarray(foot_mask, bool)
    rec("foot_mask_matches_pinned_template", foot.shape == template_foot.shape
        and np.array_equal(foot, template_foot), f"footprint pixels={int(foot.sum())}")
    expected_transform = template_profile["transform"]
    expected_crs = template_profile["crs"]
    p_nan = out_dir / f"{stem}-nan.tif"
    p_zero = out_dir / f"{stem}-zeros.tif"
    p_zip = out_dir / f"{stem}-nan.zip"

    arrays: dict[str, np.ndarray] = {}
    for path, outside_mode in ((p_nan, "nan"), (p_zero, "zero")):
        tag = path.name
        if not path.is_file():
            rec(f"{tag}:exists", False, "missing file")
            continue
        rec(f"{tag}:exists", True, f"{path.stat().st_size:,} bytes")
        try:
            with rasterio.open(path) as ds:
                arrays[tag] = _check_dataset(ds, tag=tag, foot=foot,
                    expected_transform=expected_transform, expected_crs=expected_crs,
                    expected_px=expected_px, outside_mode=outside_mode, rec=rec)
        except Exception as exc:  # format errors should be reported rather than masking other checks
            rec(f"{tag}:readable", False, f"{type(exc).__name__}: {exc}")

    if p_zip.is_file():
        rec("zip:exists", True, f"{p_zip.stat().st_size:,} bytes")
        try:
            with zipfile.ZipFile(p_zip) as z:
                names = z.namelist()
                tifs = [n for n in names if n.lower().endswith((".tif", ".tiff"))]
                exact = len(names) == 1 and len(tifs) == 1 and "/" not in tifs[0] and "\\" not in tifs[0]
                rec("zip:exactly_one_geotiff", exact, f"members={names}")
                if exact:
                    data = z.read(tifs[0])
                    try:
                        with MemoryFile(data) as mem, mem.open() as ds:
                            arr_zip = _check_dataset(ds, tag="zip:geotiff", foot=foot,
                                expected_transform=expected_transform, expected_crs=expected_crs,
                                expected_px=expected_px, outside_mode="nan", rec=rec)
                        if p_nan.name in arrays:
                            a = arrays[p_nan.name]
                            identical = a.shape == arr_zip.shape and np.array_equal(np.isnan(a), np.isnan(arr_zip)) \
                                and np.array_equal(np.nan_to_num(a), np.nan_to_num(arr_zip))
                        else:
                            identical = False
                        rec("zip:content_identical_to_nan_tif", identical)
                    except Exception as exc:
                        rec("zip:geotiff_readable", False, f"{type(exc).__name__}: {exc}")
        except (OSError, zipfile.BadZipFile) as exc:
            rec("zip:exactly_one_geotiff", False, f"{type(exc).__name__}: {exc}")
    else:
        rec("zip:exists", False, "missing file")
        rec("zip:exactly_one_geotiff", False, "ZIP not available")

    n_fails = sum(1 for c in checks.values() if not c["pass"])
    rec("__summary__", n_fails == 0, f"{len(checks)} checks, {n_fails} failures")
    return checks

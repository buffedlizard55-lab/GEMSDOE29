"""Strict, template-driven writer and independent verifier for DrivenData GEMS submissions.

Official format (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format):
same CRS (EPSG:32611), resolution (100 m) and bounds as the training data, "data outside the bounds is null
or nan", one ``float32`` layer with values between 0 and 1.

The reported portal error "Predicted values must be in range [0, 1]" on the first GEMSDOE25 file is
consistent with NaNs inside the owner-mirrored template footprint: 2,344,929 of its 5,167,373 template
pixels were NaN and 2.83 M pixels outside were finite. NaN fails every ``0 <= x <= 1`` test. The writer below
takes the footprint from the pinned owner-mirror template and refuses anything not finite in [0, 1] there.
This establishes consistency with the reported error, not organizer authentication of the mirrored template or validator.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

EXPECTED = dict(
    epsg=32611,
    shape=(3730, 3292),
    transform=(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    footprint_pixels=5_167_373,
    outside_pixels=7_111_787,
)


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_template(template_path: Path | str):
    with rasterio.open(template_path) as t:
        return t.profile.copy(), np.isfinite(t.read(1))


def write_submission(pred, template_path, out_path, *, outside: str = "nan") -> Path:
    """Write ``pred`` with the template's own raster profile.

    Inside the template footprint the prediction must be finite and within [0, 1] (nothing is silently
    clipped or filled). Outside it the pixels are NaN or 0.0 (``outside='zero'``, a separately-labelled
    fallback). Both conventions can be checked locally; no organizer acceptance of either file is asserted.
    """
    if outside not in ("nan", "zero"):
        raise ValueError("outside must be 'nan' or 'zero'")
    profile, footprint = read_template(template_path)
    pred = np.asarray(pred)
    if pred.shape != footprint.shape:
        raise ValueError(f"prediction shape {pred.shape} != template {footprint.shape}")
    v = pred[footprint]
    if not np.isfinite(v).all():
        raise ValueError(f"{int((~np.isfinite(v)).sum())} NaN/Inf pixels inside the template footprint")
    if (v < 0).any() or (v > 1).any():
        raise ValueError("predictions inside the footprint must lie in [0, 1]")
    arr = np.where(footprint, pred, np.float32(np.nan) if outside == "nan" else np.float32(0.0)).astype(np.float32)
    profile.update(driver="GTiff", dtype="float32", count=1, nodata=(np.nan if outside == "nan" else None))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(AREA_OR_POINT="Area")
    return out_path


def zip_single(tif_path: Path | str, zip_path: Path | str | None = None) -> Path:
    """Single-GeoTIFF ZIP (the portal accepts '.tif or a .zip containing a single GeoTIFF')."""
    tif_path = Path(tif_path)
    zip_path = Path(zip_path) if zip_path else tif_path.with_suffix(".zip")
    info = zipfile.ZipInfo(tif_path.name, date_time=(2026, 10, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, tif_path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(zip_path) as z:
        if z.namelist() != [tif_path.name] or z.read(tif_path.name) != tif_path.read_bytes():
            raise ValueError("ZIP does not exactly contain the single GeoTIFF")
    return zip_path


def check_file(path: Path | str, template_path: Path | str) -> dict:
    """Independent verification with plain rasterio against the template. Hard failures block upload."""
    path = Path(path)
    with rasterio.open(template_path) as t:
        tarr = t.read(1)
        tcrs, ttr, tshape, tprof = t.crs, t.transform, t.shape, t.profile
    foot = np.isfinite(tarr)
    with rasterio.open(path) as s:
        arr = s.read(1)
        masked = s.read(1, masked=True)
        crs, tr, shape, count, dtypes, nodata, prof = s.crs, s.transform, s.shape, s.count, s.dtypes, s.nodata, s.profile
    checks: dict[str, dict] = {}

    def add(name, ok, detail, hard=True):
        checks[name] = dict(pass_=bool(ok), detail=detail, hard=hard)

    tmpl_ok = (
        tcrs is not None and tcrs.to_epsg() == EXPECTED["epsg"] and tshape == EXPECTED["shape"]
        and tuple(ttr)[:6] == EXPECTED["transform"] and int(foot.sum()) == EXPECTED["footprint_pixels"]
    )
    add("template_matches_expected_grid_and_footprint", tmpl_ok, f"{tshape}, footprint {int(foot.sum()):,} px")
    add("single_band", count == 1, f"count={count}")
    add("dtype_float32", dtypes == ("float32",), f"dtypes={dtypes}")
    add("crs_epsg_32611", crs is not None and crs.to_epsg() == 32611 and crs == tcrs, str(crs.to_epsg() if crs else None))
    add("shape_matches_template", shape == tshape, f"{shape} vs {tshape}")
    add("geotransform_matches_template", tr == ttr, str(tuple(tr)[:6]))
    if shape == tshape:
        inside, outside = arr[foot], arr[~foot]
        fin = np.isfinite(inside)
        add("footprint_all_finite", fin.all(), f"{int((~fin).sum()):,} NaN/Inf inside the {int(foot.sum()):,}-px footprint")
        rng = bool(fin.any() and np.nanmin(inside) >= 0.0 and np.nanmax(inside) <= 1.0)
        add("footprint_values_in_0_1", rng, f"min={np.nanmin(inside) if fin.any() else None} max={np.nanmax(inside) if fin.any() else None}")
        add("outside_footprint_is_nan_official", bool(np.isnan(outside).all()), f"{int(np.isnan(outside).sum()):,}/{outside.size:,} NaN", hard=False)
        add("outside_footprint_is_nan_or_zero", bool((np.isnan(outside) | (outside == 0)).all()), "NaN (official) or 0 (fallback) outside", hard=True)
        add("nan_mask_identical_to_template", bool((np.isnan(arr) == ~foot).all()) or bool(np.isfinite(arr).all()),
            "NaN pixels exactly equal the template's NaN pixels (or none at all)", hard=True)
    else:
        for n in ("footprint_all_finite", "footprint_values_in_0_1", "outside_footprint_is_nan_or_zero", "nan_mask_identical_to_template"):
            add(n, False, "not evaluated: wrong shape")
        inside = outside = np.array([], np.float32)
    add("nodata_tag", True, f"nodata={nodata}", hard=False)
    # the variants a portal validator might use (information only, except the first two)
    add("variant_nan_aware_whole_array", bool(np.nanmin(arr) >= 0 and np.nanmax(arr) <= 1), "np.nanmin/np.nanmax over the whole array")
    add("variant_masked_read", bool(masked.compressed().min() >= 0 and masked.compressed().max() <= 1), "rasterio masked read")
    add("variant_strict_whole_array_no_nan", bool(((arr >= 0) & (arr <= 1)).all()),
        "((a>=0)&(a<=1)).all(): False for ANY NaN, including outside the owner-mirror template footprint", hard=False)
    same_profile = all(prof.get(k) == tprof.get(k) or (k == "nodata" and nodata is not None and np.isnan(nodata))
                       for k in ("driver", "dtype", "width", "height", "transform"))
    add("profile_matches_template", same_profile, f"compress={prof.get('compress')} (template {tprof.get('compress')})", hard=False)
    hard_fail = [k for k, v in checks.items() if v["hard"] and not v["pass_"]]
    out = dict(
        file=path.name, bytes=path.stat().st_size, sha256=sha256_file(path), ok_to_upload=not hard_fail,
        hard_failures=hard_fail, official_nan_outside=checks["outside_footprint_is_nan_official"]["pass_"] if shape == tshape else False,
        positive_pixels=int((inside > 0).sum()) if inside.size else 0,
        footprint_pixels=int(foot.sum()),
        checks={k: dict(pass_=v["pass_"], detail=v["detail"], hard=v["hard"]) for k, v in checks.items()},
    )
    return out


def content_id(pred, footprint, known) -> str:
    """12-hex digest of values in the project-defined scored subset (footprint minus the supplied ``known`` mask)."""
    pred, footprint, known = np.asarray(pred), np.asarray(footprint, bool), np.asarray(known, bool)
    v = np.asarray(pred[footprint & ~known], dtype="<f4").copy()
    v[v == 0] = 0
    return hashlib.sha256(v.tobytes()).hexdigest()[:12]


def make_filename(slug: str, date: str, cid: str, outside: str = "nan") -> str:
    s = "".join(c if c.isalnum() else "-" for c in slug.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return f"gemsdoe29-{s}-{date}-{cid}-{outside}.tif"


def make_note(tag: str, summary: str, cid: str, scored: str = "not yet live-scored", limit: int = 120) -> str:
    """Short DrivenData 'Note' (kept <= ``limit`` characters; the portal's own limit is not published)."""
    tail = f" | id {cid} | {scored}"
    head = f"GEMSDOE29 {tag} | "
    room = limit - len(head) - len(tail)
    if room < 8:
        raise ValueError("note too long for the configured limit")
    return head + summary[:room] + tail


def dump_json(obj, path) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, default=float) + "\n")

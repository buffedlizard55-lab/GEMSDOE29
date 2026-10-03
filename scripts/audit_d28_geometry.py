#!/usr/bin/env python3
"""Recompute the geometric facts behind the 0.2600 analysis (knowledge/07 §3) from the mirrored rasters.

Deterministic pixel arithmetic only — no models. The three dotted files are owner-mirrored rasters of the
H19-5 family; this receipt reproduces the emitted counts, catalogue overlap (must be 0), 8-neighbour
isolation, distance-to-catalogue distribution, and the *parent-mass kernel capture* arithmetic that
knowledge/07 uses to explain why fewer, better-placed dots scored higher under the published metric:

    captured(parent) = sum over parent pixels of k(distance to nearest child dot), k(d)=max(1-d/3, 0)
    credit_per_px    = captured / child emitted pixels

Owner-reported competition scores are NOT recomputed or restated as anything other than unverified claims
(see registry/score_claims.json). Writes evidence/d28_geometry.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import convolve, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "evidence" / "d28_geometry.json"

FILES = {
    "h19_5_parent": DATA / "h19_5_nan.tif",
    "d1_5": DATA / "dotted_h19_5_d1_5_nan.tif",
    "d2_8": DATA / "dotted_h19_5_d2_8_nan.tif",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_pred(path: Path, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as s:
        arr = s.read(1)
    return np.isfinite(arr) & (arr > 0) & foot


def main() -> None:
    for key, path in [("labels", DATA / "labels.tif"), ("template", DATA / "sample_submission.tif"), *FILES.items()]:
        if not path.is_file():
            raise SystemExit(f"missing {path}; run scripts/restore_data.py first")
    with rasterio.open(DATA / "labels.tif") as s:
        labels = s.read(1) == 1
    with rasterio.open(DATA / "sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    d_cat = distance_transform_edt(~labels)

    preds = {name: read_pred(path, foot) for name, path in FILES.items()}
    parent = preds["h19_5_parent"]
    report: dict[str, dict] = {}
    k3 = np.ones((3, 3), np.uint8)
    for name in FILES:
        pred = preds[name]
        n = int(pred.sum())
        nb = convolve(pred.astype(np.uint8), k3, mode="constant") - pred.astype(np.uint8)
        entry = dict(
            file=str(FILES[name].relative_to(ROOT)),
            sha256=sha256_file(FILES[name]),
            emitted_px=n,
            share_of_parent=round(n / max(int(parent.sum()), 1), 5),
            catalogue_overlap_px=int((pred & labels).sum()),
            mean_neighbour8=round(float(nb[pred].mean()), 4) if n else None,
            isolated_share=round(float((nb[pred] == 0).mean()), 6) if n else None,
            dist_to_catalogue_px={
                "median": round(float(np.median(d_cat[pred])), 3),
                "p10": round(float(np.percentile(d_cat[pred], 10)), 3),
                "p90": round(float(np.percentile(d_cat[pred], 90)), 3),
                "max": round(float(d_cat[pred].max()), 3),
            } if n else None,
        )
        if name != "h19_5_parent":
            dc = distance_transform_edt(~pred)
            captured = float(np.maximum(1.0 - dc[parent] / 3.0, 0.0).sum())
            entry["parent_kernel_captured_mass"] = round(captured, 3)
            entry["parent_kernel_captured_share"] = round(captured / max(float(parent.sum()), 1.0), 5)
            entry["credit_per_emitted_px"] = round(captured / max(n, 1), 4)
            del dc
        report[name] = entry
    payload = dict(
        generated_by="scripts/audit_d28_geometry.py",
        date="2026-10-03",
        kernel="triangular k(d) = max(1 - d/3 px, 0) at 100 m",
        note=("Deterministic geometry of the owner-mirrored dotted H19-5 family against the SUPPLIED catalogue "
              "and each other. This is not, and must never be presented as, a competition score; owner-reported "
              "scores remain unverified claims in registry/score_claims.json."),
        files=report,
    )
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2)[:1200])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

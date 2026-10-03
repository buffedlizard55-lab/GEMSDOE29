"""Official GDR 1391 INGENIOUS 2 m temperature probes, rasterised onto the competition grid.

Source (hash-verified locally 2026-10-03 against the 16GEMSDOE runner pin recorded by GEMSDOE27):
  zip 2m_temperature_probe_INGENIOUS_regional_data.zip, sha256 1301f70d230058e616ea5d34d1c7a32f...
  https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip
  landing page https://gdr.openei.org/submissions/1391 (CC BY 4.0 per page).

The archive's own README states: T2m = 2 m probe temperature; F2mDAB = "2m temperature normalized
to average background calculated for the specific area" — i.e. the *residualised* thermal anomaly,
which is exactly what prior session H27-2 proposed to build but could not fetch. We use the
provided residual rather than inventing our own background model.

Physical logic (Siler & Faulds, https://www.osti.gov/servlets/purl/1110515): in an extensional
amagmatic province, near-surface thermal anomalies require permeable pathways; a thermal anomaly
without a nearby mapped trace flags a high prior for an unmapped fault. A probe anomaly is not a
fault, and seasonal/background caveats in the README apply.
"""

from __future__ import annotations

import numpy as np

GRID = {"x0": 243350.0, "y_top": 4508550.0, "px": 100.0, "width": 3292, "height": 3730}


def load_probes(shp_path) -> dict:
    import shapefile
    r = shapefile.Reader(str(shp_path))
    names = [f[0] for f in r.fields[1:]]
    recs = r.records()
    col = {n: i for i, n in enumerate(names)}
    e = np.array([rec[col["UTM_E"]] for rec in recs], dtype=float)
    n = np.array([rec[col["UTM_N"]] for rec in recs], dtype=float)
    t2m = np.array([rec[col["T2m"]] if isinstance(rec[col["T2m"]], (int, float)) else np.nan for rec in recs])
    dab = np.array([rec[col["F2mDAB"]] if isinstance(rec[col["F2mDAB"]], (int, float)) else np.nan for rec in recs])
    ok = np.isfinite(e) & np.isfinite(n)
    x = (e[ok] - GRID["x0"]) / GRID["px"]
    y = (GRID["y_top"] - n[ok]) / GRID["px"]
    return {"col": x, "row": y, "t2m": t2m[ok], "dab": dab[ok], "n_records": int(len(recs)),
            "n_usable": int(ok.sum())}


def rasterise(probes: dict, valid: np.ndarray, radius_px: float = 6.0) -> dict[str, np.ndarray]:
    """Nearest-probe distance + IDW residual fields on the competition grid (inside footprint)."""
    H, W = valid.shape
    yy, xx = np.mgrid[0:H, 0:W]
    row = np.round(probes["row"]).astype(int)
    col = np.round(probes["col"]).astype(int)
    inside = (row >= 0) & (row < H) & (col >= 0) & (col < W)
    r0, c0, dab0, t0 = row[inside], col[inside], probes["dab"][inside], probes["t2m"][inside]
    keep = np.isfinite(dab0)
    r0, c0, dab0, t0 = r0[keep], c0[keep], dab0[keep], t0[keep]
    from scipy.spatial import cKDTree
    pts = np.column_stack([r0.astype(float), c0.astype(float)])
    tree = cKDTree(pts)
    q = np.column_stack([yy[valid].ravel().astype(float), xx[valid].ravel().astype(float)])
    d, j = tree.query(q, k=1)
    out = {}
    dist = np.full(valid.shape, np.inf, np.float32)
    dist[valid] = d.astype(np.float32)
    out["probe_dist_px"] = dist
    maxd = np.nan_to_num(dab0)[j]
    f = np.full(valid.shape, np.nan, np.float32)
    f[valid] = maxd.astype(np.float32)
    out["dab_nearest"] = f
    ft = np.full(valid.shape, np.nan, np.float32)
    ft[valid] = np.where(d <= 2.0, t0[j], np.nan).astype(np.float32)
    out["t2m_nearest_if_close"] = ft
    return out

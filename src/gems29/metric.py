"""Distance-weighted Tversky index (DTI), re-implemented from the official definition.

Official definition quoted from the DrivenData #306 problem page
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/, "Performance metric",
read 2026-10-03):

    k(d)  = (1 - d/R)+ = max(1 - d/300 m, 0)                     -> 3 px at 100 m
    TPw   = sum_{g in G} max_{x: d(x,g)<=R} p(x) * k(d(x,g))
    FPw   = sum_{x: p(x)>0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FNw   = sum_{g in G} [1 - max_{x: d(x,g)<=R} p(x) * k(d(x,g))]
    DTI   = TPw / (TPw + 0.2*FPw + 0.8*FNw + eps)

One behaviour is NOT specified in the cited public metric definition: whether predictions on
already-catalogued (known) pixels are excluded from credit and false-positive mass, with truth
masked there. The owner's sibling repositories historically inferred that convention from
unverified score comparisons, but those observations are not an official receipt and are not
reproduced here. This implementation exposes a `known` mask for catalogue-gap holdout experiments;
those values are explicitly local proxies and must not be presented as official scores. We keep the
mask explicit so both modes can be inspected. Structure and guards follow the sibling
re-implementation in
buffedlizard55-lab/GEMSDOE27 `src/gems27/metric.py` (credited), re-written here with an added
exhaustive brute-force cross-check test (tests/test_metric.py).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
EPS = 1e-7


def kernel_from_distance(d: np.ndarray) -> np.ndarray:
    return np.maximum(1.0 - d / RADIUS_PX, 0.0)


def _prep(pred, truth, valid, known):
    pred = np.asarray(pred)
    truth = np.asarray(truth, bool)
    if pred.shape != truth.shape or pred.ndim != 2:
        raise ValueError("pred/truth must be equal-shaped 2-D grids")
    valid = np.ones(pred.shape, bool) if valid is None else np.asarray(valid, bool)
    known = np.zeros(pred.shape, bool) if known is None else np.asarray(known, bool)
    active = valid & ~known
    vals = pred[active]
    if vals.size and (not np.isfinite(vals).all() or np.any((vals < 0) | (vals > 1))):
        raise ValueError("evaluated predictions must be finite probabilities in [0,1]")
    p = np.where(active & np.isfinite(pred), pred, 0.0)
    g = truth & active
    return p, g, active


def dti_exact(pred, truth, valid=None, known=None) -> dict[str, float]:
    """Exact DTI for soft predictions p in [0,1] (loops over the 3-px kernel footprint)."""
    p, g, _ = _prep(pred, truth, valid, known)
    n_truth = int(g.sum())
    H, W = p.shape
    yy, xx = np.nonzero(g)
    credit = np.zeros(n_truth)
    r = int(np.ceil(RADIUS_PX))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = max(1.0 - float(np.hypot(dy, dx)) / RADIUS_PX, 0.0)
            if k <= 0.0:
                continue
            ny, nx = yy + dy, xx + dx
            ok = (ny >= 0) & (nx >= 0) & (ny < H) & (nx < W)
            credit[ok] = np.maximum(credit[ok], p[ny[ok], nx[ok]] * k)
    tp = float(credit.sum())
    d_to_g = distance_transform_edt(~g) if n_truth else np.full(p.shape, np.inf)
    fp = float((p * (1.0 - kernel_from_distance(d_to_g))).sum())
    fn = n_truth - tp
    return {
        "TPw": tp, "FPw": fp, "FNw": fn, "n_truth": n_truth,
        "n_emitted": int((p > 0).sum()),
        "dti": tp / (tp + ALPHA * fp + BETA * fn + EPS) if n_truth else 0.0,
        "recall_w": tp / n_truth if n_truth else 0.0,
    }


def dti_binary(pred, truth, valid=None, known=None) -> dict[str, float]:
    """Exact DTI for a {0,1} prediction using Euclidean distance transforms (fast full-grid path)."""
    p, g, active = _prep(pred, truth, valid, known)
    pb = p > 0.5
    if np.any((p != 0) & (p != 1)):
        raise ValueError("dti_binary needs a {0,1} prediction; use dti_exact for soft values")
    n_truth = int(g.sum())
    if n_truth == 0:
        return {"TPw": 0.0, "FPw": float(pb.sum()), "FNw": 0.0, "n_truth": 0,
                "n_emitted": int(pb.sum()), "dti": 0.0, "recall_w": 0.0}
    if not pb.any():
        return {"TPw": 0.0, "FPw": 0.0, "FNw": float(n_truth), "n_truth": n_truth,
                "n_emitted": 0, "dti": 0.0, "recall_w": 0.0}
    d_to_p = distance_transform_edt(~pb)
    tp = float(kernel_from_distance(d_to_p[g]).sum())
    d_to_g = distance_transform_edt(~g)
    fp = float((1.0 - kernel_from_distance(d_to_g[pb])).sum())
    fn = n_truth - tp
    return {"TPw": tp, "FPw": fp, "FNw": fn, "n_truth": n_truth, "n_emitted": int(pb.sum()),
            "dti": tp / (tp + ALPHA * fp + BETA * fn + EPS), "recall_w": tp / n_truth}


def inclusion_threshold(dti: float) -> float:
    """Adding a pixel set raises DTI iff dTP/dFP > 0.2*DTI/(1 - 0.2*DTI).

    Derivation (from GEMSDOE27, re-verified here): with D = TP + 0.2*FP + 0.8*(|G|-TP) and
    DTI = TP/D, the marginal condition DTI' > DTI reduces to dTP/dFP > 0.2*DTI/(1-0.2*DTI).
    At DTI = 0.25 this break-even efficiency is 0.0526 credit-per-FP-pixel.
    """
    return ALPHA * dti / (1.0 - ALPHA * dti)


def marginal_gain(base, add, truth, valid=None, known=None) -> dict[str, float]:
    """(dTP, dFP) and DTI change from adding binary set `add` on top of binary `base`."""
    p0, g, active = _prep(np.asarray(base, float), truth, valid, known)
    a = np.asarray(add, bool) & active & (p0 == 0)
    b0 = p0 > 0.5
    n_truth = int(g.sum())
    if n_truth == 0:
        return {"dTP": 0.0, "dFP": float(a.sum()), "eff": 0.0, "dti_base": 0.0,
                "dti_union": 0.0, "n_added": int(a.sum())}
    d_g = distance_transform_edt(~g)
    k_pt = kernel_from_distance(d_g)
    c0 = kernel_from_distance(distance_transform_edt(~b0)[g]) if b0.any() else np.zeros(n_truth)
    u = b0 | a
    c1 = kernel_from_distance(distance_transform_edt(~u)[g]) if u.any() else np.zeros(n_truth)
    tp0, tp1 = float(c0.sum()), float(c1.sum())
    fp0 = float((1.0 - k_pt[b0]).sum())
    fp1 = float((1.0 - k_pt[u]).sum())

    def _dti(tp, fp):
        return tp / (tp + ALPHA * fp + BETA * (n_truth - tp) + EPS)

    d_tp, d_fp = tp1 - tp0, fp1 - fp0
    return {"dTP": d_tp, "dFP": d_fp, "eff": d_tp / d_fp if d_fp > 0 else float("inf"),
            "dti_base": _dti(tp0, fp0), "dti_union": _dti(tp1, fp1), "n_added": int(a.sum())}

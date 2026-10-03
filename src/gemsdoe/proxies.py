"""Registered spatial-proxy scoring shared by the file-level screens.

Two proxy targets, unchanged since session 2 and used identically by ``scripts/score_candidates.py`` and
``scripts/run_emission_sweep.py``:

1. ``catalogue_hidden`` — the repository's hide-and-recover proxy. For each of four quadrant folds and the
   two registered draws (20/21) the hidden catalogue components in the quadrant are the truth and the
   visible catalogue is masked out of the score. This is a *catalogue-gap* proxy, not new-fault truth.
2. ``sgmc_off_catalogue`` — state-geologic-map faults that are neither catalogue pixels nor within 300 m of
   one. Independent of the supplied catalogue by construction; its live-score relationship is
   peer-reported, not established here.

Neither target is the organizer's hidden expert label set and neither number is a competition score. The
module exists so that every file-level screen in this repository computes those two numbers the same way
(the H41 screen's ``sgmc_class`` is the same construction, kept there for frozen-protocol reasons).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, binary_erosion

from .holdout import Holdout
from .metric import dti_binary

FOLDS = (0, 1, 2, 3)
DRAWS = (20, 21)
DOMAIN_ERODE = 12
NEAR_LABEL_PX = 3


@dataclass
class ProxyContext:
    """Everything the two proxies need, loaded once per run."""

    foot: np.ndarray
    labels: np.ndarray
    sgmc_off: np.ndarray
    near_visible: np.ndarray
    holdout: Holdout


def read_binary(path: Path) -> np.ndarray:
    """A candidate/emission GeoTIFF as a boolean mask: finite and strictly positive."""
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0)


def load_proxy_context(data_dir: Path, *, hide_frac: float = 0.20) -> ProxyContext:
    """Load the footprint, catalogue, the off-catalogue SGMC class and the hide-and-recover holdout."""
    with rasterio.open(data_dir / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    labels = read_binary(data_dir / "labels.tif")
    with rasterio.open(data_dir / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgm = ds.read(1) > 0
    near = binary_dilation(labels, iterations=NEAR_LABEL_PX)
    sgmc_off = sgm & ~labels & ~near
    return ProxyContext(foot=foot, labels=labels, sgmc_off=sgmc_off, near_visible=near,
                        holdout=Holdout(foot, labels, hide_frac))


def score_mask(mask: np.ndarray, ctx: ProxyContext, name: str = "") -> dict:
    """Score one fixed binary emission on both registered proxies (no model fit, no randomness)."""
    mask = np.asarray(mask, bool)
    if mask.shape != ctx.foot.shape:
        raise ValueError(f"mask shape {mask.shape} does not match the template {ctx.foot.shape}")
    folds = {}
    for draw_seed in DRAWS:
        for fold in FOLDS:
            d = ctx.holdout.draw(fold, draw_seed)
            domain = binary_erosion(d.quadrant, iterations=DOMAIN_ERODE)
            truth = d.hidden_test & domain
            emit = mask & domain
            r = dti_binary(emit, truth, valid=domain, known=d.visible)
            folds[f"draw{draw_seed}_fold{fold}"] = dict(
                dti=float(r["dti"]), coverage=float(r["coverage"]), tp=float(r["tp"]), fp=float(r["fp"]),
                n_truth=int(r["n_truth"]), emitted=int(emit.sum()),
            )
    cat = np.array([v["dti"] for v in folds.values()])
    per_draw = {f"draw{ds}": float(np.mean([v["dti"] for k, v in folds.items() if k.startswith(f"draw{ds}")]))
                for ds in DRAWS}
    sg = dti_binary(mask, ctx.sgmc_off, valid=ctx.foot, known=ctx.labels)
    n = int(mask.sum())
    return dict(
        name=name or "candidate",
        catalogue_hidden_mean=float(cat.mean()),
        catalogue_hidden_per_draw=per_draw,
        catalogue_hidden_folds=folds,
        catalogue_hidden_folds_positive_vs_zero=float((cat > 0).mean()),
        sgmc_off_catalogue=dict(dti=float(sg["dti"]), coverage=float(sg["coverage"]), tp=float(sg["tp"]),
                                fp=float(sg["fp"]), n_truth=int(sg["n_truth"])),
        emitted_pixels=n,
        hug_share=float((mask & ctx.near_visible).sum() / max(n, 1)),
        on_catalogue_pixels=int((mask & ctx.labels).sum()),
    )


def paired_catalogue_hidden(mask: np.ndarray, reference: np.ndarray, ctx: ProxyContext) -> dict:
    """Per-cell catalogue-hidden DTI differences of ``mask`` minus ``reference`` on the same folds/draws."""
    deltas = {}
    for draw_seed in DRAWS:
        for fold in FOLDS:
            d = ctx.holdout.draw(fold, draw_seed)
            dom = binary_erosion(d.quadrant, iterations=DOMAIN_ERODE)
            truth = d.hidden_test & dom
            a = dti_binary(np.asarray(mask, bool) & dom, truth, valid=dom, known=d.visible)
            b = dti_binary(np.asarray(reference, bool) & dom, truth, valid=dom, known=d.visible)
            deltas[f"draw{draw_seed}_fold{fold}"] = float(a["dti"] - b["dti"])
    return dict(cells=deltas, mean=float(np.mean(list(deltas.values()))))

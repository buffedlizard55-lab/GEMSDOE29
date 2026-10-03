"""Hide-and-recover cell execution shared by the factorial, confirmation and candidate stages."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from .families import family_columns
from .features import build_catalogue_features, build_tip_continuation
from .holdout import Draw, Holdout
from .h30 import H30_PAIR_NAMES, build_paired_tip_bridge, build_scarp_persistence
from .metric import dti_binary
from .thinning import dot_thin, ridge_nms, select_top_positive

HGB_PARAMS = dict(
    max_iter=100, learning_rate=0.12, max_leaf_nodes=31, min_samples_leaf=50,
    l2_regularization=1.0, class_weight={0: 1, 1: 5}, early_stopping=False,
)
N_NEG = 300_000
BUDGET = 0.0245
DOT_MIN_DIST = 1.5
DOMAIN_ERODE = 12


@dataclass
class Context:
    foot: np.ndarray
    labels: np.ndarray
    static: np.ndarray  # (n_static, n_foot) memmap
    static_names: list
    addon: np.ndarray | None = None  # (5, n_foot) memmap from features.build_addons (optional)
    fi: np.ndarray = field(init=False)
    holdout: Holdout = field(init=False)
    scale: dict = field(init=False)
    h27_scarp: np.ndarray = field(init=False)
    h30_scarp: np.ndarray | None = field(init=False, default=None)
    h30_scarp_diag: dict | None = field(init=False, default=None)

    def __post_init__(self):
        self.fi = np.flatnonzero(self.foot.ravel())
        self.holdout = Holdout(self.foot, self.labels, 0.20)
        self.e_names = family_columns("E")
        self.extra_names = ["X1_K", "X1_ThK", "X1_UK", "X2_compat", "X2_compat_coh", "X3_gm", "X3_gd"]
        self.h27_names = ["H27_tip", "H27_scarp", "H27_tip_x_scarp"]
        self.h30_names = list(H30_PAIR_NAMES)
        self.all_names = (list(self.static_names) + list(self.e_names) + list(self.extra_names)
                          + list(self.h27_names) + list(self.h30_names))
        self.col = {n: i for i, n in enumerate(self.all_names)}
        rng = np.random.default_rng(1)
        sub = np.sort(rng.choice(self.fi.size, 200_000, replace=False))
        self.scale = {}
        for n in self.static_names:
            v = np.asarray(self.static[self.static_names.index(n), sub])
            v = v[np.isfinite(v)]
            lo, hi = (np.percentile(v, 1), np.percentile(v, 99)) if v.size else (0.0, 1.0)
            self.scale[n] = (float(lo), float(hi if hi > lo else lo + 1.0))

        required = ("L_step_max", "B_crest", "B_trough")
        if all(n in self.static_names for n in required):
            scaled = []
            for n in required:
                raw = np.asarray(self.static[self.static_names.index(n)], np.float32)
                lo, hi = self.scale[n]
                scaled.append(np.clip((raw - lo) / (hi - lo), 0.0, 1.0))
            step, crest, trough = scaled
            self.h27_scarp = np.nan_to_num(step * np.maximum(crest, trough), nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        else:
            self.h27_scarp = np.zeros(self.fi.size, np.float32)

    def ensure_h30_scarp(self) -> None:
        """Build H30's static composite only when an H30 cell actually needs it."""
        if self.h30_scarp is not None:
            return
        h30_required = ("L_step_max", "L_cross_max", "L_coh100")
        if all(n in self.static_names for n in h30_required):
            self.h30_scarp, self.h30_scarp_diag = build_scarp_persistence(self.static, self.static_names, self.scale)
        else:
            self.h30_scarp = np.zeros(self.fi.size, np.float32)
            self.h30_scarp_diag = {
                "missing_inputs": [n for n in h30_required if n not in self.static_names],
                "n_footprint_pixels": int(self.fi.size),
                "nonzero_fraction": 0.0,
                "max_value": 0.0,
            }

    def vec(self, mask: np.ndarray) -> np.ndarray:
        """Footprint-vector indices where ``mask`` is true."""
        return np.flatnonzero(mask.ravel()[self.fi])

    def columns(self, letters: str) -> list[int]:
        cols = []
        for L in letters:
            cols += [self.col[n] for n in family_columns(L)]
        return cols

    def named(self, names: list[str]) -> list[int]:
        return [self.col[n] for n in names]

    def nscale(self, name: str, v: np.ndarray) -> np.ndarray:
        lo, hi = self.scale[name]
        return np.clip((v - lo) / (hi - lo), 0, 1)


class Cell:
    """Everything shared by all runs of one (fold, draw): features, training sample, test matrix."""

    def __init__(self, ctx: Context, fold: int, seed: int, extras: bool = False, h27: bool = False,
                 h30: bool = False, h31: bool = False):
        if h27 and not extras:
            raise ValueError("H27 columns are appended after the add-on columns; set extras=True for aligned indices")
        if h30 and not (extras and h27):
            raise ValueError("H30 columns follow the H27 columns; set extras=True and h27=True for aligned indices")
        if h31 and not (extras and h27):
            raise ValueError("H31 columns follow the H27 columns; set extras=True and h27=True for aligned indices")
        if h31:
            if not hasattr(ctx, "h31_features") or not hasattr(ctx, "h31_names"):
                raise ValueError("H31 features must be loaded onto Context before requesting h31=True")
            if np.asarray(ctx.h31_features).shape != (len(ctx.h31_names), ctx.fi.size):
                raise ValueError("H31 feature cache must align with the Context footprint vector")
        self.ctx, self.fold, self.seed, self.extras, self.h27, self.h30, self.h31 = ctx, fold, seed, extras, h27, h30, h31
        t0 = time.time()
        self.draw: Draw = ctx.holdout.draw(fold, seed)
        d = self.draw
        if h30:
            ctx.ensure_h30_scarp()
        self.E = build_catalogue_features(d.visible, ctx.fi)
        self.tip = build_tip_continuation(d.visible, ctx.foot, ctx.fi) if h27 else None
        self.bridge = None
        self.bridge_diag = None
        if h30:
            self.bridge, self.bridge_diag = build_paired_tip_bridge(d.visible, ctx.foot, ctx.fi)
        rng = np.random.default_rng(777 + 31 * fold + seed)
        pos = ctx.vec(d.hidden_train)
        near = distance_transform_edt(~d.hidden_train) <= 1.5
        cand = ctx.vec(d.train_region & ~ctx.labels & ~near)
        neg = rng.choice(cand, size=min(N_NEG, cand.size), replace=False)
        self.train_idx = np.sort(np.concatenate([pos, neg]))
        self.y = np.isin(self.train_idx, pos).astype(np.int8)
        self.q = ctx.vec(d.quadrant)
        self.Xtr = self._gather(self.train_idx)
        self.Xq = self._gather(self.q)
        sl = d.bbox
        self.sl = sl
        self.domain = binary_erosion(d.quadrant, iterations=DOMAIN_ERODE)
        self.dom_c = self.domain[sl]
        self.truth_c = (d.hidden_test & self.domain)[sl]
        self.known_c = d.visible[sl]
        self.near_vis = distance_transform_edt(~self.known_c) <= 3
        self.K = int(round(BUDGET * self.dom_c.sum()))
        # AUC evaluation index sets (positions inside the quadrant vector)
        dq = self.domain.ravel()[ctx.fi][self.q]
        hq = (d.hidden_test & self.domain).ravel()[ctx.fi][self.q]
        cq = ctx.labels.ravel()[ctx.fi][self.q]
        self.auc_pos = np.flatnonzero(hq)
        neg_pool = np.flatnonzero(dq & ~cq)
        self.auc_neg = np.random.default_rng(5).choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
        self._grid = np.zeros(ctx.foot.shape, np.float32)
        self.prep_seconds = time.time() - t0

    def _gather(self, idx: np.ndarray) -> np.ndarray:
        ns, ne = self.ctx.static.shape[0], self.E.shape[0]
        n_extra = len(self.ctx.extra_names) if self.extras else 0
        n_h27, n_h30 = (3 if self.h27 else 0), (2 if self.h30 else 0)
        n_h31 = len(self.ctx.h31_names) if self.h31 else 0
        X = np.empty((idx.size, ns + ne + n_extra + n_h27 + n_h30 + n_h31), np.float32)
        gather_columns(self.ctx, self.E, idx, self.extras, out=X)
        j = ns + ne + n_extra
        if self.h27:
            tip = self.tip[idx]
            scarp = self.ctx.h27_scarp[idx]
            X[:, j] = tip
            X[:, j + 1] = scarp
            X[:, j + 2] = tip * scarp
            j += 3
        if self.h30:
            if self.bridge is None or self.ctx.h30_scarp is None:
                raise RuntimeError("H30 features were requested before their per-cell/static fields were initialized")
            X[:, j] = self.bridge[idx]
            X[:, j + 1] = self.ctx.h30_scarp[idx]
            j += 2
        if self.h31:
            h31 = self.ctx.h31_features[:, idx]
            X[:, j : j + len(self.ctx.h31_names)] = np.asarray(h31, dtype=np.float32).T
        return X

    # -------------------------------------------------------------------------------------
    def emit(self, score_q: np.ndarray, dotted: bool = True, min_dist: float = DOT_MIN_DIST, k: int | None = None):
        """Ridge NMS -> drop known -> top-K -> (dot thinning). Returns (binary crop, raw top-K crop)."""
        g = self._grid
        g[:] = 0
        g.ravel()[self.ctx.fi[self.q]] = np.nan_to_num(score_q, nan=0.0).astype(np.float32)
        s = g[self.sl]
        r = ridge_nms(s, self.dom_c, 1.0)
        sc = np.where(r & ~self.known_c, s, 0.0)
        top = select_top_positive(sc, self.dom_c, self.K if k is None else k)
        return (dot_thin(top, min_dist) if dotted else top), top

    def candidates(self, score_q: np.ndarray, k: int | None = None):
        """(score crop, top-K ridge candidates) before any dotting."""
        g = self._grid
        g[:] = 0
        g.ravel()[self.ctx.fi[self.q]] = np.nan_to_num(score_q, nan=0.0).astype(np.float32)
        s = g[self.sl].copy()
        r = ridge_nms(s, self.dom_c, 1.0)
        sc = np.where(r & ~self.known_c, s, 0.0)
        return s, select_top_positive(sc, self.dom_c, self.K if k is None else k)

    def evaluate(self, emitted_c: np.ndarray) -> dict:
        r = dti_binary(emitted_c, self.truth_c, valid=self.dom_c, known=self.known_c)
        n = int(emitted_c.sum())
        hug = float((emitted_c & self.near_vis).sum() / max(n, 1))
        return dict(dti=r["dti"], coverage=r["coverage"], tp=r["tp"], fp=r["fp"], n_truth=r["n_truth"], emitted=n, hug=hug)

    def auc(self, score_q: np.ndarray) -> float:
        if self.auc_pos.size == 0:
            return float("nan")
        idx = np.concatenate([self.auc_pos, self.auc_neg])
        y = np.concatenate([np.ones(self.auc_pos.size), np.zeros(self.auc_neg.size)])
        return float(roc_auc_score(y, np.nan_to_num(score_q[idx], nan=0.0)))

    # -------------------------------------------------------------------------------------
    def fit_predict(self, cols: list[int], seed: int = 0, params: dict | None = None):
        t = time.time()
        m = HistGradientBoostingClassifier(random_state=seed, **(params or HGB_PARAMS))
        m.fit(self.Xtr[:, cols], self.y)
        t_fit = time.time() - t
        t = time.time()
        p = m.predict_proba(np.ascontiguousarray(self.Xq[:, cols]))[:, 1].astype(np.float32)
        return p, dict(fit_s=t_fit, predict_s=time.time() - t)

    def unsupervised(self, names: list[str]) -> np.ndarray:
        """Mean of percentile-scaled raw features over the quadrant (NaN-aware): leak-free physics ridge."""
        ctx = self.ctx
        acc = np.zeros(self.q.size, np.float32)
        cnt = np.zeros(self.q.size, np.float32)
        for n in names:
            lo, hi = ctx.scale[n]
            v = np.clip((self.Xq[:, ctx.col[n]] - lo) / (hi - lo), 0, 1)
            ok = np.isfinite(v)
            acc[ok] += v[ok]
            cnt[ok] += 1
        return np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0).astype(np.float32)


def gather_columns(
    ctx: "Context", E: np.ndarray, idx: np.ndarray, extras: bool = False, out: np.ndarray | None = None
) -> np.ndarray:
    """Static + catalogue (E) (+ add-on) columns for footprint-vector indices ``idx``.

    ``out`` may be a larger preallocated matrix; only the base columns are written. This lets H27/H30 append
    per-cell features without repeated full-matrix concatenations on the 4 GB runner.
    """
    ns, ne = ctx.static.shape[0], E.shape[0]
    n_extra = len(ctx.extra_names) if extras else 0
    n_base = ns + ne + n_extra
    if out is None:
        X = np.empty((idx.size, n_base), np.float32)
    else:
        X = np.asarray(out)
        if X.ndim != 2 or X.shape[0] != idx.size or X.shape[1] < n_base or X.dtype != np.float32:
            raise ValueError("preallocated out must be float32 with matching rows and room for all base columns")
    X[:, :ns] = np.asarray(ctx.static[:, idx]).T
    X[:, ns : ns + ne] = E[:, idx].T
    if extras:
        if ctx.addon is None:
            raise ValueError("add-on columns requested but the add-on memmap is not loaded")
        a = np.asarray(ctx.addon[:, idx]).T  # X1_K, X1_ThK, X1_UK, S_dem_c2, S_dem_s2
        j = ns + ne
        X[:, j : j + 3] = a[:, :3]
        e = ns  # E column offsets: dist, cos2, sin2, dens5, dens20, dens50, coh20
        compat = a[:, 3] * X[:, e + 1] + a[:, 4] * X[:, e + 2]
        X[:, j + 3] = compat
        X[:, j + 4] = compat * X[:, e + 6]
        gh = ctx.nscale("A_grav_hg_ridge", X[:, ctx.col["A_grav_hg_ridge"]])
        mh = ctx.nscale("A_mag_hg_ridge", X[:, ctx.col["A_mag_hg_ridge"]])
        db = ctx.nscale("D_depth_base_grad", X[:, ctx.col["D_depth_base_grad"]])
        X[:, j + 5] = gh * mh
        X[:, j + 6] = gh * db
    return X


def load_context(work: Path) -> Context:
    foot = np.load(work / "bands" / "_footprint.npy")
    lab = np.load(work / "bands" / "_labels.npy")
    st = np.load(work / "static_ABCD.npy", mmap_mode="r")
    names = json.loads((work / "static_ABCD.npy.names.json").read_text())
    ad = work / "addons.npy"
    addon = np.load(ad, mmap_mode="r") if ad.exists() else None
    return Context(foot, lab, st, names, addon)

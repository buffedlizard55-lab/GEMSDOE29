#!/usr/bin/env python3
"""Build the H52 worming-filter candidate GeoTIFF (cross-fitted, leak-free, filter at emission).

Mechanism (frozen in ``knowledge/37``): train the habitat model exactly as the validated cells do
(``Cell(extras=True, h27=True)`` matrix, positives = ``draw.hidden_train``, <=300k negatives at >1.5 px,
``E`` built from ``draw.visible`` so no recovered component leaks into training), average the models'
whole-footprint probabilities, then run the frozen emission with the **worming survival veto** inserted
between the ridge/top-K selection and the dotting:

    ridge NMS -> drop catalogue pixels -> drop ``WF_SHALLOW_ONLY`` -> top K = 2.45 % -> dot_thin(2.4 px)

``WF_SHALLOW_ONLY`` is the label-free flag from ``src/gemsdoe/wormfilter.py``: a level-0 magnetic or
gravity edge whose gradient does **not** survive upward continuation (>= 25 % of its own level-0
modulus) at half of the 100-1200 m ladder. That is the brief's "a candidate that only exists at zero
continuation is exactly what the acquisition-artifact audit should already distrust", turned into a
number and applied as a filter.

Both variants are written by ``gems29.submission.write_submission`` (NaN-outside, zero-outside and the
one-TIFF ZIP, each read back and format-checked). The **zero-outside** file is the one to upload: a
strict whole-array ``[0, 1]`` check rejects NaN, which is the owner's reported
``Predicted values must be in range [0, 1]`` failure (``IR-PORTAL-01``).

    python3 scripts/build_wormfilter_candidate.py

Never contacts DrivenData.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_crossfit_candidate import assemble, base_column_names  # noqa: E402
from gems29.submission import write_submission as write_all_variants  # noqa: E402
from gemsdoe.experiment import HGB_PARAMS, N_NEG, load_context  # noqa: E402
from gemsdoe.features import build_catalogue_features, build_tip_continuation  # noqa: E402
from gemsdoe.paths import data_dir, work_dir  # noqa: E402
from gemsdoe.submission import content_id, make_note, sha256_file  # noqa: E402
from gemsdoe.thinning import dot_thin, ridge_nms, select_top_positive  # noqa: E402
from gemsdoe.wormfilter import WF_NAMES  # noqa: E402

K_FRAC = 0.0245
MIN_DIST_PX = 2.4
NMS_SIGMA = 1.0
NEG_BUFFER_PX = 1.5
CHUNK = 250_000
FOLDS = ("NW", "NE", "SW", "SE")
DEFAULT_DRAWS = (20, 21)  # the draws the H52 stage measured (knowledge/37); the artifact inherits them
FIELDS = ("wormfilter_fields.npy", "wormfilter_az_defined.npy", "wormfilter_fields.json")


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            return f"unavailable ({exc})"

    return dict(branch=run("branch", "--show-current"), revision=run("rev-parse", "HEAD"),
                dirty_worktree=bool(run("status", "--porcelain")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draws", default=",".join(str(d) for d in DEFAULT_DRAWS))
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "downloads")
    parser.add_argument("--record", type=Path, default=ROOT / "evidence" / "wormfilter_candidate_build.json")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    args = parser.parse_args()
    draws = tuple(int(d) for d in args.draws.split(",") if d.strip())
    if not draws:
        raise SystemExit("no draws given")
    if args.record.exists():
        raise SystemExit(f"refusing to overwrite {args.record}; move it aside first")

    data, work = data_dir(), work_dir()
    missing = [str(work / name) for name in ("static_ABCD.npy", "addons.npy", *FIELDS) if not (work / name).is_file()]
    if missing:
        raise SystemExit(f"missing caches: {missing}")
    ctx = load_context(work)
    vectors = np.load(work / FIELDS[0], mmap_mode="r")
    field_meta = json.loads((work / FIELDS[2]).read_text())
    if vectors.shape != (len(WF_NAMES), ctx.fi.size):
        raise SystemExit("cached worm fields do not match the footprint vector")
    shallow_vec = np.asarray(vectors[WF_NAMES.index("WF_SHALLOW_ONLY")], np.float32)
    shallow = np.zeros(ctx.foot.shape, bool)
    shallow.ravel()[ctx.fi] = shallow_vec > 0.5

    E_full = build_catalogue_features(ctx.labels, ctx.fi)
    tip_full = build_tip_continuation(ctx.labels, ctx.foot, ctx.fi)
    names = base_column_names(ctx, E_full)
    prob = np.zeros(ctx.fi.size, np.float64)
    cells: list[dict] = []
    for fold in range(len(FOLDS)):
        for seed in draws:
            d = ctx.holdout.draw(fold, seed)
            E_vis = build_catalogue_features(d.visible, ctx.fi)
            tip_vis = build_tip_continuation(d.visible, ctx.foot, ctx.fi)
            rng = np.random.default_rng(777 + 31 * fold + seed)  # identical to Cell.__init__
            pos = ctx.vec(d.hidden_train)
            near = distance_transform_edt(~d.hidden_train) <= NEG_BUFFER_PX
            cand = ctx.vec(d.train_region & ~ctx.labels & ~near)
            neg = rng.choice(cand, size=min(N_NEG, cand.size), replace=False)
            idx = np.sort(np.concatenate([pos, neg]))
            y = np.isin(idx, pos).astype(np.int8)
            Xtr = assemble(ctx, E_vis, tip_vis, idx, None)
            t0 = time.time()
            model = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
            model.fit(np.ascontiguousarray(Xtr), y)
            fit_s = time.time() - t0
            used: dict[str, int] = {}
            for stage in model._predictors:
                for predictor in stage:
                    for f in predictor.nodes["feature_idx"]:
                        used[names[f]] = used.get(names[f], 0) + 1
            del Xtr
            for start in range(0, ctx.fi.size, CHUNK):
                rows = np.arange(start, min(start + CHUNK, ctx.fi.size))
                Xq = assemble(ctx, E_full, tip_full, rows, None)
                prob[rows] += model.predict_proba(np.ascontiguousarray(Xq))[:, 1]
                del Xq
            cells.append(dict(fold=FOLDS[fold], fold_index=fold, draw=seed, train_rows=int(idx.size),
                              positives=int(y.sum()), columns=int(len(names)), fit_s=fit_s,
                              features_used=len(used),
                              top_features=sorted(used.items(), key=lambda kv: -kv[1])[:5]))
            print(f"fold={FOLDS[fold]} draw={seed}: fit {fit_s:.1f}s, {len(used)} features used, "
                  f"full-footprint prediction done", flush=True)
    prob = (prob / float(len(FOLDS) * len(draws))).astype(np.float32)

    score = np.zeros(ctx.foot.shape, np.float32)
    score.ravel()[ctx.fi] = prob
    ridge = ridge_nms(score, ctx.foot, NMS_SIGMA)
    scored = np.where(ridge & ~ctx.labels, score, 0.0)
    k = int(round(K_FRAC * int(ctx.foot.sum())))
    control_candidates = select_top_positive(scored, ctx.foot, k)
    control_emitted = dot_thin(control_candidates, MIN_DIST_PX)
    eligible = ridge & ~ctx.labels & ~shallow
    candidates = select_top_positive(scored, eligible, k)
    emitted = dot_thin(candidates, MIN_DIST_PX)

    n_dots = int(emitted.sum())
    if n_dots == 0:
        raise SystemExit("the worming-filter emission produced no dots")
    catalogue_overlap = int((emitted & ctx.labels).sum())
    if catalogue_overlap:
        raise SystemExit(f"emission overlaps {catalogue_overlap} catalogue pixels; refusing to package")
    if np.array_equal(emitted, control_emitted):
        raise SystemExit("degeneracy guard: the veto changed nothing, so this file would not implement its own method")

    cid = content_id(emitted, ctx.foot, ctx.labels)
    stem = f"gemsdoe29-wormsurv-filter-{args.date}-{cid}"
    note = make_note("worm-survival filter", "WF shallow-only veto at emission; cross-fitted", cid,
                     scored="proxy-only, not slot-cleared")
    checks = write_all_variants(emitted, args.out_dir, stem, note=note)

    record = dict(
        schema_version=1,
        built_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        stage="wormfilter_candidate",
        mechanism="cross-fitted habitat score + WF_SHALLOW_ONLY veto before top-K, then 2.4 px dotting",
        preregistration="knowledge/37_preregistered_wormfilter_h34protocol_2026-10-03.md",
        screen_evidence="evidence/wormfilter_screen/summary.json",
        draws=list(draws), folds=list(FOLDS),
        training=dict(matrix="static + E(draw.visible) + add-on extras + H27 (identical to Cell extras/h27)",
                      columns=int(len(names)), negatives_cap=N_NEG, neg_buffer_px=NEG_BUFFER_PX,
                      model="HistGradientBoostingClassifier(**HGB_PARAMS)"),
        emission=dict(ridge_nms_sigma_px=NMS_SIGMA, k=int(k), k_fraction=K_FRAC, min_dist_px=MIN_DIST_PX,
                      veto="WF_SHALLOW_ONLY removed from the eligible ridge set before top-K",
                      policy="top-K then deterministic geodesic dot thinning (frozen)"),
        worm_fields=dict(config=field_meta["config"], ladder=field_meta["ladder"],
                         level_detector=field_meta["level_detector"], survival_rule=field_meta["survival_rule"],
                         cache_sha256={name: sha256_file(work / name) for name in FIELDS},
                         shallow_fraction_footprint=float(shallow_vec.mean())),
        guard=dict(catalogue_overlap_px=catalogue_overlap, emitted_px=n_dots,
                   control_emitted_px=int(control_emitted.sum()),
                   veto_rate_on_candidates=float((control_candidates & shallow).sum() / max(int(control_candidates.sum()), 1)),
                   identical_to_control=False,
                   wf_columns_used_in_model=0,
                   note="the filter acts at emission, so no WF column enters the model by construction"),
        cells=cells,
        files={p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
               for p in (args.out_dir / f"{stem}-nan.tif", args.out_dir / f"{stem}-zeros.tif",
                         args.out_dir / f"{stem}-nan.zip") if p.is_file()},
        content_id=cid, stem=stem, note_to_paste=note,
        local_format_receipt=str((args.out_dir / f"checks-{stem}.json").relative_to(ROOT)),
        local_format_verified=bool(checks["__summary__"]["pass"]),
        recommended_upload=f"{stem}-zeros.tif",
        recommended_upload_reason="a strict whole-array [0,1] check rejects NaN (IR-PORTAL-01)",
        slot_approved=False,
        score_claims="none: no organizer score is claimed or implied for this file",
        environment=dict(python=platform.python_version(), numpy=np.__version__, platform=platform.platform()),
        git=git_state(), drivendata_contacted=False,
    )
    args.record.write_text(json.dumps(record, indent=2, default=float) + "\n")
    print(f"emitted {n_dots:,} dots (control without the veto: {int(control_emitted.sum()):,}); "
          f"veto rate on candidates {record['guard']['veto_rate_on_candidates']:.3f}")
    print(f"wrote {stem}-nan.tif / -zeros.tif / -nan.zip + checks-{stem}.json")
    print(f"upload the zero-outside file: {stem}-zeros.tif")
    print(f"note: {note}")
    print(f"record: {args.record.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

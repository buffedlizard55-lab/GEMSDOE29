# 24 — Preregistered H41 screen (slip-rate-weighted fault-corridor evidence), frozen 2026-10-03

Status: **frozen before implementation is exercised on real data.** Nothing in the parameter table, the arm
definitions, the gates or the draw assignment may be edited after the screen summary exists. A change of
intent is recorded as a dated amendment below with its own sha-pinned evidence file; the original text
stays.

## 1. Hypothesis and mode

The GDR 1391 INGENIOUS Quaternary fault inventory that underpins the USGS QFault data
(<https://gdr.openei.org/submissions/1391>) maps young traces the organizers' labels deliberately do not:
their mapping guidance (second-hand staff statements, `knowledge/07_metric_emission_analysis_2026-10-03.md`
§1) excludes *isolated range-front faults and short structures* while including *newly mapped geometry of
an existing system*. A trace that is (a) recent and slipping, and (b) far from anything in the visible
catalogue, is therefore positive evidence for the labelled class at exactly the place the competition
rewards, and it is the only free, official, static layer in this project that carries a **slip rate**
(mm/yr) and an **age bin** per object.

Mode of gain: prior-shape only. The metric is credit-density-limited (`knowledge/07` §5), so a new feature
can pay either by moving mass onto the ~2.4 % of pixels that become dots or by improving the *ranking*
inside a corridor. This screen measures the composite effect at the frozen emission budget.

Declared ceiling, stated before the run: the pinned mirror is an **attribute table with one grid centroid
per trace**, not geometry — 1,126 rows, 376 inside the footprint (verified this session, 2026-10-03).
A centroid plus a 2.5 km kernel cannot place a 300 m-kernel credit dot on a trace; it can only raise the
prior in its neighbourhood. Any arm that passes does so through corridor ranking near mapped young faults,
and any interpretation beyond that is out of scope for this screen.

Family lineage: `C_gdr_distance_to_active_fault` is distance only, no magnitude (`registry/hypotheses.json`,
family C); H37 used the *density* of young faults around **thermal springs** (`knowledge/15`) — a different
mechanism (fluid pathway), different weights (distance decay, not slip rate), different endpoints (springs,
not trace centroids). H41 is neither: it is slip-rate × recency weighted trace centroids with an
off-catalogue restriction and an anisotropic corridor. **No module in `src/` or `scripts/` reads the
qfaults attribute table for prediction** (verified by grep this session; it is only pinned in
`registry/data_manifest.json`).

## 2. Frozen inputs and parameters

Inputs (pinned in `registry/data_manifest.json`, hashes verified at restore time by
`scripts/restore_h31_data.py`; `data/` is gitignored so these are the audit anchors):

| input | sha256 | role |
|---|---|---|
| `data/external/gdr_qfaults_traces.csv` | `9702f2e5c382a4f472ae834d22b94990983b059677a37adfafd51c50f75e643c` (126,177 B) | 1,126 trace rows: `slip_rate`, `recency`, `map_scale`, `centroid_row/col`, `centroid_in_footprint` |
| `data/labels.tif` | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | label side; never read except through `Cell` visibility masks and the residual diagnostic |
| `data/sample_submission.tif` | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` | footprint and grid (3730×3292, 100 m, EPSG:32611) |
| `data/work/static_ABCD.npy` | `fe584a12ed3e1ed7d26b272c49f6da0bbe16e072d98f6b1694938d858305b084` | the 64-column cached static block (`scripts/prepare_data.py` + `scripts/build_features.py`) |
| `data/work/addons.npy` | see `data/work/addons.npy.names.json` | the cached S/G/E/H27 addons (`scripts/build_addons.py`) |

Grid convention: `(row, col)`, 1 px = 100 m, `x = 243350 + 100(col + 0.5)`, `y = 4508550 − 100(row + 0.5)`
(`src/gems29/paths.py`). The CSV's `centroid_row/centroid_col` are already grid indices — no reprojection,
hence no datum risk; the file's own UTM coordinates are not used.

Frozen parameters, implemented once in `src/gemsdoe/h41.py::H41_PARAMS`:

| name | value | rationale (declared, never re-tuned) |
|---|---|---|
| `decay_px` | 25.0 | 2.5 km exponential support length — the length scale at which a mapped Quaternary trace implies un-mapped continuation; matches the v3 spec `exp(-d/2.5 km)` |
| `cutoff_px` | 50.0 | kernel dropped beyond 2 × decay (5 km), keeping the build exact (patch accumulation, no FFT wrap) |
| `off_catalogue_min_px` | 5.0 | "off-catalogue" = centroid ≥ 500 m from every *visible* catalogue pixel; 500 m is one mapped-trace width and is coarser than the 100 m pixel, so it does not encode the holdout |
| `corridor_half_len_px` | 12.0 | ±1.2 km smear along the local strike: the median in-footprint clipped trace length is 7.1 km, so a half-length of 1.2 km smears each centroid to a ~2.4 km corridor, well inside one trace |
| `n_orientations` | 8 | 22.5° sampling of a mod-180° orientation |
| `purity_eps` | 1e-6 | numerical floor of the ratio |
| recency weights | `<150`:1.00, `<15,000`:0.80, `<130,000`:0.60, `<750,000`:0.40, `<1,600,000`:0.25, anything else 0.15 | judgement weights on the age bin, monotone in youth; the fallback counts unlisted/malformed bins |
| slip-rate term | `log1p(slip)/log1p(max slip in file)`, missing/non-positive → 0.25 | log scale because the file spans 1.47e-5…4.5 mm/yr; the 0.25 fallback is below the 99th-percentile-scaled weight of a real young trace so a missing rate cannot out-rank a measured one |
| weight | `clip(slip_term × recency / 1.0, 1e-6, 1)` | bounded in (0,1], draw-independent; median measured weight on the real file 0.0335, max 0.8 |
| `support_scale` | 99.9th percentile of the all-centroid support field, in-footprint only | fixed once per run before the fits, so arms share one normalization; measured 1.025 on the real file |

Strike source: the **local doubled-angle structure-tensor field of the existing H27 scarp composite**
(`ctx.h27_scarp`, `src/gemsdoe/experiment.py`, computed at grid resolution), reusing
`gemsdoe.h35._trace_grids` verbatim so angle conventions are identical to the H35 field family (σ=2 px,
0.5 px Gaussian, 3×3 tensor, 90–100th percentile clip, `(cos 2t, sin 2t)`). No catalogue geometry enters it.
Where the scarp composite has no local fabric the corridor falls back to the isotropic off-catalogue
support. The corridor is therefore *not* "along the trace strike" (the mirror carries no trace strike) —
it is along the geomorphic fabric of the scarp field, which is the honest description.

Degeneracy guard (pre-declared because H31 was defeated by exactly this): every arm's columns must be
nonzero on ≥ **0.2 %** of footprint pixels. Measured on the real file before any fit: the support field is
nonzero on 16.0 % of the whole grid (`H41_SUPP`), versus H31's worst measured 0.084 %; the guard is
reported in `design_screen.json` per column, and any violation aborts the stage with a recorded reason
rather than silently producing a null result.

## 3. Columns (5, all `float32`, [0,1], zero outside the footprint)

1. `H41_SUPP` — `Σᵢ wᵢ exp(-d(p,cᵢ)/2.5 km) / scale` over **all** in-footprint trace centroids.
2. `H41_OFF` — same sum restricted to centroids that are off-catalogue for this draw.
3. `H41_CORR` — `H41_OFF`'s point field smeared anisotropically ±1.2 km along the local scarp strike
   (orientation-weighted mean of 8 directional smears, weight `0.5(1+cos 2Δt)`), / `scale`.
4. `H41_OFF_SCARP` — `H41_OFF × h27_scarp` (corridor evidence co-located with a scarp crest/trough signal).
5. `H41_PURITY` — `H41_OFF / (H41_SUPP + ε)`: the fraction of local young-fault support the supplied
   catalogue does **not** already explain. This column is *not* a new data channel; it is a re-cut of 1 and
   2, admitted because the H34 lesson is that conditional/relative encodings beat raw ones.

Leakage rule (tested): `H41_*` is computed from the attribute table plus the *visible* catalogue grid; the
holdout pixels enter only through the off-catalogue mask, which **removes** information. The
`labels.tif ≡ existing_faults.tif` byte-identity (`sha256 7ba308cc…`) is recorded as an irregularity so
that nobody later mistakes the "near-catalogue" suppression for holdout-blindness.

## 4. Arms, cells, gates, draws

Arms are `C0_base` plus four additions; each is fit exactly as in `knowledge/19` (HistGB over
`[visible label, class prior, 64 static, 8 addons, E1, H27-2, 3 scarp, H41 block]`, n_estimators 100,
learning_rate 0.12, max_leaf_nodes 31, min_samples_leaf 50, l2 1.0, class_weight {0:1, 1:5}, 300k
negatives, fixed seeds).

| arm | H41 columns |
|---|---|
| `C0_base` | none |
| `A1_h41_off` | `H41_OFF, H41_PURITY` |
| `A2_h41_support` | `H41_SUPP, H41_OFF, H41_OFF_SCARP, H41_PURITY` |
| `A3_h41_corridor` | `H41_CORR, H41_OFF, H41_OFF_SCARP, H41_PURITY` |
| `A4_h41_union` | all five |

Cells: 4 blocked folds (NW/NE/SW/SE, `scripts/run_h35_screen.py` `FOLDS` geometry reused verbatim:
30 % folds, 10 % domain erosion, dilate-2 catalogue) × 2 draws × 5 arms = 40 cells;
`k_frac = 0.0245`, `min_dist_px = 1.5`, `BUDGET = 0.0245`, `DOT_MIN_DIST = 1.5`, `DOMAIN_ERODE = 12`.
Emission is the frozen H34 C0 chain (ridge NMS → drop visible → top-K → score-ordered Poisson-2.4 thinning);
the τ rule is not re-solved here, and both are evaluated only through the DTI proxy.

Draws: **28, 29** for the screen; **30, 31** for the confirmation. Seed policy is per cell
(`777 + 31*fold + seed`), the same as every GEMSDOE29 screen, so draws 0–27 remain untouched
(`knowledge/18` ledger; this family's own use is 24/25 screen, 26/27 confirmation, `knowledge/19`).

Gates, frozen (identical to `knowledge/19` so that the negative-streak arithmetic stays comparable):

- **G1 (screen, must hold for the confirmation to be run)** — per arm, mean ΔDTI vs `C0_base` over the
  8 cells ≥ **+0.005**; ≥ 3 of 4 folds positive in *each* draw; worst single-cell ΔDTI ≥ **−0.010**;
  emitted count within 0.75–1.25 × control in every cell. No second chance.
- **G2 (confirmation)** — same gates on draws 30, 31. Any arm passing G1+G2 advances to the pre-registered
  candidate-score step of `knowledge/23` (candidate score = 1.5 × screen mean ΔDTI, hard cap +0.030; a
  confirmation mean above +0.005 is additionally floored at +0.005).
- **Slot policy** — nothing may consume a weekly submission slot unless the resulting candidate's
  catalogue-hidden holdout proxy beats the current holdout best **0.14479018210246675**
  (`registry/status_feed.json`, `holdout_best`).

## 5. Deliverables and prohibitions

Stage deliverables: `evidence/h41_screen/{design_screen.json,cells_screen.jsonl,summary_screen.json,
analyzer_report_screen.json}` (and `_confirm` equivalents), generated by
`scripts/run_h41_screen.py` / `scripts/analyze_h41_screen.py`; the runner refuses a dirty worktree and
refuses to overwrite existing evidence.

Prohibited after the screen summary exists: re-tuning any parameter in §2, re-picking arms, moving
`min_nonzero_fraction` or the ±0.005 gate, dropping a fold/draw, or re-reading these numbers as anything
other than a proxy. Expected effect size, declared before the run: a well-motivated prior channel of this
kind, if real, should move the proxy by +0.005…+0.015; four sibling feature families have delivered
−0.014…+0.006 on identical gates (`knowledge/18`, `knowledge/21`), which is the base rate this screen is
being tested against.

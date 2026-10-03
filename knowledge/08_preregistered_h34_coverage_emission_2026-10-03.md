# H34 preregistration — metric-native coverage emission versus the frozen Poisson-disk control

**Frozen before any H34 run.** Date: 2026-10-03 (UTC). This file is written before
`scripts/run_h34_coverage_screen.py` is executed on real data. Nothing in it may be edited afterwards;
outcomes go in a separate dated note, and a failure is reported as a failure.

Context this hypothesis answers (see `knowledge/07_metric_emission_analysis_2026-10-03.md`): the metric's
TP term is a **maximum over predictions per truth pixel**
(`TP_w = Σ_g max_x p(x) k(d)`), so extra predicted pixels *adjacent to* an already-covering prediction add
no credit but do add `0.2 · (1 − k)` of false-positive mass, while every uncovered truth pixel costs `0.8`.
The historical emissions in this project's family are all distance-rule thinnings (`dot_thin`,
`score_ordered_dots`) — geometry heuristics that ignore the actual marginal trade-off of the metric.

## 1. Question

Holding the fitted model and the score field **exactly** fixed, does a residual-greedy *covering* emission
with an adaptive dot density (and a budget chosen from the metric's own marginal rule) beat the frozen
Poisson-disk control on the project's spatially blocked holdout?

This is an emission-geometry experiment, not a habitat/geology experiment. It cannot and does not claim to
find new faults; it claims only that the same field is placed better or worse under the official metric.

## 2. Design (frozen)

- **Folds:** the existing four spatial quadrants NW, NE, SW, SE (`gemsdoe.holdout`).
- **Draws:** fresh seeds **20 and 21**. Inventory of prior holdout draw seeds: 0–9 used on `main`,
  10–13 frozen for H31 (screen/confirm), 14–19 unused. 20–21 are new.
- **Model:** `HGB_PARAMS` exactly as registered elsewhere in this repository
  (`max_iter=100, learning_rate=0.12, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.0,
  class_weight={0:1,1:5}, early_stopping=False`), one fit per (fold, draw), trained on the base
  static A–D + catalogue-geometry E + X1–X3 add-ons + the visible-only `H27_tip` control column.
  No H31/worming features are used here.
- **Score field:** the fitted model's predicted probability on the test quadrant, identical bytes for
  all arms. Emission arms differ only in how that field is turned into a prediction raster.
- **Budget reference:** `K = round(0.0245 · |scored domain|)` and a 2.4-px minimum spacing, the frozen
  policy of the H31 registration; the domain is the quadrant eroded by 12 px and catalogue pixels are
  dropped, exactly as in the existing cell code.

### Arms (fixed order, all four run in every cell)

| Arm | Construction |
|---|---|
| `C0_ordered_dots` (**control**) | Hessian ridge NMS (σ=1.0) → drop visible catalogue → top-K (`K` as above) → `score_ordered_dots(score, candidates, 2.4)` |
| `C1_geodesic_dots` | same candidates → `dot_thin(candidates, 2.4)` (the older score-blind policy) |
| `C2_coverage_rule` (**primary candidate**) | `greedy_coverage` on the *continuous* ridge-NMS score field (radius 3.0 px, min separation 2.0 px, gain floor 0.02) with budgets `{N0, 1.5·N0, 2·N0, 3·N0}` where `N0` = the number of pixels `C0` emitted; the shipped budget is the one maximising the module's own `dti_hat` estimator |
| `C3_coverage_binary` | `greedy_coverage` on the *binary* top-K candidate mask, at exactly the budget `C2` chose (isolates continuous-field value from the covering geometry) |

`C2` is the registered primary candidate. `C1` and `C3` exist to separate two effects: score-blind vs
score-aware spacing (`C0` vs `C1`) and continuous vs binary prior (`C2` vs `C3`).

### Response

- **Primary:** exact masked catalogue-gap DTI inside the test quadrant
  (`Cell.evaluate`, the metric in `gemsdoe.metric` with `valid = domain`, `known = visible catalogue`).
- **Secondary (independent truth class):** the same emissions scored against
  `external/derived_sgmc_faults_100m_u8.tif` pixels that are **not** in the competition catalogue and not
  within 300 m of it (state-geologic-map faults absent from the Quaternary catalogue — a second,
  imperfect stand-in for “faults missing from the catalogue”). Reported as a paired mean over folds.
- Both are **proxies**. Neither is the organizer's hidden expert label set, and neither is a competition
  score.

### Gates (all must pass for the candidate to be called slot-eligible)

1. mean paired gain of `C2` over the per-fold best control (`C0`/`C1`, 2-draw mean) across the four
   spatial blocks **> +0.001 DTI**;
2. positive paired gain in **≥ 3 of 4** blocks;
3. no block worse than **−0.010 DTI**;
4. budget sanity: `C2` emits **≤ 3×** the pixel count of `C0`, and every emitted pixel lies inside the
   scored domain;
5. all cells present, finite, and bounded in `[0, 1]` where emitted.

### Decision rules

- Any gate failure ⇒ report the negative result, keep no new artifact as a submission candidate, and do
  not describe the method as an improvement.
- All gates pass ⇒ the winning emission may be applied to the group's best live-scored **habitat**
  (the H19-5 detector surface, whose parent scored an owner-reported 0.1922 and whose dotted transform
  scored an owner-reported 0.2477) to build one new, clearly-labelled GeoTIFF. That file is *not*
  slot-approved by this experiment: it still requires the format audit, the honest label that the
  habitat is unchanged and the live score unverified, and the owner's own decision to spend a slot.
- No post-hoc addition or removal of arms, no threshold tuning after seeing results, no re-running with
  different seeds to obtain a pass.

## 3. What this cannot establish

- It cannot measure new-fault discovery skill: both proxies are catalogued-fault surrogates.
- It cannot predict the leaderboard delta of the emission change; the H28 model in the sibling project
  (conditional on unverified owner-reported anchors) is the only available bridge, and it is a model,
  not a receipt.
- It cannot validate the habitat; a pass is about geometry only.

## 4. Immutability

Code paths used: `src/gemsdoe/coverage.py`, `src/gemsdoe/thinning.py`, `src/gemsdoe/holdout.py`,
`src/gemsdoe/experiment.py`, `src/gemsdoe/metric.py`, `scripts/run_h34_coverage_screen.py`. The runner
records the Git revision, the restored-input SHA-256 values and the wheel/library versions into
`evidence/h34_coverage_screen/design.json` before fitting, and refuses to overwrite a non-empty evidence
directory.

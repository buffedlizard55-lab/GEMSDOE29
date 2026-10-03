# Preregistration — H35 structural-interaction zones & H40 dense continuation persistence (session 3)

**Frozen:** 2026-10-03 (UTC), before any model fit on competition data for these arms and before the H40
feature cache is built. `scripts/build_h40_features.py` and `scripts/run_h35_screen.py` refuse to run without
this file; the runner records this file's SHA-256 and the source hashes into its `design.json`.
Nothing in this document was informed by any fit on real data: the only runs performed before freezing are
synthetic unit tests (`tests/test_h35_h40_features.py`) and a feature-construction smoke test on the full
owner-mirror catalogue (build time and density invariants only; no model, no score, no emission).

## 0. Scope and honesty boundary

This is a **spatially blocked hide-and-recover proxy** screen. Its response is the masked DTI of an emission
against *hidden catalogue components* (catalogue-gap proxy) plus a secondary state-geologic-map (SGMC)
off-catalogue class. **Neither is the organizer's hidden expert-label metric; no result here is, or may be
presented as, a competition score.** Historical score numbers from owner reports are not used as targets,
gates, or anchors anywhere in this experiment. The competition rasters are hash-pinned owner mirrors, not
organizer-authenticated downloads (`registry/irregularities.json` IR-DATA-01).

## 1. Research questions

* **H35** (ranked first in `knowledge/10_candidates_v2_2026-10-03.md`): do explicit structural
  interaction-zone objects — relay-ramp tip pairs inside a step window, transverse orientation
  disturbances, and tip-cluster density, optionally weighted by Andersonian dilation tendency and
  corroborated by scarp/potential-field ridges — add predictive support for faults the catalogue is
  missing, beyond the frozen control matrix?
* **H40** (the fix diagnosed by the H31 failure, `knowledge/16_h31_screen_results_2026-10-03.md`): does
  a **dense, continuous** upward-continuation persistence surface (the "worming" idea of Hornby,
  Boschetti & Horowitz 1999, doi:10.1111/j.1365-2478.1999.ggg031.x, re-expressed as a per-pixel persistence
  fraction rather than a binary seed-track set) add support where the sparse seed tracks could not?

Mechanism claims being tested: an edge that persists across continuation heights (0–1200 m ladder)
is attributed to a deeper equivalent source and trusted; an edge present only at zero continuation is a
shallow/cultural/acquisition-line artifact and is distrusted. Interaction-zone habitat claims follow
Faulds, Hinz & Kreemer (GDR 383) and Giddens & Faulds (2025): step-overs/relay ramps host ~32–47 % of
Great Basin geothermal systems while range-front faults host ~1 %; the catalogue traces through-going
strands and misses short overlapping ones.

## 2. Arms (one model per cell; same training sample, seeds, and emission; column sets differ)

Base matrix P0 = the frozen H34 control matrix: static families A–D + catalogue family E + the seven
add-on extras + the three H27 tip/scarp columns (`Cell(ctx, fold, draw, extras=True, h27=True)`), i.e.
exactly the arms' control of the H34 screen (`knowledge/08_...md`, `evidence/h34_coverage_screen/`).

| arm | added columns | source of columns |
|---|---|---|
| `C0_base` | — (control) | P0 only |
| `A1_h35_struct` | `H35_RELAY`, `H35_RELAY_TD`, `H35_JUNCTION`, `H35_TIPDENS` | `src/gemsdoe/h35.py::build_interaction_zone_fields` on the draw's **visible** catalogue only (per cell) |
| `A2_h35_corrob` | A1's four + `H35_RELAY_TD_X_SCARP` (× H27 scarp composite) + `H35_RELAY_TD_X_PFG` (× sqrt of percentile-scaled mag·gravity hg-ridges) | per cell |
| `A3_h40_persist` | `HP_MAG`, `HP_GRAV`, `HP_MIN`, `HP_DEEP` | static cache `work/h40_dense_persistence.npy` (`src/gemsdoe/dense_persist.py`; no labels used) |
| `A4_union` | A2 + A3 columns (8 added) | per cell + cache |

Frozen construction constants (no post-run tuning is permitted):

* H35: `sigma3_azimuth_deg = 105.0` (Bellier & Zoback 1995, doi:10.1029/94TC00596: WLZ normal-faulting
  σ3 mean N85±9°W ≡ 95°; strike-slip regime N65–70°W ≡ 110–115°; midpoint), `dip = 60°`, `r2 = 0.85`,
  `r3 = 0.60`; relay window: step width 3–25 px (0.3–2.5 km), tip separation 4–30 px (0.4–3.0 km),
  sub-parallel ≤ 25°, facing cos ≥ 0.5, corridor weight exp(−dist/20 px), 2-px buffer; junction:
  >45° doubled-angle orientation change within 3 px (Chebyshev radius 2), Gaussian σ=1, 99.9-pct
  normalisation; tip density: Gaussian σ=10 px, 99.5-pct normalisation. Known semantics, declared up
  front: `H35_JUNCTION` is an orientation-**disturbance** field (it fires at bends, junctions, and facing
  en-echelon tips where tensors merge within smoothing; it is not a pure crossing counter), and Siler 2022
  (DOI 10.5066/P9YL58W6) reports dilation tendency is nearly regime-invariant across this region — the TD
  column is a documented soft weight, expected to move rankings little.
* H40: continuation ladder (0, 100, 200, 400, 800, 1200 m) with the frozen H31 `WormConfig` (FFT
  preparation: 128-px reflect pad, 64-px cosine taper, 16-px boundary guard, 90th-pct gradient-ridge
  threshold, 2-px match tolerance); persistence fraction = (#heights with a thresholded |∇| ridge within
  tolerance)/6 over the safe region; `HP_DEEP` = (#heights ≥ 400 m)/3; Gaussian σ=1 px smoothing; clip
  [0,1]. Fields: band 02 `rtp`, band 13 `iso_grav_anom`.

Model: `HistGradientBoostingClassifier` with the frozen `HGB_PARAMS` (max_iter 100, lr 0.12, 31 leaves,
min_samples_leaf 50, l2 1.0, class_weight {0:1, 1:5}, no early stopping), `random_state = draw`, training
sample = `hidden_train` positives + ≤300,000 non-catalogue negatives >1.5 px from any hidden component
(the frozen `Cell` procedure — the model never sees the test quadrant or its 1.5 km collar).

Emission (identical for every arm): Hessian ridge NMS σ=1.0 → zero on visible-catalogue pixels → top
K = round(0.0245 × domain pixels) → score-ordered Poisson-disk dots at 2.4 px (the frozen C0 protocol).
Evaluation: exact masked DTI on `hidden_test ∧ eroded domain` (`src/gemsdoe/metric.py`) and the SGMC class
(state-map faults minus catalogue minus 300 m dilation), same as the H34 runner.

## 3. Data and fold protocol

Four spatial quadrants (folds 0–3 = NW/NE/SW/SE of the footprint split at the median row/col), hide_frac
0.20 of catalogue components. **Screen draws 24 and 25** (draws 0–13 used by earlier main/H31/H29 runs,
14–15 factorial, 20–21 H34/C0; these two are unused). **Confirmation draws 26 and 27**, fit only if an arm
passes the screen gate on both screen draws. No other seeds. Restored inputs must verify all manifest
SHA-256 pins first; the runner aborts otherwise.

## 4. Frozen gates (checked by code, from `evidence/h35_h40_screen/cells.jsonl` only)

Per arm (each of A1–A4 independently):

* **G1 screen**: mean paired ΔDTI vs `C0_base` (per fold, averaged over the two draws' per-fold means)
  ≥ **+0.005**, and ≥3/4 folds positive on **both** draws, and worst fold mean paired ΔDTI ≥ −0.010.
* **G2 confirmation** (only if G1): same thresholds on draws 26+27.
* **G3 slot eligibility** (only if G1+G2): the arm's 8-cell screen mean DTI **and** its 8-cell confirmation
  mean both exceed the current comparable spatial-holdout best `0.14479` (H34 C1,
  `evidence/h34_coverage_screen/summary.json`), and the SGMC secondary gain vs C0 is positive on ≥3/4
  folds on both screens (entry rule from `knowledge/10_candidates_v2_2026-10-03.md`).
* **Sanity**: all cells present (folds × draws × arms), all finite; emission budget within ±25 % of C0's
  emitted count per cell (a guard against winning by emitting more); `visible`-only feature provenance
  asserted in code.

If G1 fails for every arm, no confirmation is run, nothing is promoted, and the negative result is
published as-is. Proxy PASS ≠ live evidence; a slot may only be *considered by the owner* after all gates.

## 5. Pre-declared interpretation forks and falsifiers

* A1 gains concentrated in one fold or one draw → treated as noise; G1 requires both draws.
* `H35_RELAY` nonzero on <0.1 % of the footprint after visible-masking (H31's sparsity pathology) → arm is
  declared *inert by construction*, not "tested and negative"; the smoke test on the full catalogue showed
  3.07 % density, so this fork is not expected to fire; per-draw visible sets are ~80 % of that.
* Any arm beating C0 on catalogue-hidden DTI while SGMC gain is negative on ≥3/4 folds → reported as a
  proxy conflict (pattern registered as IR-29-PROXY-CONFLICT); no promotion.
* H40 persistence on this grid previously showed E-W (survey-line-parallel) edges to be the *most*
  persistent strata (H29 diagnostic) — the frozen ladder therefore cannot be described as a pure artifact
  filter; it is tested as a depth-proportionality prior and this caveat travels with any result.
* Post-freeze amendments: any change to constants, arms, gates, or draws requires a dated amendment section
  appended BEFORE the affected run, with the reason; silently re-running with changed constants is
  prohibited.

## 6. Sources for manual review (all verified 2026-10-03 unless marked)

* Hornby, Boschetti & Horowitz 1999 (multiscale wavelet edge detection / "worms"),
  <https://doi.org/10.1111/j.1365-2478.1999.ggg031.x>
* Bellier & Zoback 1995, Walker Lane stress, <https://doi.org/10.1029/94TC00596>
  (free copy: <https://digitalcommons.unl.edu/usgsstaffpub/472/>)
* Faulds, Hinz & Kreemer — GDR submission 383 geothermal play-fairway studies
  (<https://gdr.openei.org/submissions/383>); Giddens & Faulds 2025, Stanford SGW
  (<https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf>) — as cited by
  `knowledge/10_candidates_v2_2026-10-03.md` (link check for this document's fetch was blocked in the
  sandbox; citations descend from the prior session's verified review).
* Siler 2022 slip/dilation-tendency map, USGS, DOI <https://doi.org/10.5066/P9YL58W6> (metadata verified
  2026-10-03 per `registry/sources.json`; file unreachable from sandbox)
* DrivenData GEMS problem page (metric & scoring), transcribed in
  `registry/submission_contract.json` from <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
  (page text reviewed manually on 2026-10-03; no programmatic leaderboard access).
* Prior-session internal: `knowledge/16_h31_screen_results_2026-10-03.md` (sparsity failure diagnosis),
  `knowledge/09_h34_results_2026-10-03.md` (control protocol + holdout best),
  `knowledge/14_factorial_results_2026-10-03.md` (families B/E support).

## 7. Planned outputs (written by scripts only)

`evidence/h35_h40_screen/{design.json,cells.jsonl,summary.json}` (never overwritten), plus
`work/h40_dense_persistence.npy(.names.json,.metadata.json)` (ignored), a results document
`knowledge/21_h35_h40_results_2026-10-03.md`, registry updates (`hypotheses.json` statuses, `status_feed`,
`candidate_scoreboard`), and — only on full gate pass — a built candidate artifact with format receipts.

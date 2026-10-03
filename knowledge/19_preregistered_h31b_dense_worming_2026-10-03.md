# H31b preregistration — dense continuous worming persistence fields (magnetic + gravity)

**Base design frozen before implementation.** Date: 2026-10-03 (UTC). This preregistration
follows the owner's standing brief (README "Standing brief — current session"), which asks for
multiscale potential-field worming (upward continuation + horizontal-gradient-magnitude edge
strength; persistence with height as an explicit feature or filter) applied to the two independent
potential-field layers in the stack (gravity, magnetic), including the FFT/vertical-integration
route from magnetic TMI to pseudogravity, and validated on the spatially-blocked holdout before
any weekly slot is spent. It supersedes nothing: the failed H31 (sparse binary tracking,
`knowledge/16`) and H29 (raw worming, five arms failed) screens remain closed negatives. No
DrivenData leaderboard, forum, data, or submission endpoint is accessed by this experiment.

## 1. Why H31 failed, and the single structural change

H31 recorded persistence only at the **0-m local-maximum seed pixels** that re-matched at each
height; its cache was nonzero on 0.001–0.084 % of the 5,167,373-px footprint
(`knowledge/16_h31_screen_results_2026-10-03.md`). In 8/8 screen cells every worming arm emitted
pixel-identical dots to its control: a HistGradientBoosting head over 300,000 negatives cannot
move a top-2.45 % ridge emission from a column that is zero almost everywhere.

H31b changes exactly one thing: the persistence observation is **dense and continuous in space**.
For *every* footprint pixel we record, at each continuation height, whether the horizontal-gradient
modulus (HGM) there clears a per-height scale threshold, and aggregate across heights. The result
is a 12-column cache whose values are nonzero over a large fraction of the footprint, so the model
head can actually rank pixels by persistence. The spectral preparation, height ladder, threshold
percentile, and all holdout machinery are unchanged from the frozen H31 design and the existing
repository code.

Nothing in this design is tuned after outcomes; the gate below is evaluated once, on fresh draws.

## 2. Inputs, provenance, and leak audit

- Bands: `rtp` (reduced-to-pole magnetic anomaly, band 2 of the 19-band owner-mirror stack) and
  `iso_grav_anom` (isostatic gravity anomaly, band 13), from the hash-pinned
  `training_features.tif` (sha256 `4371c82e3b83…`, 418,912,844 bytes,
  `registry/data_manifest.json`). Both are the two independent potential-field layers named in
  the owner brief; no label, catalogue, well, spring, or held-out target enters feature
  construction.
- Grid: 3292×3730, EPSG:32611, 100 m, footprint 5,167,373 px (`src/gems29/paths.py` constants,
  verified against the restored template in `scripts/prepare_data.py`).
- Pseudogravity route: per the owner brief and the documented FFT/vertical-integration method
  (SEG 2014 abstract
  [10.1190/segam2014-1323.1](https://library.seg.org/doi/10.1190/segam2014-1323.1); Seequent
  `fft2con` manual documents RTP as a valid input at inclination 90°), the magnetic branch
  `W_PSG_*` is built from a **regularized vertical-integration pseudogravity proxy**
  `P(k) = R(k)/max(k, k_floor)` of the mean-removed, tapered, padded `rtp` spectrum — the same
  operator as H31's `pseudogravity_vertical_integration=True` path. It is a proxy, not a
  vendor-exact GPSD filter (no flight-date, true-field, density, or remanence metadata exists for
  the delivered grid). The branch `W_RTP_*` applies the identical ladder directly to `rtp`, so
  the screen also isolates whether the integration route itself matters.
- Gravity branch `W_GRAV_*` uses `iso_grav_anom` directly (it is an isostatic anomaly, not a
  Bouguer anomaly; worm positions on it are scale-space edge locations, not source depths).
- No DrivenData content is fetched, viewed, or copied by any step of this experiment.

## 3. Frozen feature construction (family W, 12 columns)

Spectral preparation (identical to H31, `src/gemsdoe/worms.py::_prepare_spectrum`): nearest
finite-value fill only as an FFT boundary condition; mean removed; cosine taper reaching zero
over 64 px toward the footprint boundary; 128-px reflect padding; zero-frequency coefficient
removed; `k_floor = 2π/(min(height,width)·100 m)`.

**Boundary-integrity amendment (frozen here before any fit):** the taper itself is an artificial
field edge and produces spurious HGM rings up to `taper_px` = 64 px inside the footprint.
Therefore all twelve W columns are **zero within 68 px (taper_px + 4) of the footprint boundary**
(a margin-zero band), and the per-height p90 scale thresholds and the (1,99) amplitude scalings
are computed over the interior domain (pixels ≥ 68 px from the boundary) only. The 16-px guard
of the spectral preparation is retained for diagnostics. This costs a fixed boundary margin
(≈9.2 M px, ~18 % of the footprint perimeter band) and makes the remaining values free of the
taper artifact; nothing inside the interior band depends on the FFT boundary condition.

For each branch input field `F` ∈ {`rtp`, `P(rtp)` pseudogravity proxy, `iso_grav_anom`} and each
continuation height `h` ∈ **0, 100, 200, 400, 800, 1,200 m** (the frozen H31 ladder), apply the
harmonic upward-continuation filter `exp(−2π k h)` to the precomputed spectrum, inverse
transform, and compute the horizontal-gradient modulus `E_h = |∇F_h|` with `np.gradient` at
100 m spacing. Let `safe` be the H31 safe domain (finite footprint ≥ 16 px from the boundary).

**Column mask convention (frozen here before any fit):** a W column carries its value where the
corresponding input band is finite and ≥ 68 px from the footprint boundary; it is **exactly 0**
in the 68-px margin band and outside the template footprint; and it is **NaN where the input
band is nodata** (the A-family re-masking convention; HistGradientBoosting consumes NaN natively
as a missing-value split, so the model can route "no magnetic data here" distinctly from "no
edge here"). The per-height p90 thresholds and the (1,99) amplitude scalings are computed over
**observed** interior pixels only (finite input, ≥ 68 px from the boundary), never over the
nearest-filled FFT boundary regions.

Per-branch columns (4 each, 12 total), all float32:

| Column | Definition |
|---|---|
| `W_<B>_FRAC` | **(primary dense-persistence column)** fraction of the five *upward* heights {100, 200, 400, 800, 1200} at which `E_h(x) ≥ q_h`, where `q_h` is the 90th percentile of `E_h` over the `safe` domain at that height. Values in {0, 0.2, …, 1}. |
| `W_<B>_LAST` | deepest surviving height at x divided by 1200 (0 if no upward height survives): `max{h : E_h(x) ≥ q_h}/1200`. |
| `W_<B>_E0` | `E_0(x)` scaled by the (1st, 99th) percentiles of `E_0` over `safe`, clipped to [0, 1] — level-0 edge amplitude. |
| `W_<B>_DEEP` | `E_1200(x)` scaled by the (1st, 99th) percentiles of `E_1200` over `safe`, clipped to [0, 1] — deep-ladder edge amplitude (shallow noise dies; deep sources keep finite amplitude). |

`<B>` ∈ {`RTP`, `PSG`, `GRAV`}. The 90th-percentile scale threshold follows H31's
`edge_percentile = 90` convention; it ranks edge locations within each scale and is not a
cross-scale amplitude comparison. Diagnostics recorded in the cache metadata: input band
SHA-256, code revision, config, per-height `q_h`, per-column nonzero/finite fractions over the
footprint, and output cache SHA-256. The cache is regenerable and lives in the ignored work
directory; the evidence directory is refused if nonempty.

## 4. Paired spatial design

- **Screen:** holdout draw seeds **22 and 23** (fresh; the inventory in
  `knowledge/02_preregistered_h31_worming_2026-10-03.md` §1 lists seeds 0–13 as used/reserved,
  14/15 by the factorial confirmation, 20/21 by H34; 16–19 and 22 onward are unused — 22/23
  are taken next to H34). **Confirmation** draws 24 and 25, run only if the screen passes.
- Folds: the four contiguous NW/NE/SW/SE quadrants, existing holdout implementation unchanged
  (20 % component hide, 1.5-km collar, no training from a component touching the test
  quadrant/collar, catalogue features from `draw.visible` only, scoring against `hidden_test`
  with visible faults masked, 12-px domain erosion).
- Base feature matrix: the 81-column H34 screen-control layout exactly — static families A–D
  (64), catalogue-relative E (7), add-on extras (7), H27 visible-tip columns (3). Family W
  (12) is appended after, via the existing `Context.h31_features`/`h31_names` slot with
  `Cell(..., extras=True, h27=True, h31=True)`.
- **Arms (5, fixed):**
  1. `C_base` — 81 base columns (same-run control; equals the H34 C0 feature set);
  2. `C_wrtp` — base + `W_RTP_*`;
  3. `C_wpsg` — base + `W_PSG_*`;
  4. `C_wgrav` — base + `W_GRAV_*`;
  5. `C_wall` — base + all 12 W columns. **Primary candidate.**
- Model: the repository's frozen `HGB_PARAMS` (`max_iter=100`, `learning_rate=0.12`,
  `max_leaf_nodes=31`, `min_samples_leaf=50`, `l2_regularization=1`, class weights `{0:1,1:5}`,
  no early stopping), ≤300,000 negatives, fit seed = draw. One fit per arm per cell; no
  hyperparameter search, no feature ablation or emission tuning after outcomes.
- Emission (identical for all arms, the frozen standard screen emission): Hessian-ridge NMS
  σ=1.0, drop visible known catalogue pixels, top `K = round(0.0245 · scored_domain_cells)`,
  Poisson-disk dot thinning at **2.4-px** minimum spacing — the same spacing as the H34 report that
  established the 0.14479 holdout best, keeping G4's comparison on an identical emission protocol.
  Metric: the repository's unit-tested
  transcription of the official 300 m triangular distance-weighted Tversky, α=0.2, β=0.8.
- Secondary (descriptive only, no gate — the two local proxies are in a registered conflict,
  IR-29-PROXY-CONFLICT): the H34 SGMC off-catalogue class
  (`data/external/derived_sgmc_faults_100m_u8.tif`, catalogue + 300 m excluded), reported per arm.

## 5. Fail-closed gates

Per stage (screen, then confirmation), let `Δ(fold, draw) = DTI(C_wall) − DTI(C_base)` in the
paired cell, and let `mean_w8` be the 8-cell mean DTI of `C_wall`:

1. **G1** For *each* stage draw, the mean of Δ over the four folds is **≥ +0.005**.
2. **G2** For *each* stage draw, Δ is positive in **≥ 3 of 4** folds.
3. **G3** No fold in either draw has Δ < **−0.010**.
4. **G4** `mean_w8` **> 0.14479**, the then-current comparable spatially-blocked holdout best
   (H34 C1 geodesic-dot control, 8-cell mean on draws 20/21, same Cell/emission/K/metric
   protocol; `knowledge/17_repo_candidate_2026-10-03.md`). This encodes the owner rule that no
   slot is spent on an idea that has not beaten the current holdout best.
5. **G5** All 40 cells present and finite; W-cache manifest SHA-256, input band hashes, frozen
   code revision, and HGB parameters match this document and the evidence design record.

**Decision rules.** Any screen gate failure → stop; no confirmation, no candidate file, no slot.
Confirmation failure → stop; no candidate file. Only a passing screen **and** passing
confirmation, plus the exact-file audit (single float32 band, EPSG:32611, 100 m, exact template
bounds, finite [0,1] in footprint, NaN outside, content-addressed filename, SHA-256 receipt),
authorizes building a *candidate* TIF to present to the owner. Nothing is submitted
automatically; the owner decides slot use, and the final selection rule (one submission scored
in both prize rounds) means a slot is spent at most once.

The per-branch arms `C_wrtp`, `C_wpsg`, `C_wgrav` are diagnostic contrasts only; they are
reported but never gate on their own (the primary question is whether dense worming persistence,
as a family, pays inside the frozen base matrix).

## 6. Sources

- Owner standing brief (this session's prompt), preserved in `README.md` and
  `knowledge/owner_brief_verbatim.txt` for the original session.
- Official problem page (metric, format):
  <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> (fetched
  2026-10-03; α=0.2, β=0.8, R=300 m; float32 [0,1] single band).
- Official rules (submission mechanics): NLR OSTI 96647,
  <https://docs.nlr.gov/docs/fy26osti/96647.pdf> (fetched 2026-10-03; single GeoTIFF, 100 m,
  three submissions per week, generative-AI narrative disclosure).
- Reference solution (official baseline, TverskyLoss α=0.2 β=0.8):
  <https://github.com/drivendataorg/gems-prize-reference-solution> (fetched 2026-10-03).
- Worm method: Hornby, Boschetti & Horowitz 1999
  ([10.1046/j.1365-246x.1999.00788.x](https://doi.org/10.1046/j.1365-246x.1999.00788.x));
  Horowitz 2018 ([Stanford-hosted review](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf)).
- Pseudogravity route: SEG 2014
  ([10.1190/segam2014-1323.1](https://library.seg.org/doi/10.1190/segam2014-1323.1));
  Seequent/Oasis montaj `fft2con` documentation.

## 7. Interpretation limits

All holdout DTIs are proxy results on hash-pinned **owner-mirror** inputs and artificially
hidden catalogue components. They do not reproduce the organizer's hidden expert-labeled test
faults, the public leaderboard, the private test score, or the final-round expanded-label
score. A gate pass authorizes a reviewed build and an owner decision, nothing more. Leaderboard
content is not copied into the repository by this experiment (single page fetches for manual
verification are logged in `registry/sources.json`).

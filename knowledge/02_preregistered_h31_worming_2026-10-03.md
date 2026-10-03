# H31 preregistration — multiscale potential-field edge persistence

**Base design frozen before H31 implementation.** Date: 2026-10-03 (UTC). The dated synthetic-test amendment below was made after feature-code construction but before any real-data model fit or DTI evaluation. This preregistration follows the ranked candidate review in [`01_candidates_ranked_2026-10-03.md`](01_candidates_ranked_2026-10-03.md). No DrivenData leaderboard, forum, data, or submission endpoint is accessed by this experiment.

## 1. Prior-work and draw-seed audit

The reviewed GEMSDOE25 repository is pinned at `efc4be7bb3cfdf2def12a7fb83284d3311ac9220` (`chore(feed): refresh source feed`). Before selecting new seeds, all available holdout evidence JSON/JSONL, all experiment runner defaults, and the H27/H28/H30 registers were inventoried:

| Prior work | Holdout draw seeds present in raw evidence | Evidence / qualification |
|---|---:|---|
| Five-family factorial | 0, 1 | `evidence/factorial/cells.jsonl`; four spatial quadrants. |
| H26 add-ons | 0, 1 | `evidence/addons/cells.jsonl`. |
| H26 add-on confirmation | 2, 3 | `evidence/addons_confirm/cells.jsonl`. |
| H27 tip/scarp screen | 4, 5 | `evidence/h27_screen/cells.jsonl`; its conditional confirmation on 6,7 did **not** run because the H27 gate failed. |
| H28 emission factorial | 0, 1 | `evidence/h28_holdout/cells.jsonl`. |
| H30 relay factorial screen | 6, 7 | `evidence/h30_relay_screen/cells.jsonl`; 40 model cells. |
| H30 feature-only smoke | 6 | `evidence/h30_feature_smoke.json`; feature construction only, no model fit or DTI. |
| H30 relay confirmation | 8, 9 | `evidence/h30_relay_confirm/cells.jsonl`; 40 model cells after the registered screen passed. |

Thus seeds **0–9** have been used in an evaluated or deliberately registered holdout context. H27's reserved-but-unrun 6,7 were later used by H30 after H27 failed; the H30 register records that reuse. Seeds **10,11** have no prior holdout row and are the new screen. Seeds **12,13** have no prior holdout row and are reserved for fresh confirmation, conditional on a passing screen. The separate model fit RNG is `seed=draw`; it is not an independent spatial replicate. The inventory was made before choosing 10–13.

The complete evidence scan is reproducible from the cloned predecessor repository and returned these draw sets for every raw holdout `cells.jsonl`: `factorial [0,1]`, `addons [0,1]`, `addons_confirm [2,3]`, `h27_screen [4,5]`, `h28_holdout [0,1]`, `h30_relay_screen [6,7]`, `h30_relay_confirm [8,9]`. H28 calibration Monte-Carlo draws and bootstrap iterations are not holdout draw seeds.

## 2. Newness boundary and primary question

The H31 question is whether a multi-height, linked edge-persistence representation of two independent potential-field sources improves held-out fault-trace prediction over the same training and emission pipeline. The reviewed predecessor has fixed-scale magnetic/gravity gradients, analytic signal, tilt, Hessian ridges, a reported H16 continuation attempt, a gravity–magnetic/depth conjunction, and previous A-family factorial results. Its recorded A-family effect was inert/negative on a catalogue-gap proxy. No inspected predecessor source or registered experiment makes a per-pixel path of horizontal-gradient maxima through multiple upward-continuation heights an explicit predictor. H31 does not claim that the idea is globally unprecedented.

The full physical **worm** method is not implemented. The available magnetic grid is reduced-to-pole (`rtp`), not a delivered pseudogravity grid; the gravity layer is **isostatic gravity anomaly**, not a Bouguer anomaly. H31 will first derive a Fourier vertical-integration pseudogravity **proxy** from `rtp`, then test it beside the isostatic gravity proxy. It will not treat raw RTP as canonical pseudogravity, estimate a source distribution, recover fault depth/dip, or infer geothermal activity from edge persistence alone.

## 3. Frozen feature construction

### Inputs and coordinate conventions

- Use only the aligned 100-m grids from the 19-band feature stack: `rtp` (magnetic input for the pseudogravity proxy) and `iso_grav_anom` (isostatic gravity proxy), plus the existing valid footprint and finite-data masks. No label, fault catalogue, well, spring, or held-out target is used to construct H31 static features.
- Grid spacing is 100 m in both axes. The existing project feature builder verifies band order against the owner-mirrored stack. The data byte pins prove only the mirror is unchanged; they do not authenticate it as an organizer download.
- Work on the full raster grid for spectral processing. Use nearest finite-value fill only as an FFT boundary condition. Multiply the detrended/mean-centered field by a cosine taper that reaches zero over 64 pixels toward the footprint boundary, pad by 128 pixels, and set the zero-frequency coefficient to zero. H31 output is always zero outside the finite footprint and within the 16-pixel boundary guard. Diagnostics retain the number of valid pixels removed by the guard.

### Magnetic vertical-integration pseudogravity proxy

Let `R(kx,ky)` be the two-dimensional Fourier transform of the padded, tapered, centered RTP grid and `k = sqrt(kx**2 + ky**2)` in radians per metre. Form `P(kx,ky) = R(kx,ky) / max(k, k_floor)` for nonzero frequencies and set `P(0,0)=0`, where `k_floor = 2*pi/(min(height,width)*100m)`. Take the real inverse FFT to obtain a **regularized vertical-integration pseudogravity proxy**. This captures the documented FFT/vertical-integration operation, but is not asserted to be an exact reproduction of the vendor filter: no flight date, true field parameters, density contrast, magnetization, remanence model, or vendor filter settings have been independently verified. Multiplicative unit conversion is omitted because the test uses scale-relative edge locations, not physical amplitude. The `k_floor`, taper and padding are fixed here and may not be tuned after DTI is observed.

### Height sequence, edges and tracking

For each scalar field (`P` pseudogravity proxy and isostatic gravity `G`), use continuation heights **0, 100, 200, 400, 800, and 1,200 m**. At each height apply the harmonic upward-continuation filter `exp(-h*k)` to the precomputed spectrum, inverse transform, compute the horizontal-gradient modulus, and detect local maxima with a 3×3 maximum filter. Retain maxima at or above the 90th percentile of the modulus over the safe finite-footprint domain for that height. The scale threshold is computed separately at each height; it ranks edge locations within that scale and is not a source-amplitude comparison.

From every retained 0-m maximum, follow the nearest retained maximum at the next height if it lies within **2 pixels** (200 m); repeat at each of the five transitions, stopping permanently on the first failed match. Use the Euclidean distance transform for nearest-maximum lookup. Record at the 0-m seed pixel:

- `H31_PSG_PERSIST` / `H31_GRAV_PERSIST`: number of visited heights divided by six, in `[1/6,1]` for surviving 0-m seeds and zero elsewhere;
- `H31_PSG_DRIFT` / `H31_GRAV_DRIFT`: cumulative lateral path length divided by the maximum possible 10 pixels, clipped to `[0,1]`, zero elsewhere;
- `H31_JOINT_PERSIST`: symmetric 200-m cross-grid support: at each footprint pixel, take the maximum of (a) the geometric mean of magnetic persistence there and the maximum gravity persistence within Euclidean radius 2 pixels, and (b) the geometric mean of gravity persistence there and the maximum magnetic persistence within the same radius. The search uses a 5×5 bounding window with diagonal corners excluded. This is zero unless both field types have an edge seed within 2 pixels.

Because tracks only begin at the zero-height maxima, this is a **discrete, thresholded local-neighbourhood persistence proxy**, not a continuous Poisson-wavelet transform and not a unique geological source inversion. Strong neighbouring sources may still shadow weaker contacts. Deep edge positions and apparent trajectories can be wrong. All such limitations remain visible in output documentation.

### Cache and diagnostics

Write a new regenerable float32 feature cache with an explicit names file and deterministic metadata: input file SHA-256 values, code revision, 100-m spacing, heights, spectral regularizer, taper/pad/guard sizes, per-height thresholds, maxima counts, matched-track counts, output finite/nonzero fractions, and output SHA-256 values. Refuse to overwrite nonempty H31 evidence directories. Keep caches under the ignored work directory, not Git.

## 4. Paired spatial design

- **Screen:** holdout draw seeds **10 and 11** in every existing NW/NE/SW/SE spatial quadrant.
- **Confirmation:** fresh holdout draw seeds **12 and 13**, run only if the screen passes every primary gate below.
- Use the existing holdout implementation without changing it: 20% component hide, four contiguous quadrants, 1.5-km collar, no training from a component touching the test quadrant/collar, catalogue features computed only from `draw.visible`, and scoring against `hidden_test` with `visible` known faults masked. Keep the existing 12-pixel domain erosion.
- The train/test/hide masks, negative sample, and metric calculation are shared within each fold×draw across all arms. Four spatial quadrants are the replication units; draws are repeated component-hide realizations, not eight independent geographies.
- **Factorial arms (5 total, fixed order randomized with seed 20261005 and then reused in all cells):**
  1. `BASE_NO_TIP`: BDE static families + existing X1–X3 add-ons;
  2. `T_BASE`: `BASE_NO_TIP` plus the existing H27 visible-only `H27_tip` feature;
  3. `T_PLUS_PSG`: `T_BASE` plus `H31_PSG_PERSIST` and `H31_PSG_DRIFT`;
  4. `T_PLUS_GRAV`: `T_BASE` plus `H31_GRAV_PERSIST` and `H31_GRAV_DRIFT`;
  5. `T_PLUS_PSG_GRAV`: `T_BASE` plus both field feature pairs and `H31_JOINT_PERSIST`.
- H27 tip is a fixed same-run control only; it is not promoted or relabeled as slot-approved. The baseline is **BDE + X1–X3**, matching the established holdout pipeline. No hyperparameter search, feature ablation after outcomes, or emission tuning is allowed.
- Model: the predecessor's `HistGradientBoostingClassifier` settings unchanged (`max_iter=100`, `learning_rate=0.12`, `max_leaf_nodes=31`, `min_samples_leaf=50`, `l2_regularization=1`, class weights `{0:1,1:5}`, no early stopping). At most 300,000 negatives; seeded component-hide training data and model seed use the draw ID.
- Emission fixed for all arms: Hessian-ridge NMS with sigma 1.0, remove visible known catalogue pixels, top `K = round(0.0245 * scored_domain_cells)`, then score-ordered Poisson-disk thinning with 2.4-pixel minimum spacing. DTI uses the project's unit-tested transcription of the official triangular 300-m distance-weighted Tversky metric (`alpha=0.2`, `beta=0.8`).

## 5. Primary response and fail-closed gates

The primary candidate is `T_PLUS_PSG_GRAV`. The diagnostic 2² factorial contrasts (PSG main effect, gravity main effect, and PSG×gravity response interaction) are computed on the four `T_BASE` factorial arms, averaged over the two draws within each fold. `BASE_NO_TIP` is an additional same-run comparator. Do not treat the eight fold×draw cells as independent spatial blocks.

For each stage, the per-fold control is the highest mean DTI among `BASE_NO_TIP`, `T_BASE`, `T_PLUS_PSG`, and `T_PLUS_GRAV`; the paired gain is the candidate's two-draw mean minus that per-fold best-control DTI. **Screen and confirmation must each satisfy all of:**

1. mean paired gain across the four spatial blocks is **greater than +0.001 DTI**;
2. paired gain is positive in **at least 3 of 4** spatial blocks;
3. no spatial block is worse than **−0.010 DTI**;
4. average emitted share within 300 m of visible catalogue faults does not increase by more than **+0.10** versus the same per-fold best-control arm;
5. all 40 cells are present, finite, and match the frozen feature/model/emission manifest; every H31 feature has finite values inside its allowed range and zeros outside the safe footprint.

No historical comparator is used as an absolute gate because predecessor records document cache/environment comparator drift. H30 failed its registered fresh confirmation; it is not a current eligible baseline. Report historical scores only as contextual proxy measurements and never as competition scores.

**Decision rules:** if any screen gate fails, stop and do not run confirmation. If confirmation fails, stop and do not create a candidate TIFF. Even if confirmation passes, it only authorizes a separately reviewed full-data build and format audit; it does not automatically authorize a weekly submission. A final submission requires the official template grid/CRS/geotransform, single float32 band, finite `[0,1]` predictions on the footprint, null/NaN outside, one-click download, a unique distinguishing filename, and a concise paste-ready comment. No weekly slot is used by this research run.

## 6. Source basis and caveats

- Hornby, Boschetti & Horowitz (1999), [Geophysical Journal International 137, 175–196](https://doi.org/10.1046/j.1365-246x.1999.00788.x), and Horowitz (2018), [Stanford-hosted review](https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf), describe gravity worms from upward-continued gravity grids and magnetic worms from pseudogravity grids; edge positions are maxima of horizontal-gradient modulus at multiple heights. Horowitz explicitly states inversion non-uniqueness, source-shadowing, and worsening positional accuracy with depth.
- The [SEG 2014 abstract](https://library.seg.org/doi/10.1190/segam2014-1323.1) describes pseudogravity as vertical integration of magnetic TMI using FFT. The [Seequent/Oasis montaj filter manual](https://help.seequent.com/Oasismontaj/2023.2/Content/gxhelp/fft2con/fft2con_gpsd.htm) documents RTP as a valid input when inclination is set to 90° and declination to 0°. These support a **pseudogravity-like input route**; they do not verify the supplied grid's survey acquisition metadata or make this implementation vendor-identical.
- The official [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and rules PDF [NLR 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) are the competition target/format sources recorded by the predecessor source registry. No competition website data or leaderboard is fetched by the H31 runner.
- All holdout DTI results are computed on hash-pinned **owner-mirror** inputs and artificially hidden catalogue components. They are proxy evidence only, with uncertain relation to organizer-hidden faults and official leaderboard DTI.

## 7. Pre-fit implementation amendment — cross-grid co-location tolerance

**2026-10-03, before any H31 model fit or DTI evaluation.** The initial deterministic synthetic engineering test used an identical step field for both sensors. The vertical-integration transform shifts/spreads its local maxima relative to the untransformed gravity maxima, so exact same-pixel multiplication made the preregistered joint term identically zero even when edges were spatially aligned within one grid cell. This is a geometry/feature-construction defect found in a synthetic test, not a holdout outcome. The joint term is therefore defined above as a symmetric maximum within a fixed Euclidean radius of 2 pixels (200 m; represented by a 5×5 bounding window with corners excluded) for the aligned 100-m inputs. The radius equals the per-height tracking radius and is frozen before any real-data DTI. This is a clarification to avoid exact pixel equality of two different transforms; no scales, data layers, model, draws, response, emission, or promotion threshold changed.

## 8. Immutable registration and outcome reporting

This file is the hash-pinned preregistration. Do not edit it after the code freeze or any model fit. Dated screen/confirmation outcomes, raw-cell checksums, and analyzer receipts are recorded in their evidence directories and in a separate post-analysis outcome note. This keeps the registered hypothesis and thresholds immutable while allowing the findings to be appended without changing the preregistration hash.

## 9. Post-sync prior-work correction (2026-10-03; before any H31 model fit)

The Arena branch was originally based at `ad130c8d`, before the H29 work reached `main`. During the PR rebase, the current main history was reviewed and the H29 outcome was found: raw-RTP/isostatic-gravity worm persistence was already screened as a gate, rank feature, and model feature, alongside residualized thermal features. All four H29 arms failed their pre-registered `+0.005` catalogue-gap proxy gate; no confirmation or weekly slot followed (see `knowledge/02_h29_results_2026-10-03.md` and `evidence/h29_gate.json`).

This corrects the novelty boundary: H31 is **not** a first test of worming or persistence. Its narrow remaining distinction is the regularized vertical-integration pseudogravity transform on RTP and explicit lateral edge-drift features, which the H29 implementation did not test. The H29 negative proxy result lowers the prior probability of a useful H31 gain and H31 is now lower priority than the unimplemented H32 terrain-shape hypothesis. This note does **not** change H31 inputs, scales, feature names, folds, random seeds, model, emission budget, response, thresholds, or promotion gates; no H31 model fit, DTI screen, or confirmation has occurred. H31 remains parked until the inputs are restored and a fresh, clean-source screen is deliberately run.

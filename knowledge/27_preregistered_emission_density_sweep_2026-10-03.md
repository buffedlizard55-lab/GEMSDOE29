# 27 — Preregistered emission-density sweep on the frozen H19-5 habitat, frozen 2026-10-03

Status: **frozen before any proxy score in this family is computed.** The spacing set, the score-aware
variant, the calibration rows, the decision rule and the interpretation limits below may not be edited
after `evidence/emission_sweep/summary.json` exists. A change of intent is recorded as a dated amendment
with its own sha-pinned evidence file; the original text stays.

This document is the *measurement* counterpart of [`knowledge/07`](07_metric_emission_analysis_2026-10-03.md).
`knowledge/07` explains, from the published metric algebra and from geometry computed on the pinned bytes,
why the group's ladder moved `0.1922 → 0.2477 → 0.2600` as the emission was thinned (`H19-5` solid →
`dot_thin(·, 1.5)` → `dot_thin(·, 2.8)`). It also states the open question this document answers: **the ladder
was measured at three points only and its last measured point (2.8 px) is the best one, so nothing in the
repository shows whether the density optimum is at 2.8 px, beyond it, or between the measured points.**

## 1. Question, stated so it can come out negative

Under the two registered spatial proxies defined in `scripts/score_candidates.py` — (i)
`catalogue_hidden`, the mask-and-hide quadrant proxy on draws 20/21, and (ii) `sgmc_off_catalogue`, the
state-map fault class ≥300 m from the supplied catalogue — does a different Poisson-disk spacing of the
**same, frozen** H19-5 habitat, or a score-aware placement of the same number of dots, beat the pinned
`d = 2.8 px` artifact (`sha256 91eae1ca…39b8`, 44,090 px, the file whose owner-reported live score is
0.2600)?

Falsifiers, all of which are publishable outcomes:

* the proxy preference is flat across the sweep (no spacing beats 2.8 px) → the ladder is converged on the
  proxy axis and the 0.2600 file should not be re-spaced;
* the proxy ranks the calibration ladder in the *opposite* order to the live ladder → the proxy's density
  axis is miscalibrated and this document reports a measurement, not a recommendation;
* the score-aware placement loses to the blind one → averaging kernel mass is not what the metric wants at
  this budget, and H26-0's score-ordered dotting is not a free improvement.

## 2. Frozen inputs (all hash-pinned; verified at restore time by `scripts/restore_data.py`)

| input | sha256 (prefix) | bytes | role |
|---|---|---|---|
| `data/inputs/h19_5_nan.tif` | `ec1f9b56b83c…` | 1,712,322 | the frozen habitat: binary float32, 121,131 positive pixels, no catalogue pixels |
| `data/inputs/dotted_h19_5_d2_8_nan.tif` | `91eae1ca42ec…` | 1,603,424 | the reference artifact (`d = 2.8`, 44,090 px) |
| `data/inputs/dotted_h19_5_d1_5_nan.tif` | `68d0e2e4fcc5…` | 1,632,732 | calibration rung (`d = 1.5`, 60,069 px) |
| `data/sample_submission.tif` | `2176d08e485a…` | 1,599,597 | footprint/grid definition |
| `data/labels.tif` | `7ba308ccdc44…` | 425,830 | the visible/hidden catalogue used by the proxy |
| `data/external/derived_sgmc_faults_100m_u8.tif` | `643cbe992ef4…` | 198,602 | the second proxy's truth |

**Verified this session, before freezing (pure geometry, no scoring):** `dot_thin(H19-5 > 0, 2.8)` is
**pixel-identical** to the pinned 2.8 file (44,090 px) and `dot_thin(H19-5 > 0, 1.5)` is pixel-identical to
the pinned 1.5 file (60,069 px). This closes irregularity **IR-29-D28-NAMING** (knowledge/07 §6.1): the
`d2-8` file name is correct for these bytes. The transform implemented in `src/gemsdoe/thinning.py` is the
transform that produced the group's best-scoring artifact.

## 3. Frozen candidate set (15 scored rows = 12 new + 3 calibration)

All new rows are deterministic transforms of the pinned parent. No label, score, model or random number is
read by the *construction*; labels are read only by the scoring step, exactly as in
`scripts/score_candidates.py`.

1. **`thin_<d>` for d ∈ {2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 4.8, 5.6, 6.4}** — `dot_thin(parent > 0, d)`,
   the same score-blind geodesic Poisson-disk transform as the ladder. `thin_2.8` is a determinism control:
   it must reproduce the pinned reference pixel-for-pixel, and the run aborts if it does not.
2. **`aware_<d>` for d ∈ {2.8, 3.6, 4.8}** — `score_ordered_dots(score, parent > 0, min_dist=d)` with the
   score surface **frozen here** as `gaussian_filter(parent.astype(float32), sigma=2.0)` (px). Rationale,
   declared before measuring: `dot_thin` starts from each component's lowest raster index, so it can place a
   dot at the ragged end of a wide lineament; a blurred-density score puts the same number of dots where
   more of the parent's kernel mass is, which is the quantity the metric's TP term accumulates.
3. **Calibration rows (not selectable as recommendations):** `cal_solid` (the parent itself, d ≤ 1),
   `cal_d1_5` (pinned file), `cal_d2_8` (pinned file, also the reference).

Budget is reported for every row (emitted pixels inside the footprint); no row's budget is used to alter the
emission — this is a spacing/placement comparison, not a budget search.

## 4. Frozen scoring protocol

Identical to `scripts/score_candidates.py` (which produced `evidence/candidate_scoreboard.json`): folds
0–3 of `gemsdoe.holdout.Holdout(foot, labels, 0.20)`, draws 20 and 21, `DOMAIN_ERODE = 12` px, truth =
`draw.hidden_test & domain`, `dtI_binary(emit & domain, truth, valid=domain, known=draw.visible)`; SGMC
class = SGMC pixels that are neither catalogue nor within 3 px of catalogue, scored with
`valid=footprint, known=labels`. No model is fitted, no draw is spent (this is a fixed-file screen; draws
20/21 are the registered proxy draws already used by the committed scoreboard).

## 5. Frozen decision rule

1. **Report** the full curve: every row's `catalogue_hidden_mean`, the eight paired per-cell deltas against
   `cal_d2_8`, and its SGMC DTI. Nothing is dropped or averaged away.
2. **Proxy-calibration check (reported first):** the live ladder is monotone increasing in spacing
   (0.1922 < 0.2477 < 0.2600). If `catalogue_hidden_mean(cal_solid) ≤ mean(cal_d1_5) ≤ mean(cal_d2_8)`
   does **not** hold, the proxy's density axis is declared *uncalibrated* and any recommendation below is
   labelled "measurement only — not a slot-relevant selection".
3. **Admissible row:** a new row `s` is admissible iff (a) its paired mean delta against `cal_d2_8` on the
   catalogue-hidden proxy is **> 0**, and (b) its SGMC DTI is **not worse than 0.98 ×** the reference's.
4. **Recommendation:** if ≥1 row is admissible, recommend the admissible row with the largest
   catalogue-hidden mean; its TIF becomes **a downloadable research candidate, not a slot-approved
   submission**. If none is admissible, the recommendation is explicitly "keep the pinned 2.8 px artifact".
5. **No slot implication.** The project's slot rule is unchanged and stricter: a weekly slot requires
   beating `holdout_best = 0.14479018210246675` *on the protocol that produced it* (the H34 cells, draws
   20/21, a fitted-model protocol). A file-level proxy comparison cannot clear that rule and this document
   does not claim it does. The ladder's own history (live 0.1922 → 0.2477 → 0.2600 = a *reported* +0.068
   from spacing alone, knowledge/07 §3) is the reason a spacing measurement is worth a session at all.
6. **No re-tuning after the fact.** If the winner is at the boundary of the sweep (6.4 px) that is reported
   as a boundary result and **not** extended by a second sweep in this session.

## 6. Interpretation limits declared in advance

* Both proxies are catalogue-derived; the organizer's private expert labels are unobservable here. A proxy
  win is not a competition-score prediction (standing limitation, `knowledge/22`).
* `knowledge/07` §4's conditional model (|G| ≈ 12.7 k, credit/dot ≈ 0.089) is **not** used to select a row;
  it appears only in the discussion of *why* a spacing win is plausible.
* The committed scoreboard numbers for `cal_d2_8` are a free replication check: this run must reproduce
  `catalogue_hidden_mean = 0.09832378835029429` and `sgmc dti = 0.09528236525789707` for that file to
  within float32 read noise; if it does not, the run is void and is reported as such.

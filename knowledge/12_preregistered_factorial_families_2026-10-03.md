# Pre-registration — 2^(5−1) fractional factorial over the five feature families

**Date frozen:** 2026-10-03 (UTC), written **before** the first cell of this experiment was fitted.
**Owner brief item:** “Instead of adjusting one factor at a time, run a fractional factorial experiment (with
statistical significance) with respect to feature families”. Design theory follows Box, Hunter & Hunter,
*Statistics for Experimenters* (2nd ed.), ch. 6–7: a resolution V 2^(5−1) design estimates all five main
effects and all ten two-factor interactions under the standard **sparsity-of-effects** assumption
(three-factor and higher interactions negligible).

## Design matrix (frozen)

Five factors, each at two levels (−1 = family excluded, +1 = family included):

| code | family | columns (registry `src/gemsdoe/families.py`) |
|---|---|---|
| A | potential-field gradients | 16 gravity + magnetic gradient / analytic-signal / ridge columns |
| B | DEM curvature & scarp | 24 detrended-DEM and 3DEP-LiDAR scarp columns |
| C | strain & seismicity | 7 geodetic-strain and earthquake-density columns |
| D | thermal & geochemical | 17 radiometric, MT-conductance and GDR-1391 columns |
| E | catalogue geometry | 7 distance / orientation / density columns of the **visible** faults |

**Generator:** `E = A·B·C·D` (defining relation `I = ABCDE`), 16 runs, resolution V. The coded model
matrix has an intercept, 5 main effects and 10 two-factor interactions and is exactly orthogonal
(`XᵀX = 16·I`), so every reported contrast is a plain difference of means.

**Run order** is a fixed random permutation recorded in `design.json` (seed 20261003); fits are
order-independent given the frozen HGB seed, so the permutation is a documented safeguard, not an input.

## Response, model and emission (frozen, identical for all 16 runs)

* `Cell` construction as in `src/gemsdoe/experiment.py` with `extras=False, h27=False, h30=False, h31=False`;
  training sample = all visible-catalogue positives + 300 000 randomly drawn off-catalogue negatives
  (seed from the cell), model = `HGB_PARAMS` (100 iters, lr 0.12, 31 leaves, min_leaf 50, l2 1.0,
  class weight {0:1, 1:5}), `random_state=0`.
* Columns used = the union of the selected families' columns, in registry order. No add-on (`X1_*`,
  `S_dem_*`) or H27/H30/H31 columns are used, so the design is exactly the five families of the brief.
* Emission = the repository's standard screen pipeline, identical to every other registered screen:
  ridge NMS (Hessian σ = 1 px, across-strike NMS) → drop pixels on/near the visible catalogue → top
  `K = round(0.0245 × scored domain pixels)` → `dot_thin(min_dist = 1.5 px)`.
* Response per cell = the masked holdout DTI from `Cell.evaluate` (spatial hide-and-recover, 20 % of
  visible catalogue components removed per fold, 15 px collar; catalogue pixels masked in the score).
* Cells = all four quadrant folds × two holdout draws, **draws 14 and 15** (draw inventory: 0–9 earlier
  work, 10–13 frozen to H31, 20–21 frozen to H34, 14–19 unused at freeze time; this experiment claims
  14–15). Every (run, fold, draw) response is written to `cells.jsonl`; nothing is averaged before the
  raw table exists.

## Analysis (frozen)

1. `y[run, fold, draw]` = DTI; per-run mean over cells, `ȳ[run]`.
2. Effects = `Xᵀȳ/16 × 2` (i.e. mean at +1 minus mean at −1) for the 5 main effects and 10 two-factor
   interactions, with residual standard error from the 5 unestimated (3-factor) columns, reported as
   `effect ± se` and `t = effect/se` with 5 residual degrees of freedom.
3. Paired robustness: for each factor, the 8 within-cell contrasts (4 folds × 2 draws) are reported
   with their sign count and minimum.
4. **Support rule (frozen):** a factor or interaction is called *supported* only if
   `|effect| ≥ 0.001` **and** at least 6 of the 8 within-cell contrasts agree in sign **and** the
   per-cell advantage never falls below −0.010 in any cell. Anything else is reported as noise.
5. This experiment cannot justify a submission slot (it tests family inclusion, not a candidate file),
   and its holdout DTI is a catalogue-gap proxy, not the competition metric.

## Interpretation limits, stated up front

* The design speaks only to the frozen HGB + emission configuration. A family that looks inert here
  could be informative in a different model class or emission geometry.
* Family membership is a working interpretation (`src/gemsdoe/families.py` header lists the disputed
  assignments, e.g. `tc`), so a family effect is an effect of *this column set*.
* Two draws are two holdout splittings, not independent datasets; the fold-level sign test is reported
  precisely to keep that visible.

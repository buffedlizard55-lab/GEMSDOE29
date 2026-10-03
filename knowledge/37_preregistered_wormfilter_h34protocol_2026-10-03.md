# 37 — Preregistered H52 stage: worming survival as an *emission filter*, scored on the H34 bar protocol

**Status: FROZEN before any fit.** Written 2026-10-03 (session 7) and committed before
`scripts/run_wormfilter_screen.py` runs. Its SHA-256 is recorded in `evidence/wormfilter_screen/design.json`;
editing this file after the run invalidates the stage.

## 1. The question, and why a fifth worming stage is not silent fishing

`knowledge/34` §4 closed the worming family after four negative formulations and said plainly that a
fifth variant *without a new mechanism* would be fishing. This stage carries a new mechanism, and the
reason is measured, not asserted (`tests/test_wormfilter.py`, all synthetic, all reproducible):

| defect in the four earlier formulations | measurement in this repository |
|---|---|
| `worms._edge_maxima` marks an edge where the horizontal-gradient modulus is an **isotropic 3×3 local maximum** — a straight contact becomes a handful of points, so persistence was measured on points, not lines | a 64-px synthetic contact yields **37** level-0 pixels under the isotropic test |
| the per-level threshold is a **percentile of that level's own** modulus, so a low-pass filter never removes anything from the edge set: **nothing can "vanish"** | a synthetic **400 m-wavelength ripple** (unambiguously shallow) keeps **3,362** ridge pixels at 0–400 m and scores geometric persistence **0.80** |
| consequence | geometric persistence on the same three synthetics: shallow ripple **0.257**, deep 4,800 m ripple **0.250**, straight contact **0.096** — near-blind |

The replacement implemented in `src/gemsdoe/wormfilter.py` measures what the brief describes:

1. **across-strike ridge levels** (45°-quantized non-maximum suppression along the field-gradient
   direction, the `thinning.ridge_nms` convention) plus a contrast floor of 10⁻³ of the level's own
   maximum HGM, so a quiet field cannot mark float round-off as an edge;
2. **survival with height**: at each continuation height an edge survives where the continued gradient
   modulus retains ≥ `rho_retention` of its own level-0 modulus within `tol_px`. Deep equivalent sources
   keep their gradient; shallow ones decay as exp(−k·h) and drop out.

Verified separation on the same synthetics (`WF_SURV_JOINT`, interior mean): shallow 400 m ripple
**0.000** (ridge population 1,643 → **0** at 1,200 m), deep 4,800 m ripple **0.707** (246 → 128), and a
contact whose survival rises monotonically with its transition width (sharp **0.40** → 400 m-wide
**0.80**). This is the first worming statistic in this repository that separates shallow from deep.

That is the mechanism delta. It does **not** change the prior much: the family base rate is 0-for-4 and
this stage is allowed to fail. What it changes is the interpretation — if survival-as-filter also fails,
the repository can say the *physics-correct* version was tested, not only the geometry-only proxies.

## 2. Frozen fields (label-free; built before any fit)

`scripts/build_wormfilter_fields.py` → `data/work/wormfilter_fields.npy` (8 × 5,167,373 float32),
`wormfilter_az_defined.npy`, `wormfilter_fields.json`. Inputs: `02_rtp.npy` (RTP magnetics) and
`13_iso_grav_anom.npy` (isostatic residual gravity) from the hash-pinned owner mirror. No label,
catalogue or holdout array is read.

| column | definition |
|---|---|
| `WF_SURV_MAG` / `WF_SURV_GRAV` | fraction of continuation heights (h > 0, ladder 0/100/200/400/800/1200 m) retaining ≥ 25 % of the local level-0 gradient modulus |
| `WF_SURV_JOINT` | `min` of the two — the edge must survive in **both** independent fields |
| `WF_SURV_DEEP` | magnetic survival restricted to heights ≥ 400 m |
| `WF_P_JOINT` | geometric persistence (fraction of levels with a ridge within 2 px) — kept as the earlier statistic |
| `WF_CONV` | convergence size: level-0 ridge pixels within 600 m of a deep edge, log-scaled by its p99 |
| `WF_AZ_AGREE` | `(1 + cos 2(θ_mag − θ_grav))/2` from level-0 structure tensors; 0.5 where undefined |
| `WF_SHALLOW_ONLY` | 1 where a level-0 edge exists in either field but `WF_SURV_JOINT < 0.5` |

Frozen filter parameters (`WormFilterConfig` defaults, declared here): `tol_px = 2.0`,
`smooth_sigma_px = 1.0`, `rho_retention = 0.25`, `tau_survival = 0.5`, `tau_azimuth = 0.5`,
`coherence_min = 0.2`, `convergence_radius_px = 6.0`, `azimuth_sigma_px = 1.5`,
`min_contrast_fraction = 1e-3`. **No parameter may be re-tuned after any cell is scored.**

## 3. Frozen protocol (identical cell set to `knowledge/27`, so the bar is comparable)

| field | value |
|---|---|
| folds | NW/NE/SW/SE = fold ids 0,1,2,3 (`Cell` quadrant folds, 12 px domain erosion) |
| draws | **20, 21** — already spent by the H34 screen and *reused* because they define the bar; no new draws are claimed and `registry/draw_ledger.json` `next_free_draw` stays 36 |
| model | `HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)` on the frozen H34 control matrix (`extras=True, h27=True`), positives = hidden-train labels, ≤300,000 negatives at >1.5 px |
| `k` | `round(0.0245 × dom_c.sum())`; dot spacing **2.4 px** (the H34 constants) |
| metric | masked DTI inside the eroded quadrant domain, `known` = visible catalogue; SGMC off-catalogue class exactly as in H34/H41 |

Arms (one fit per cell for the six emission arms; a second fit only for the feature arm):

| arm | definition |
|---|---|
| `C0_base` | frozen control: `score_ordered_dots(score, candidates, 2.4)` |
| `C1_geodesic_dots` | frozen control: `dot_thin(candidates, 2.4)` — the parent of every refill arm |
| **`W2_surv_refill` (PRIMARY, declared now)** | drop ridge candidates flagged `WF_SHALLOW_ONLY`, re-select the top-*k* from what remains, then `dot_thin(·, 2.4)` — identical to `C1` except for the veto |
| `W1_surv_veto` | `dot_thin(candidates & ~veto, 2.4)`: the veto without refill, so the budget is allowed to shrink and the shrinkage is reported |
| `W3_azimuth_refill` | refill after the azimuth veto (defined **and** `WF_AZ_AGREE < 0.5`) |
| `W4_union_refill` | refill after the union of both vetoes |
| `W5_surv_features` | `C0` emission with the 8 `WF_*` columns appended (the *feature* role comparator) |

The H29 A1 convention is kept: a candidate is removed only where the statistic is **defined**; where the
worm fields are silent (no level-0 edge, or no coherent azimuth) the candidate is untouched.

## 4. Frozen gates (all must hold for a promotion recommendation)

Per fold, `bar_fold = max(mean DTI of C0_base, mean DTI of C1_geodesic_dots)` over draws 20/21 and
`gain_fold = mean DTI of W2_surv_refill − bar_fold`.

- **G1 (effect):** `mean(gain_fold) ≥ +0.005` **and** ≥ 3 of 4 folds positive **and** `min(gain_fold) ≥ −0.010`.
- **G2 (level of the bar):** `mean DTI of W2_surv_refill > 0.14479018210246675` (the recorded H34 best).
- **G3 (secondary proxy, inherited verbatim from `knowledge/19` §4/§5 — the clause that vetoed H41):** the
  SGMC off-catalogue class must move `≥ 0.000` **and** be positive in ≥ 3 of 4 folds; otherwise
  *proxy conflict, no promotion*.
- **G4 (integrity):** all 42 cells present and finite; `C0_base` and `C1_geodesic_dots` reproduce the
  stored `evidence/h34_coverage_screen/cells.jsonl` values for the same (fold, draw) to ≤ 1e-6 absolute.
  If G4 fails the stage reports **not comparable** and issues no verdict.
- **G5 (inertness guard, pre-declared from the H31 sparsity failure):** the stage is **FAIL-inert** if the
  primary arm's emitted set equals `C1`'s in all 8 cells, or if the mean veto rate over cells is
  < 0.02 or > 0.60 of the candidate set. A veto touching < 2 % cannot move DTI by 0.005; above 60 % the
  arm is a budget cut, not a re-ranking, and must be reported as such.
- **G6 (leak/inertness guard for the feature arm, from `IR-29-ARTIFACT-LEAK`):** `W5_surv_features` must
  place ≥ 1 split on a `WF_*` column in ≥ 3 of 8 cells, else the feature arm is reported inert and no
  claim is made about the feature role.

**Interpretation rule, frozen.** G1+G2+G4+G5 with G3 failing = *primary gain, secondary-proxy conflict,
no promotion* (the H41 outcome). G1+G2+G3+G4+G5 = the first slot-eligible method in this repository; a
cross-fitted artifact may then be built and registered, still subject to the exact-file audit and the
owner's decision. Any other combination = no promotion, with the failure mode written down here in
advance. Secondary arms (W1/W3/W4/W5) are **reported, never promoted**: promoting one would require a
new preregistration, and this document names `W2_surv_refill` as the only promotable arm.

## 5. The artifact-audit number the brief asks for (design-time, label-free)

The brief wants the acquisition-artifact distrust expressed as a number. Alongside the cells this stage
reports, from the same frozen fields and no labels:

- the share of the owner-mirrored **D2.8** emission (44,090 px, `data/inputs/dotted_h19_5_d2_8_nan.tif`)
  that `WF_SHALLOW_ONLY` flags, and the mean `WF_SURV_JOINT` of its dots versus the whole domain;
- the same two numbers for the repository's cross-fitted `C0` emission;
- the footprint-wide `WF_SHALLOW_ONLY` fraction and the `WF_SURV_*` distribution.

## 6. What this stage explicitly does **not** claim

- Not a competition score, not organizer ground truth, not a statement about the hidden expert labels.
  Both proxies are local; the SGMC class is a state-map fault inventory.
- No weekly slot is spent, nothing is uploaded, DrivenData is never contacted.
- Reusing draws 20/21 makes this a **paired re-measurement on the bar-defining cells**, not a fresh
  screen. A pass here would still require fresh confirmation draws (36/37) before any slot discussion.
- Survival-with-height is a reliability proxy. Upward continuation does not give a unique source depth
  (Horowitz 2018 warns explicitly about non-uniqueness and source shadowing), and a "shallow" verdict
  is not proof that an edge is cultural noise.

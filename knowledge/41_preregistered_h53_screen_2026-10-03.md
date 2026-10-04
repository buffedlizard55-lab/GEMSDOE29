# 41 — Preregistered H53 screen: cross-scale topographic fabric coherence (frozen before any fit)

**Date:** 2026-10-03 (session 8). **Status:** frozen protocol. **Written:** after the design-stage audit
(`evidence/h53_design_audit.json`) and **before** any cell of the screen was fit.
**Stage:** `evidence/h53_screen/`. **Stage runner:** `scripts/run_h53_screen.py` (hashes this file into
`design.json`; refuses to run from a dirty worktree and refuses to overwrite existing evidence).

This document follows the frozen structure of `knowledge/19` / `knowledge/24` / `knowledge/27` /
`knowledge/37`: arms, draws, constants, gates and the decision rule are declared here, and nothing in
this file may be edited after the screen runs (a post-run correction must be a new dated document).

## 1. Question

Does a **label-free**, cross-scale topographic fabric statistic — the structure-tensor *coherence* and
the *agreement of the dominant strike across three analysis windows* (300 / 700 / 1500 m) — add
catalogue-hidden DTI ranking information beyond the frozen 69-column matrix, on the frozen H34 bar
protocol, on **fresh** draws?

Physics in one sentence: a fault-controlled lineament keeps one strike as the observation window grows,
while dune fields, drainage texture, bedding and acquisition-scale noise rotate or are replaced; a
fabric that exists at one window only is the topographic analogue of a candidate that exists only at
zero continuation.

Primary references (already in `registry/sources.json` or added with this stage):
Bigün & Granlund (1987, *Proc. IEEE First Int. Conf. on Computer Vision*, London, 433–438) for the
orientation tensor; Weickert (1999, *International Journal of Computer Vision* 31:111–127,
doi:10.1023/A:1008009714131) for the coherence/eigenvalue formalism; Hornby, Boschetti & Horowitz (1999) for the
scale-persistence *idea* the owner brief asked this project to test (already screened for the potential
fields — `knowledge/34` §4, `knowledge/40` — and **not** re-screened here); Bull & McFadden (1977) is
*not* used by H53 (that is the H50 range-front idea). H53 uses **no external data**: only the cached
100 m `det_elev` band and the footprint.

## 2. Columns and the design-stage choice (disclosed, not hidden)

The four columns (footprint vectors, float32, `[0, 1]`, frozen order; built by
`scripts/build_h53_fields.py`, label-free — no catalogue, no labels, no fit):

| column | definition |
|---|---|
| `H53_COH_MIN` | minimum structure-tensor coherence over the three windows that have a defined orientation; 0 if fewer than two are defined |
| `H53_AGREE` | axial (mod 180°) coherence-weighted resultant length of the three window strikes; 1 = one strike, ~0.5 = three unrelated strikes, 0 = incompatible |
| `H53_NSCALES` | share of the three windows whose strike lies within ±15° of the coherence-weighted mean strike (0, 1/3, 2/3, 1) |
| `H53_PERSIST` | `H53_COH_MIN × H53_AGREE` (strong **and** scale-persistent) |

Frozen parameters (`src/gemsdoe/h53.py::H53Config`): `scales_px=(3, 7, 15)`,
`gradient_sigma_px=1.0` (gradient pre-scale; the window is the *tensor* window), `tensor_sigma_factor=1.0`,
`tol_deg=15.0`, `coherence_min=0.15`, `min_contrast_fraction=1e-3` (an **absolute** fraction of each
window's own 99th-percentile gradient modulus — deliberately not a percentile-of-own-level threshold,
the failure mode diagnosed in `knowledge/34` §4), `elev_band=12_det_elev.npy`.

**Design-stage selection (disclosed):** three variants were declared and measured *before* this file was
written, on one **spent** draw (NW, draw 20) only — raw, high-pass 3 km (`hp30`), high-pass 6 km
(`hp60`); the declared selection rule was "best `H53_PERSIST` off-catalogue AUC, provided the top decile
is not more catalogue-hugging than `det_elev_slope`'s". Result (`evidence/h53_design_audit.json`):
`hp30` won (`H53_PERSIST` off-catalogue AUC **0.5933**; `H53_COH_MIN` 0.5915, `H53_NSCALES` 0.5681,
`H53_AGREE` 0.5392); its top decile is **3.75 %** within 300 m of the visible catalogue versus
4.4–8.1 % for the DEM-family columns `B_crest`/`det_elev`/`det_elev_slope`/`L_step_max`, and its
correlation with those columns is **negative** (|ρ| 0.14–0.27). The base DEM-family columns' own
single-column off-catalogue AUCs are 0.478–0.506 on the same draw. The screen therefore uses the `hp30`
variant. **Draws 36/37 were not touched during the audit** (the audit reads only draw 20).

## 3. Arms (5) and the declared primary

| arm | columns added to the frozen matrix | role |
|---|---|---|
| `C0_base` | none; emission `score_ordered_dots(score, candidates, 2.4)` | control |
| `C1_geodesic_dots` | none; emission `dot_thin(candidates, 2.4)` | the recorded slot **bar** control (`knowledge/27`) |
| **`A1_h53_persist`** | the four `H53_*` columns | **declared primary** |
| `A2_h53_off` | the four `H53_*` columns multiplied by a per-cell off-catalogue mask (Euclidean distance to the draw's *visible* catalogue ≥ 5 px) | isolates the off-catalogue increment (slate v6 §"Known risks") |
| `A3_h53_scarp` | `H53_PERSIST` and `H53_PERSIST × norm(H27_scarp)` | the conjunction with existing family-B scarp amplitude |

`norm(H27_scarp)` is exactly `Cell`/`Context`'s frozen H27 composite (`L_step_max × max(B_crest, B_trough)`
with each factor already percentile-scaled to `[0,1]` inside `Context.__post_init__`, so the product is in
`[0,1]` by construction); it is read from `Context.h27_scarp`, never rebuilt per cell and never re-scaled
per draw. All three
candidate arms use `extras=True, h27=True` (i.e. the frozen matrix with the same 69 columns the C0/C1
controls use) plus their own columns; the model is `HistGradientBoostingClassifier(**HGB_PARAMS)` from
`src/gemsdoe/experiment.py`, `random_state = draw`, as in every frozen stage here. The off-catalogue mask
is computed from `cell.known_c` (the visible catalogue inside the quadrant crop) — a legitimate
prediction-time input, exactly as family E uses it.

## 4. Draws, phases and the reproduction check

* **Fresh screen draws: 36 and 37** (`registry/draw_ledger.json`: `next_free_draw = 36`; draws 36/37 are
  unspent). Four quadrant folds × two draws × five arms = **40 cells**. This stage claims draws 36/37.
* **Control-reproduction phase (spent draws 20/21, disclosed):** the same runner first re-fits `C0_base`
  and `C1_geodesic_dots` on all four folds of draws 20/21 (8 cells, 2 arms) and compares them with the
  stored `evidence/h34_coverage_screen/cells.jsonl` values. This is the G4 integrity check; it uses
  spent draws and produces no promotion evidence. If the reproduction fails, the stage stops with
  **NOT COMPARABLE** and no verdict.
* Emission constants (unchanged from the frozen protocol): top-K budget `KFRAC = 0.0245` of the eroded
  domain, `MIN_DIST_PX = 2.4`, ridge NMS σ = 1.0, domain erosion 12 px, collar 15 px, `hide_frac = 0.20`.

## 5. Gates (frozen; identical in form to `knowledge/37`)

* **G1 effect.** Primary arm mean paired gain over `max(C0_base, C1_geodesic_dots)` **per fold**:
  mean ≥ **+0.005**, at least **3 of 4 folds positive in each draw**, worst fold ≥ **−0.010**, and the
  per-cell emitted-pixel budget ratio (primary ÷ C1) inside **[0.75, 1.25]**.
* **G2 level.** Primary arm mean DTI > the recorded bar **0.14479018210246675**.
* **G3 secondary proxy.** SGMC off-catalogue class (`derived_sgmc_faults_100m_u8.tif` minus catalogue
  minus its 300 m dilation, the H34 convention): mean gain ≥ **0.000** and ≥ **3 of 4** folds positive.
* **G4 integrity.** 40/40 fresh cells present and finite, and the spent-draw control reproduction with
  max |Δ| ≤ **1e-6**.
* **G5 viability (not inert).** Every `H53_*` column nonzero on ≥ **0.2 %** of the footprint, and the
  primary arm's emission differs from `C1_geodesic_dots` in at least **1 of 8** cells. (The H31 killer
  was sparsity; the opposite failure — a field that cannot change the emission — is equally fatal.)
* **G6 split accounting.** The `H53_*` columns are used in at least one split in ≥ **3 of 8** primary-arm
  cells (feature indices ≥ the base block only).

## 6. Decision rule (declared before the numbers exist)

* **G1 ∧ G2 ∧ G3** → **SLOT-ELIGIBLE**: build **at most one** cross-fitted artifact
  (`scripts/build_crossfit_candidate.py`, AGENTS.md rule 8) from the passing arm with the frozen emission;
  slot recommendation still requires the exact-file audit and the owner's approval.
* **G1 ∧ G2 ∧ ¬G3** → **PRIMARY PASS, SECONDARY-PROXY CONFLICT**: no promotion, exactly as H41 and H43
  closed; the artifact may be built only as a clearly labelled *research download* that is not slot-cleared.
* **¬G1** → **NO PROMOTION**; the family is recorded as screened and the next slate item (H50) becomes
  the top untried candidate. No re-tuning of `H53_*`, no fifth variant on the same draws.
* **¬G4** → **NOT COMPARABLE**, no verdict, environment investigated first.
* **¬G5 ∨ ¬G6** → **FAIL-INERT** with the measured rate recorded (the H31 precedent).

## 7. Honest prior and the bracket (judgement, never a gate)

The family base rate in this repository: 6 screened candidate stages, 2 reached a G1 pass (H41, H43), and
both were then vetoed by G3. The `hp30` design statistics (single-column off-catalogue AUC ≈ 0.59, top
decile *less* catalogue-adjacent than the DEM columns) are the best single-column numbers any candidate
in this slate has produced, but they are one spent draw and one quadrant. Declared bracket for the
primary arm's mean paired gain: **−0.010 to +0.012, most likely +0.001 to +0.004**; a G1 pass is
plausible, not the base case. Nothing here is a competition score: every number this stage produces is a
catalogue-gap **proxy**, and the DrivenData leaderboard is not contacted, fetched or polled
(`AGENTS.md` rule 3).

## 8. Known limits, declared in advance

1. The 100 m grid coarsens the 300 m window; the smallest window is close to the DEM's own texture scale.
2. Lithologic layering, bedding and dyke swarms also produce scale-persistent fabric. Arms A2 (off
   catalogue) and A3 (conjunction with scarp amplitude) exist precisely to test whether the *candidate*
   signal survives those alternatives; a positive A1 with negative A2/A3 would be read as "the model
   found a use for the columns that is not the off-catalogue lineament claim".
3. `H53_AGREE` alone is a weak discriminator (off-catalogue AUC 0.539) — the design audit says so; the
   arm is tested as a block, and a score driven only by `H53_COH_MIN` is reported as such.
4. The audit's variant choice was made on one spent draw; this is a design choice, disclosed, and the
   screen is on fresh draws, so the *evaluation* is not contaminated — but the *selection* is not
   independent, and any confirmation stage must keep that in mind.

# 27 — Preregistered H43 screen (drainage-network organization: stream-power residual and knickpoint excess), frozen 2026-10-03

Status: **frozen before any model is fit on real data.** Nothing in the parameter table, the arm
definitions, the gates, or the draw assignment may be edited after the screen summary exists. Any change of
intent must be recorded as a dated amendment with its own SHA-256-pinned evidence file; the original text
remains byte-identical.

## 1. Hypothesis and physical mechanism

Every topographic feature previously tested in this repository (`B_*`, `L_*`, `S_*`, `H27`, `H30`) is a
*local-window* operator on the 100 m detrended elevation or derived LiDAR grids. Drainage organization is a
*catchment-network* property: whether a pixel carries a channel (`A >= 25` cells = 2.5 km²), its stream-power
index (`Omega = A^m S`, with `m = 0.5`), and whether its local slope exceeds the smooth concave equilibrium
profile (`S propto A^-theta`, Flint 1974; Whipple & Tucker 1999) of its drainage basin depend on the entire
upslope catchment (`10^1–10^5` pixels). In extending Basin-and-Range half-grabens, active range-front and
relay faults pin knickpoints and focus stream power along footwall/hanging-wall transitions that local
curvature filters cannot separate from short-wavelength hillslope roughness.

Because the supplied catalogue and its static `B_*`/`L_*` blocks contain no hydrologic routing (verified by
repository-wide grep in `knowledge/25_candidates_v4_2026-10-03.md`), a boosted tree cannot synthesize
contributing area `A` from local slope/Laplacian splits. H43 tests whether supplying the routed catchment
network and its per-basin slope–area envelope residual improves holdout fault recovery at the frozen emission
budget.

## 2. Frozen inputs and parameters

Inputs (pinned in `registry/data_manifest.json` and derived by `scripts/prepare_data.py` +
`scripts/build_features.py` + `scripts/build_addons.py`):

| input | sha256 | role |
|---|---|---|
| `data/training_features.tif` (band 12 `det_elev`) | `4371c82e3b83bd4ac8e03923ce477293c987fc1b91e069bc1d16e54b1b8c600b` | source raster for `data/work/bands/12_det_elev.npy` (`sha256 739d6373125abf164e0f56163b8d9d02f651eb8d622decfe0360882085a0de32`) |
| `data/labels.tif` | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | label side; never read by `prepare_drainage`, and read by `build_h43_fields` only through the cell's `visible` catalogue mask |
| `data/sample_submission.tif` | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` | footprint and grid (`3730 x 3292`, 100 m, EPSG:32611, `5,167,373` valid footprint pixels) |
| `data/work/static_ABCD.npy` | `fe584a12ed3e1ed7d26b272c49f6da0bbe16e072d98f6b1694938d858305b084` | the 64-column cached static block |
| `data/work/addons.npy` | see `data/work/addons.npy.names.json` | the cached add-on columns |

Frozen parameters, implemented in `src/gemsdoe/h43.py::H43_PARAMS` and verified on `12_det_elev.npy` before
any model fit:

| parameter | value | rationale and measured diagnostic on `12_det_elev.npy` |
|---|---|---|
| `pit_eps` | `1e-6` | monotone step increment across flat/pit cells during priority-flood (Barnes, Lehman & Mulla 2014, doi:10.1016/j.cageo.2013.04.024); raises `876,389` pit cells inside the footprint and leaves `0` trapped interior cells (`outlet_mass_sum = 5,167,373.0` across `17,865` boundary outlets) |
| `slope_smooth_sigma_px` | `3.0` | 3-pixel (300 m) Gaussian pre-smoothing on nearest-valid-padded `det_elev` before `np.gradient`, suppressing 100 m pixel-step quantization noise without blurring range-front facets |
| `stream_power_m` | `0.5` | standard unit-stream-power area exponent (`Omega = A^0.5 * S`) |
| `min_channel_acc_px` | `25.0` | `25` cells (`2.5 km^2` catchment) validity threshold for channel pixels and knickpoint excess; selects `1,367,321` footprint pixels (`26.4607 %` of footprint) |
| `min_basin_channel_px` | `200.0` | minimum channel pixels (`acc >= 25`) in a single boundary-outlet basin to receive its own 16-bin repeated-median log-log `S-A` fit (`108` major basins); smaller boundary basins fall back to the 32-bin global footprint channel fit (`b1 = -0.144585`, concavity `theta = +0.144585`, `b0 = +0.546487`) |
| `knick_clip_pct` | `95.0` | positive `log10(slope) - fitted` residual on channel pixels is divided by its 95th percentile (`1.184093`) and clipped to `[0, 1]` |
| `off_catalogue_min_px` | `5.0` | `>= 500 m` (`5 px`) from every *visible* catalogue pixel defines the off-catalogue mask for `H43_OFF_FRONT` |
| `lnacc_scale_pct` | `99.9` | `log10(acc)` is scaled by its 99.9th footprint percentile (`5.000313`, `max_acc_px = 824,820.0`) and clipped to `[0, 1]` |
| `omega_lo_pct`, `omega_hi_pct` | `1.0`, `99.0` | `Omega` is linearly scaled between its 1st (`0.199045`) and 99th (`212.555717`) footprint percentiles and clipped to `[0, 1]` |
| `slope_floor` | `1e-4` | numerical floor on `slope` before `log10(slope)` in the `S-A` regression |

Boundary and leakage rules (enforced in `src/gemsdoe/h43.py` and tested in `tests/test_h43_features.py`):

1. **Catalogue-blind DEM fill and routing.** `prepare_drainage` takes only `elev` and `footprint`; the
   3,061 in-footprint NaNs of `12_det_elev.npy` (`IR-29-FOOTPRINT-DIFF`) are repaired by nearest-valid
   filling (`distance_transform_edt`), and only the outer 8-connected boundary of `footprint` seeds the
   priority-flood outlets. No quadrant boundary, eroded domain boundary, or catalogue pixel enters the
   hydrologic routing.
2. **Draw-isolated off-catalogue mask.** `H43_OFF_FRONT` multiplies `H43_KNICK` by
   `distance_transform_edt(~visible) >= 5.0`, using only the draw's *visible* catalogue mask. Hidden holdout
   labels never enter.

Degeneracy guard (pre-declared at `min_nonzero_fraction = 0.002` = `0.2 %` of footprint pixels):
measured before any model fit (using draw 99 fold NW for the draw-dependent column `H43_OFF_FRONT`, outside
every frozen screen/confirmation draw set), the footprint nonzero fractions (`> 1e-4`) are:

- `H43_LNACC`: `70.98 %` (`0.709770`)
- `H43_OMEGA`: `98.84 %` (`0.988365`)
- `H43_KNICK`: `13.33 %` (`0.133263`)
- `H43_OFF_FRONT`: `11.84 %` (`0.118367` on draw 99 fold NW)
- `H43_CHANNEL_SCARP`: `44.00 %` (`0.439995`)

Every column clears the `0.2 %` floor by `59x–494x`.

## 3. Columns (5, all `float32`, `[0, 1]`, zero outside the footprint)

1. `H43_LNACC` — `clip(log10(acc) / p99.9(log10(acc)), 0, 1)` over the footprint.
2. `H43_OMEGA` — `clip((Omega - p1) / (p99 - p1), 0, 1)` where `Omega = acc^0.5 * slope`.
3. `H43_KNICK` — `clip(max(log10(slope) - fitted_log10_slope, 0) / p95_pos_resid, 0, 1)` on channel pixels
   (`acc >= 25`), zero outside channels.
4. `H43_OFF_FRONT` — `H43_KNICK` restricted to pixels `>= 500 m` (`5.0 px`) from every *visible* catalogue
   pixel of the current draw.
5. `H43_CHANNEL_SCARP` — `clip(H43_OMEGA * h27_scarp, 0, 1)`, where `h27_scarp` is the draw-independent
   footprint-vector scarp composite (`ctx.h27_scarp`).

## 4. Arms, cells, draws, and frozen gates (G1, G2, G3)

Arms follow `knowledge/25_candidates_v4_2026-10-03.md` step 5 (`C0_base` + off-knickpoint-only +
`Omega`/area block + scarp-free union + full union), fit with the identical `HistGradientBoostingClassifier`
and frozen H34 C0 emission chain (`k_frac = 0.0245`, `min_dist_px = 2.4`, `DOMAIN_ERODE = 12`) used in
`knowledge/19` and `knowledge/24`:

| arm | H43 columns appended to `C0_base` | extra columns |
|---|---|---:|
| `C0_base` | none | 0 |
| `A1_h43_off_front` | `H43_OFF_FRONT, H43_KNICK` | 2 |
| `A2_h43_omega_area` | `H43_LNACC, H43_OMEGA, H43_CHANNEL_SCARP` | 3 |
| `A3_h43_scarp_free` | `H43_LNACC, H43_OMEGA, H43_KNICK, H43_OFF_FRONT` | 4 |
| `A4_h43_union` | `H43_LNACC, H43_OMEGA, H43_KNICK, H43_OFF_FRONT, H43_CHANNEL_SCARP` | 5 |

Cells: 4 blocked spatial folds (`NW, NE, SW, SE`) × 2 draws × 5 arms = 40 cells per stage.

Draws (verified against `registry/draw_ledger.json`, where `next_free_draw = 32` after H41 confirmation used
draws `30, 31`):

- **Screen draws:** `32, 33` (40 cells).
- **Confirmation draws (run only if at least one arm passes G1 on the screen):** `34, 35` (40 cells).

Frozen gates (copied explicitly from `knowledge/19_preregistered_h35_h40_screen_2026-10-03.md` §§4–5 so that
both primary-proxy and secondary-proxy clauses are machine-checked without omission, resolving
`IR-29-H41-G3-OMISSION` and `IR-29-H41-DANGLING-CANDIDATE-SCORE-RULE`):

- **G1 (screen gate, draws 32/33, must hold for confirmation to run):** per arm, across the 8 paired cells
  (4 folds × 2 draws), (a) mean paired ΔDTI vs `C0_base` ≥ **`+0.005`**, (b) paired ΔDTI > 0 on **≥ 3 of 4**
  folds in *each* draw (`min(positive_folds_per_draw) >= 3`), (c) worst single-fold mean gain ≥ **`-0.010`**,
  (d) all 8 cells present and finite with no viability-guard violations (`min_nonzero_fraction >= 0.002`),
  and (e) emitted dot count within **`[0.75, 1.25] ×`** the paired `C0_base` count in every cell.
- **G2 (confirmation gate, draws 34/35):** identical criteria (a)–(e) evaluated on fresh draws `34, 35` for
  an arm that passed G1.
- **G3 (promotion / slot-eligibility gate, evaluated only if G1 and G2 both pass for the same arm):**
  1. Both the screen mean DTI (draws 32/33) and the confirmation mean DTI (draws 34/35) must exceed the
     comparable spatial holdout best **`0.14479018210246675`** (`registry/status_feed.json`, `holdout_best`).
  2. The SGMC off-catalogue secondary proxy gain vs `C0_base` must be positive (`> 0`) on **≥ 3 of 4** folds
     on *both* the screen and the confirmation stages (`sgmc_positive_folds >= 3` in each stage).
  3. **Pre-declared proxy-conflict fork (`knowledge/19` §5):** any arm that beats `C0_base` on the
     catalogue-hidden primary proxy while its SGMC off-catalogue gain is positive on fewer than 3 of 4 folds
     (i.e. negative or zero on ≥ 2 of 4 folds) is reported as a proxy conflict (`IR-29-PROXY-CONFLICT`) with
     **no promotion** (`G3_ELIGIBLE = false`) and no weekly slot.
  4. Even if G1 + G2 + G3 all pass, a full-footprint candidate build must be scored on the H34 reference
     protocol (`evidence/candidate_scoreboard.json`) and pass the exact-file submission audit before any
     weekly slot is considered by the owner.

## 5. Deliverables and prohibitions

Stage deliverables: `evidence/h43_screen/{design_screen.json,cells_screen.jsonl,summary_screen.json,
analyzer_report.json}` (plus `_confirm` equivalents and `promotion_gate.json` if G1 authorizes confirmation),
generated by `scripts/run_h43_screen.py` and independently recomputed from raw cells by
`scripts/analyze_h43_screen.py`. Both scripts refuse a dirty worktree and refuse to overwrite existing
evidence.

Prohibited after the screen summary exists: re-tuning any parameter in §2, changing arm column sets, moving
the `0.002` sparsity floor or any G1/G2/G3 threshold, dropping a fold or draw, or presenting a primary-proxy
G1/G2 pass as slot eligibility without G3.

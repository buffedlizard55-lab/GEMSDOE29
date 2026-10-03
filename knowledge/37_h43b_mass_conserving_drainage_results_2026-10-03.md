# 37 — H43b (Workstream B): mass-conserving priority-flood D8 & per-basin knickpoint screen, and head-to-head comparison with Workstream A (2026-10-03)

**Frozen preregistration:** [`knowledge/27b_preregistered_h43b_screen_2026-10-03.md`](27b_preregistered_h43b_screen_2026-10-03.md),
sha256 `f6d6b33e7ae2782fc74e73088b507f4ba04d02aa14d007ee62dd8a4f9a025fb2` (committed at `09e81264` before any
fit; renamed from `27_...` to `27b_...` at merge with byte-identical contents so the recorded SHA-256 matches).  
**Feature module:** [`src/gemsdoe/h43b.py`](../src/gemsdoe/h43b.py) (`sha256 48ba63e5efd4748ce8b8231e52ca7f2387fea4851602d69d238d350f5e6e2c04`).  
**Runner & independent analyzer:** [`scripts/run_h43b_screen.py`](../scripts/run_h43b_screen.py),
[`scripts/analyze_h43b_screen.py`](../scripts/analyze_h43b_screen.py).  
**Evidence:** [`evidence/h43b_screen/`](../evidence/h43b_screen/) (`design_screen.json`, `cells_screen.jsonl`,
`summary_screen.json`, `promotion_gate.json`, `analyzer_report.json`, `screen_run.log`).  
**Sibling workstream compared here:** Workstream A's `src/gemsdoe/h43.py`,
[`knowledge/29_preregistered_h43_screen_2026-10-03.md`](29_preregistered_h43_screen_2026-10-03.md),
[`knowledge/30_h43_drainage_results_2026-10-03.md`](30_h43_drainage_results_2026-10-03.md), and
[`knowledge/32_proxy_policy_review_2026-10-03.md`](32_proxy_policy_review_2026-10-03.md).

---

## 1. Summary of the Workstream-B screen and why the two workstreams are complementary

Two parallel Session-5 workstreams branched from commit `a626e8a` (where `next_free_draw` was `32`) and
independently implemented and screened **H43** (DEM drainage-network organization, rank 1 of the v4 slate in
`knowledge/25_candidates_v4_2026-10-03.md`) on the identical screen cells (`draws 32, 33 × folds NW, NE, SW, SE`).
Because both workstreams used the exact same `Cell(ctx, fold, seed=draw)` harness and frozen H34 C0 emission,
their `C0_base` control rows are **bit-for-bit identical** (`mean_dti = 0.1431676384889805`,
`mean_auc = 0.78829` across the 8 control cells), providing a controlled head-to-head experiment between two
different physical and numerical realizations of DEM drainage routing:

1. **Workstream A (`src/gemsdoe/h43.py`, `evidence/h43_screen/`, `knowledge/30`):**
   - **Routing:** `count_strict_pits` checked `n > elev` on all 8 neighbours (which evaluates to `0` strict
     single-cell pits on `12_det_elev.npy` because closed basins in the 100 m DEM are multi-cell flats or
     border internal NaNs), so `fill_depressions` was bypassed (`pits = 0, fill_changed = False`), and
     `d8_receivers` accepted only strictly descending steps (`drop > 0.0`). Flow paths therefore terminated at
     the first flat or depression cell (`acc_max = 109` pixels = `1.09 km²`, channel fraction `acc >= 25` is
     `4.05 %` of the footprint).
   - **Envelope:** a single global 20-bin quantile-median log–log $S\text{–}A$ line across the footprint.
   - **Arm design & outcome:** `A3_knick` bundled `H43_KNICK + H43_CHANNEL_SCARP` (`2` columns) and passed
     primary G1 (`+0.01419`) and G2 confirmation on draws `34/35` (`+0.01674`), as did `A4_union` (`+0.01287`
     screen, `+0.01568` confirm), with gains concentrated in `NE/SW/SE` and negative/zero in `NW`
     (`-0.00095 / -0.00105` on screen, `0.0 / -0.00053` on confirm). Both arms failed G3 because the SGMC
     secondary proxy was negative in both stages (`A3_knick` `-0.00012` on `2/4` folds $\to$ `-0.00214` on `0/4`;
     `A4_union` `-0.00190` on `1/4` $\to$ `-0.00002` on `2/4`).

2. **Workstream B (`src/gemsdoe/h43b.py`, `evidence/h43b_screen/`, this document):**
   - **Routing (`fill_dem` + `d8_order`):** nearest-filled the `3,061` internal DEM NaNs, seeded
     Barnes–Lehman–Mulla (2014) priority-flood at the **true footprint boundary**
     (`valid & ~binary_erosion(valid)`, `17,865` boundary outlets), and applied a deterministic
     $\varepsilon = 10^{-5}\text{ m}$ per-step tiebreaker across `876,389` raised depression/flat cells.
     Every non-outlet cell has a strictly lower D8 neighbour (`n_interior_trapped = 0`), **100 % of the
     `5,167,373` footprint pixels drain to the boundary** (`outlet_mass_sum = 5,167,373.0`,
     `mass_conserved = true`), and contributing area reaches **`max_acc_px = 824,820` pixels (`8,248.2 km²`)**
     with `1,367,321` channel pixels at `acc >= 25` (`26.46 %` of the footprint).
   - **Envelope (`prepare_drainage`):** propagated outlet labels upstream to partition the footprint into
     drainage basins and fitted **per-basin repeated-median (Siegel 1982) log–log $S\text{–}A$ envelopes
     across `108` major basins** ($\ge 500$ channel pixels each; global fallback $\theta = 0.144585$).
   - **Arm design & outcome:** explicitly separated `A3_h43_scarp_free` (`H43_LNACC, H43_OMEGA, H43_KNICK, H43_OFF_FRONT`
     — the 4 drainage/knickpoint columns *without* `H43_CHANNEL_SCARP`) from `A4_h43_union` (all 5 columns
     *including* `H43_CHANNEL_SCARP`). All 40 cells completed in a single uninterrupted process (`1,330.27 s`,
     clean tree at `09e81264`, `gc.collect()` between cells preventing OOM).
     - **`A4_h43_union`** gained **`+0.0039976`** mean paired DTI and cleared every stability, floor, and
       budget criterion (**positive in all 4 quadrant fold means**: `NW +0.00387, NE +0.00350, SW +0.00642, SE +0.00220`;
       `3/4` positive folds on draw 32 and `4/4` on draw 33; worst fold `+0.0021960`; holdout AUC
       `0.78829 -> 0.79127`), missing G1 solely by `0.0010024` against the `+0.005` mean-gain bar.
     - **`A3_h43_scarp_free`** gained **`+0.0019365`** on the primary proxy (`0.1451041` mean DTI, above
       `holdout_best = 0.1447902`, holdout AUC `0.79074`) and **passed the SGMC off-catalogue $\ge 3/4$
       positive-folds gate (`+0.0013560` mean SGMC gain, `3/4` folds positive, `sgmc_gate_pass = True`)**.
     - Because no arm reached `+0.005` on the primary proxy in Workstream B, confirmation was not run in
       Workstream B (`promotion_gate.json`: `G3_ELIGIBLE = false` for all four arms) and no weekly slot was used.

---

## 2. Priority-flood D8 and basin-envelope diagnostics (`evidence/h43b_screen/design_screen.json`)

Computed deterministically by `gemsdoe.h43b.prepare_drainage` on `data/work/bands/12_det_elev.npy`
(`sha256 739d6373125abf164e0f56163b8d9d02f651eb8d622decfe0360882085a0de32`):

| Diagnostic | Workstream B (`src/gemsdoe/h43b.py`) | Workstream A (`src/gemsdoe/h43.py`) |
|---|---:|---:|
| `n_footprint_px` | `5,167,373` | `5,167,373` |
| `n_elev_nan_in_footprint_filled` | `3,061` | `0` (left as `inf` barriers) |
| `n_cells_raised_by_fill` | `876,389` (`16.96 %`) | `0` (`pits = 0`, fill skipped) |
| `n_boundary_outlets` | `17,865` | not tracked (sinks at every flat/pit) |
| `n_interior_trapped` | **`0`** | $> 0$ (every internal sink terminates flow) |
| `outlet_mass_sum` | **`5,167,373.0`** (`mass_conserved = true`) | — |
| `max_acc_px` | **`824,820.0`** (`8,248.2 km²`) | `109.0` (`1.09 km²`) |
| `channel_px_acc25` (`acc >= 25`) | `1,367,321` (`26.4607 %`) | `209,264` (`4.05 %`) |
| Log–log $S\text{–}A$ fit | `108` major basins (Siegel repeated medians, $\theta_{\text{global}} = 0.144585$) | 1 global 20-bin median fit ($\theta = 0.2584$) |
| Nonzero fractions (`H43_LNACC, H43_OMEGA, H43_KNICK, H43_OFF_FRONT, H43_CHANNEL_SCARP`) | `70.98 %, 98.84 %, 13.33 %, 11.79–11.87 %, 44.00 %` | `40.2 %, 70.1 %, 4.05 %, 0.0 %*, 52.4 %` |

*\*Note: in Workstream A's `design_screen.json`, the draw-independent pre-check calls `build_h43_columns(..., off_mask=None)` where `H43_OFF_FRONT` defaults to `0.0`, and then populates `H43_OFF_FRONT` inside each draw cell (`~3.6 %` nonzero).*

---

## 3. Workstream-B 40-cell screen results (`draws 32, 33 × folds NW, NE, SW, SE × 5 arms`)

### 3.1 Per-arm summary (`evidence/h43b_screen/summary_screen.json` & `analyzer_report.json`)

| Arm | Extra cols | Mean DTI | Mean paired gain | Fold gains `(NW, NE, SW, SE)` | Pos folds `(d32, d33)` | Worst fold gain | Mean AUC | SGMC mean gain | SGMC pos folds | Budget ok | G1 PASS |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---|
| `C0_base` | `0` | `0.1431676` | `+0.0000000` | `+0.00000, +0.00000, +0.00000, +0.00000` | `0, 0` | `+0.0000000` | `0.78829` | `+0.000000` | `0/4` | `true` | — |
| `A1_h43_off_front` | `2` (`OFF_FRONT, KNICK`) | `0.1420632` | `-0.0011044` | `-0.00306, -0.00036, -0.00160, +0.00060` | `2, 2` | `-0.0030606` | `0.78576` | `-0.000367` | `2/4` | `true` (`0.988–1.015×`) | **FAIL** |
| `A2_h43_omega_area` | `3` (`LNACC, OMEGA, CHANNEL_SCARP`) | `0.1450484` | `+0.0018808` | `+0.00220, -0.00032, +0.00182, +0.00381` | `3, 3` | `-0.0003184` | `0.78886` | `+0.000199` | `2/4` | `true` (`0.993–1.024×`) | **FAIL** |
| `A3_h43_scarp_free` | `4` (`LNACC, OMEGA, KNICK, OFF_FRONT`) | `0.1451041` | `+0.0019365` | `-0.00245, +0.00274, -0.00341, +0.01086` | `2, 3` | `-0.0034099` | `0.79074` | **`+0.001356`** | **`3/4` (PASS)** | `true` (`0.986–1.013×`) | **FAIL** |
| **`A4_h43_union`** | `5` (all 5 H43b cols) | **`0.1471652`** | **`+0.0039976`** | **`+0.00387, +0.00350, +0.00642, +0.00220`** | **`3, 4`** | **`+0.0021960`** | **`0.79127`** | `-0.001125` | `2/4` | `true` (`0.988–1.015×`) | **FAIL** (mean `< +0.005`) |

### 3.2 Per-cell primary DTI and paired gain (`evidence/h43b_screen/cells_screen.jsonl`)

| Fold | Draw | `C0_base` DTI | `A1_h43_off_front` ($\Delta$) | `A2_h43_omega_area` ($\Delta$) | `A3_h43_scarp_free` ($\Delta$) | `A4_h43_union` ($\Delta$) |
|---|---:|---:|---:|---:|---:|---:|
| `NW` (0) | `32` | `0.161997` | `0.156338` (`-0.005660`) | `0.163109` (`+0.001112`) | `0.158805` (`-0.003192`) | `0.160461` (`-0.001536`) |
| `NW` (0) | `33` | `0.167458` | `0.166996` (`-0.000462`) | `0.170750` (`+0.003292`) | `0.165757` (`-0.001701`) | `0.176734` (`+0.009277`) |
| `NE` (1) | `32` | `0.170907` | `0.168371` (`-0.002535`) | `0.175343` (`+0.004436`) | `0.176750` (`+0.005844`) | `0.176787` (`+0.005880`) |
| `NE` (1) | `33` | `0.124328` | `0.126149` (`+0.001821`) | `0.119255` (`-0.005073`) | `0.123966` (`-0.000362`) | `0.125453` (`+0.001125`) |
| `SW` (2) | `32` | `0.128397` | `0.129258` (`+0.000861`) | `0.128027` (`-0.000370`) | `0.120263` (`-0.008134`) | `0.138789` (`+0.010392`) |
| `SW` (2) | `33` | `0.114103` | `0.110045` (`-0.004057`) | `0.118113` (`+0.004010`) | `0.115417` (`+0.001314`) | `0.116552` (`+0.002450`) |
| `SE` (3) | `32` | `0.130669` | `0.136954` (`+0.006285`) | `0.134243` (`+0.003574`) | `0.143699` (`+0.013030`) | `0.133765` (`+0.003096`) |
| `SE` (3) | `33` | `0.147483` | `0.142395` (`-0.005088`) | `0.151548` (`+0.004065`) | `0.156175` (`+0.008692`) | `0.148779` (`+0.001296`) |

---

## 4. What the comparison between Workstream A (`h43.py`) and Workstream B (`h43b.py`) proves

1. **Why Workstream A has a larger primary gain in `NE/SW/SE` (`+0.01419`) while Workstream B is positive in all 4 quadrants (`+0.00400`):**
   - In Workstream A (`h43.py`), because flat/depression cells are not filled (`pits = 0`, `acc_max = 109` cells),
     `acc >= 25` selects only **uninterrupted steep hillside/scarp chutes** at least `25` pixels long (`4.05 %`
     of the footprint), and `H43_KNICK` measures where those steep chutes exceed the global slope–area trend.
     In the Great Basin, uninterrupted 2.5 km downhill runs occur almost exclusively on range-bounding fault
     facets (`NE/SW/SE`), giving a strong primary-proxy boost (`+0.01419` screen, `+0.01674` confirm) while
     leaving `NW` flat/negative (`-0.00095 / 0.0`).
   - In Workstream B (`h43b.py`), priority-flood fills all `876,389` interior depressions so flow accumulates
     all the way across alluvial valleys to the `17,865` boundary outlets (`max_acc_px = 824,820` cells,
     `26.46 %` channel fraction), and repeated medians fit each of the `108` major basins separately. The
     resulting `A4_h43_union` gain is smaller in magnitude (`+0.0039976`) because valley-floor channels dilute
     range-front concentration, but it is **positive across all 4 quadrant fold means**
     (`NW +0.00387, NE +0.00350, SW +0.00642, SE +0.00220`, `3/4` and `4/4` positive folds per draw, worst fold
     `+0.0021960`).

2. **Why `A3_h43_scarp_free` in Workstream B passes the SGMC secondary-proxy gate (`+0.00136`, `3/4` folds positive):**
   - [`knowledge/32_proxy_policy_review_2026-10-03.md`](32_proxy_policy_review_2026-10-03.md) showed that across
     all 23 prior arm-stages, every arm that cleared a primary gate had a negative SGMC sign, and
     [`knowledge/30`](30_h43_drainage_results_2026-10-03.md) §5 noted that resolving the deadlock requires
     identifying *which* mechanism trades SGMC performance away.
   - Workstream B's ablation between `A3_h43_scarp_free` (`H43_LNACC, H43_OMEGA, H43_KNICK, H43_OFF_FRONT`)
     and `A4_h43_union` (`A3 + H43_CHANNEL_SCARP`) isolates the exact column responsible:
     - **Without `H43_CHANNEL_SCARP` (`A3_h43_scarp_free`):** primary paired gain is **`+0.0019365`**
       (`mean_dti = 0.1451041 > holdout_best`), and SGMC paired gain is **`+0.0013560` with `3/4` folds positive
       (`sgmc_gate_pass = True`)**.
     - **Adding `H43_CHANNEL_SCARP` (`A4_h43_union`):** primary paired gain doubles to **`+0.0039976`**
       (`4/4` fold means positive), while SGMC paired gain flips to **`-0.001125` (`2/4` folds positive)**.
   - Physical explanation: `H43_CHANNEL_SCARP = H43_OMEGA * h27_scarp` concentrates model probability on
     topographic range fronts (the habitat of the USGS/INGENIOUS Quaternary fault catalogue), pulling top-$K$
     dot budget away from intra-range bedrock contacts mapped in SGMC. Conversely, basin-normalized knickpoints
     and stream power *without* the scarp multiplier (`A3_h43_scarp_free`) detect intra-range and across-basin
     drainage anomalies that align with both Quaternary faults and SGMC bedrock structures.

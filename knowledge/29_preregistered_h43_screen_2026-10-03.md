# 29 — Preregistered H43 screen (drainage-network organization), frozen 2026-10-03

Status: **frozen before any model is fitted on these columns.** The column definitions, the parameter table,
the arm wiring, the gates and the draw assignment may not be edited after `evidence/h43_screen/summary_screen.json`
exists. A change of intent is recorded as a dated amendment with its own sha-pinned evidence file; the original
text stays.

## 1. Hypothesis and mode

**H43:** in an extending range the locus of active faulting is also the locus of the topographic boundary
condition — water leaves along the front — and the *network* statistics of the 100 m surface (contributing
area, its residual steepness) carry structural information that no local window of the supplied bands can
reproduce. Concretely: stream-power concentration and positive knickpoint residual along a range front mark
the front's active segments, including segments the supplied USGS/INGENIOUS catalogue does not carry.

Mode of gain: **prior shape**. The metric is credit-density-limited (`knowledge/07` §2–§4): a feature pays
either by moving emitted mass onto pixels that become dots or by improving the ranking inside the corridor
the emission stage already scans. This screen measures the composite effect at the frozen emission budget.

Why it is not already in the repository (checked, not asserted): the supplied stack contains point/edge
catalogue products and local terrain derivatives; **there is no flow routing anywhere in `src/` or
`scripts/`** — `grep -rniE "flow_accum|contributing|knickpoint|stream_power|d8" src scripts tests` matches
only this new module and its tests. Drainage integration is a network property (every channel cell needs its
whole catchment), so no re-weighting of a local window can produce it. The L_*/B_* static columns encode
ridge/valley *morphology*; H43's increment is the network part.

Difference from repo work: H27/H30 filtered the scarp inside catalogue geometry; H31/H40/H31b filtered
potential-field ridges (persistence with height — three negative verdicts, `knowledge/22`); H35 built
interaction zones between catalogue segments; H41 used an external young-fault inventory (label side). H43
is the first candidate to use the **topographic boundary condition** as an independent structural probe.

## 2. Frozen inputs

| input | sha256 (prefix) | role |
|---|---|---|
| `data/work/bands/12_det_elev.npy` | see `data/work/design_h43.json` | the cached 100 m surface band (`det_elev`), 5,164,312 finite of 5,167,373 footprint pixels |
| `data/work/bands/_footprint.npy` | idem | footprint mask (5,167,373 px) |
| `data/labels.tif` | `7ba308ccdc44…` | catalogue; read only through `Cell` visibility masks and the off-catalogue mask |
| `data/sample_submission.tif` | `2176d08e485a…` | grid (3730×3292, 100 m, EPSG:32611) |
| `data/work/static_ABCD.npy` + `.names.json` | idem | the 64-column frozen static block used by every arm |
| `data/work/addons.npy` + `.names.json` | idem | the S/G/E/H27 add-on block |
| `data/external/derived_sgmc_faults_100m_u8.tif` | `643cbe992ef4…` | second-proxy truth class (reported, not a screen gate) |

Datum caveat carried from `knowledge/25`: `det_elev` is a **detrended** surface spanning −590…+1470 m with
unknown vertical datum, so only relative topography is used, no absolute gradient or discharge is claimed.

## 3. Frozen parameters (implemented once in `src/gemsdoe/h43.py`)

| name | value | rationale (declared, never re-tuned) |
|---|---|---|
| `NEIGHBOURS` | 8-connected, distances 1 / √2 | D8 routing; ties broken by the fixed neighbour order, so the field is deterministic |
| `CHANNEL_MIN_CELLS` | 25 cells | channel definition; **correction of a unit error in `knowledge/25`**, which called 25 cells "2.5 km²" — 25 × (100 m)² = **0.25 km²**. The number is kept as written in the slate; the area statement is corrected and disclosed as IR-29-H43-AREA-UNIT |
| `SLOPE_SIGMA_PX` | 1.0 px Gaussian pre-smooth | the slate's "3-pixel Gaussian" was read as a ±1 px (σ=1) kernel so the channel slope is not smoothed away; disclosed as IR-29-H43-SLOPE-KERNEL |
| `OMEGA_M` | 0.5 | Ω ∝ A^0.5·S unit-coefficient proxy (m ≈ 0.5 in the stream-power literature); *not* a discharge claim |
| `KNICK_BINS` | 20 quantile bins of log10 A | binned-median robust fit of log10 S on log10 A; deterministic, no RNG, no optimiser |
| `min positives per bin` | 25 | a bin with fewer members is dropped before the fit |
| knickpoint normaliser | 95th percentile of the **positive** residuals | refinement of `knowledge/25`'s "clipped at its 95th percentile" after the synthetic test showed a plain q95 over all channel pixels collapses to 0 whenever fewer than 5 % of channels have a positive residual; disclosed as IR-29-H43-KNICK-NORMALISER |
| `h27_scarp` | `gemsdoe.experiment.Context.h27_scarp` | the frozen H27 scarp composite used by every screen since session 3; no new construction |
| off-catalogue mask | ≥ 5 px (500 m) from **visible** catalogue pixels | identical to H41's `off_catalogue_min_px`; uses the visible catalogue only, so the holdout enters only by *removing* information |

**Deviation from the slate's plan, disclosed:** `knowledge/25` §H43.3 proposed per-basin log-log fits; this
preregistration uses **one global binned-median fit**. Reason: per-basin attribution on a detrended surface
(a basin label per one of 21,164 filled pits, on a grid whose absolute datum is unknown) is a second
uncontrolled modelling choice inside a single screen, and the arm design already isolates the residual's
information content. Disclosed as IR-29-H43-FIT-SIMPLIFICATION.

**Viability measurements taken before freezing** (these are diagnostics of the *inputs*, not results of the
screen; they are reported in `evidence/h43_screen/design_screen.json`):

* strict 3×3 pits on the raw band: **21,164** → `fill_depressions` ran and changed the surface;
  `max_uphill_step = 0.0` after filling (the receiver graph is strictly descending, hence acyclic).
* channel pixels (acc ≥ 25 cells): **416,542 = 8.07 %** of the footprint — 40× the 0.2 % viability floor
  that H31 failed, so the H31 sparsity failure mode does not apply here.
* positive-residual pixels: 209,479 (50.3 % of channel pixels); knickpoint q95 = 0.6516 (log10 units).
* fitted concavity: θ = 0.184, intercept = 1.096 — below the 0.3–0.9 literature range, consistent with a
  detrended 100 m surface, and reported as a property of the input, not as a calibration.
* nonzero fractions: `H43_LNACC` 40.2 %, `H43_OMEGA` 70.2 %, `H43_KNICK` 4.06 %.
* column build time: 32.7 s single-core on this checkout.

## 4. Columns (5, `float32`, [0, 1], zero outside the footprint)

1. `H43_LNACC` — log10(contributing cells) / its 99.9th footprint percentile, clipped to [0, 1].
2. `H43_OMEGA` — Ω ∝ A^0.5·S, scaled to [0, 1] by its own 99.9th percentile over channel pixels.
3. `H43_KNICK` — positive residual of log10 S over the fitted concave profile, normalised by its 95th
   percentile; zero off-channel.
4. `H43_OFF_FRONT` — `H43_KNICK` × (≥ 500 m from the **visible** catalogue), recomputed per draw.
5. `H43_CHANNEL_SCARP` — `H43_OMEGA` × `ctx.h27_scarp` (stream-power concentration co-located with a
   crest/trough scarp signal).

Degeneracy guard (pre-declared, the H31 lesson): every column used by an arm must be nonzero on **≥ 0.2 %**
of footprint pixels in every cell; a violation aborts the stage with a recorded reason rather than producing
a silent null.

## 5. Arms, cells, gates, draws

`C0_base` + four arms, evaluated on the frozen `Cell` machinery (`src/gemsdoe/experiment.py`) with
`extras=True, h27=True` — the exact control layout every screen in this family has used since H34:

| arm | H43 columns added |
|---|---|
| `C0_base` | none (frozen H34 C0 control) |
| `A1_off` | `H43_OFF_FRONT` |
| `A2_network` | `H43_LNACC`, `H43_OMEGA` |
| `A3_knick` | `H43_KNICK`, `H43_OFF_FRONT` |
| `A4_union` | all five |

Cells: 4 quadrant folds × 2 draws = 8 cells per arm, 40 cells per stage. Screen draws **32/33** — the two
draws `registry/draw_ledger.json` records as the next free pair (nothing has fitted them). Confirmation
draws 34/35 are authorized *only* if at least one arm passes G1; otherwise the confirmation command exits
before fitting anything.

Gates, identical to `knowledge/24` §4 (the family's frozen gates, unchanged):

* **G1 (screen pass):** mean paired DTI gain vs `C0_base` on the same cell ≥ **+0.005**; ≥ **3 of 4** folds
  positive in **each** draw; worst fold ≥ **−0.010**; emission budget within **0.75–1.25×** the control's;
  8 cells present per arm.
* **G2 (confirmation):** the same arithmetic on the fresh draws, per arm that passed G1.
* **G3 (promotion, inherited from `knowledge/19` §4):** the SGMC off-catalogue secondary class must gain on
  ≥ 3 of 4 folds in **both** stages; it is reported here but does not affect the screen verdict. No arm can
  be promoted on the primary proxy alone; that is the rule that cost H41 its own passing result.
* **Slot rule:** unchanged — a weekly slot requires beating `holdout_best = 0.14479018210246675` *on the
  protocol that produced it* (the H34 cells, draws 20/21) **and** passing G1+G2+G3. Nothing in this screen
  can clear that rule by itself.

## 6. Declared ceilings and falsifiers

* **Resolution:** at 100 m a knickpoint is 1–3 pixels; the honest unit called out in `knowledge/25` is the
  *basin/front* statistic, not the pixel. A pass would therefore be corridor-ranking evidence, and this
  screen cannot resolve a 30 m scarp.
* **Detrended input:** routing down a detrended surface is a topographic proxy, not a surveyed hydrologic
  network. If the column carries information it is because drainage organization still correlates with
  structure, not because the proxy discharges are real.
* **Falsifiers:** (i) all four arms fail G1 → the drainage channel carries no incremental information for
  the frozen habitat under this protocol; (ii) an arm passes but its SGMC secondary class moves the wrong
  way in both stages → same proxy-conflict outcome as H41 (`knowledge/26` §5); (iii) a guard violation →
  the stage is void, not negative.
* **No re-tuning after the fact.** Parameters are frozen above; a null result is reported as a null result.

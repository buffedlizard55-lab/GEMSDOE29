# 30 — H43 drainage-network results (2026-10-03)

Frozen protocol: [`knowledge/29`](29_preregistered_h43_screen_2026-10-03.md), sha256 `919210d9dad7ccd0…`
(recorded in `evidence/h43_screen/design_screen.json` together with the module and input hashes).
Runner: `scripts/run_h43_screen.py`. Independent checker: `scripts/analyze_h43_screen.py`
(`evidence/h43_screen/analyzer_report.json`, **integrity problems: 0**).
Raw cells: `evidence/h43_screen/cells_screen.jsonl` (40 rows); runner summary:
`evidence/h43_screen/summary_screen.json`.

**This is a proxy result, not a competition score.** The DTI values below are the repository's spatially
blocked catalogue-hidden proxy on draws 32/33; the second proxy is the SGMC off-catalogue class. Nothing here
was submitted and no weekly slot was used.

## 1. Execution record (read this before the numbers)

The first launch (commit `a244032`) was killed by the container OOM killer after 23 of 40 rows. Its partial
evidence was quarantined — not deleted — under
`evidence/history/h43_screen_oom_partial_2026-10-03/`, because resuming it would have mixed two different
`det_elev` arrays (the cached band recorded at launch no longer reproduced from the pinned GeoTIFF; see
`IR-29-H43-INPUT-DRIFT` and that directory's README for the hash table).

The stage recorded here was therefore re-run **from scratch under the same frozen preregistration** (same
draws 32/33, folds, arms, seeds, gates; the preregistration file was never edited), staged into 2-cell
processes (`--max-cells 2`, ten rows per process) so that no single process exceeds the 3.9 GB container.

Process accounting, from the raw-cell file's git history rather than from the runner's own counter: after the
quarantine reset the file was empty (`87ecc24`), and rows were appended in three committed batches —
10 rows at the merge (`ca271ba`), 20 rows with the resume-guard patch (`910dffd`), 40 rows at close-out
(`bd6811e`). Since one process can append at most two cells (ten rows), that is **four process episodes: the
launch plus three `--resume` continuations**. The summary's `execution` block says
`processes: 2, resumed: true, rows_this_process: 10`; that counter is the runner's own formula (launch, plus
one if any rows already existed) and therefore *under*-counts staged runs — read it as a lower bound, not a
census. This is covered by `IR-29-H43-STAGED-EXECUTION`.

Provenance detail, disclosed rather than smoothed over: the first continuation ran under the merge revision
and **rewrote `design_screen.json`** (the "keep the launch design" guard was added only afterwards, in
`910dffd`). The rewrite is visible in that commit's diff: `build_seconds` 35.12 → 32.04 and the recorded
revision `c89e0e27…` → `ca271bae48…`. So the design file now labels the whole stage with the merge revision
while the launch process — and the first ten rows — ran under `c89e0e2`. What is *not* recoverable: per-row
git revisions are not recorded, so the revision of each individual row cannot be proven from the evidence;
only the launch revision is known from the pre-rewrite design. What is verified: the module hashes recorded
in the design are byte-identical between those revisions (`src/gemsdoe/*` was untouched by the merge), every
continuation re-verified them before appending a row, and the analyzer re-checks the preregistration hash.
The 40 rows therefore share one feature definition and one input set. Also disclosed: cells that can be
compared against the quarantined stage reproduce to four decimals, which is consistent with — but does not
prove — the input drift being numerically inert.

## 2. Screen results, 40/40 cells (draws 32/33 × four quadrant folds × five arms)

Per-cell proxy DTI (C0 / A1_off / A2_network / A3_knick / A4_union):

| fold | draw | C0_base | A1_off | A2_network | A3_knick | A4_union |
|---|---|---:|---:|---:|---:|---:|
| NW | 32 | 0.1620 | 0.1620 | 0.1564 | 0.1620 | 0.1618 |
| NW | 33 | 0.1675 | 0.1656 | 0.1706 | 0.1656 | 0.1657 |
| NE | 32 | 0.1709 | 0.1809 | 0.1649 | **0.1860** | 0.1801 |
| NE | 33 | 0.1243 | 0.1278 | 0.1192 | **0.1481** | 0.1480 |
| SW | 32 | 0.1284 | 0.1346 | 0.1278 | 0.1412 | 0.1482 |
| SW | 33 | 0.1141 | 0.1248 | 0.1143 | 0.1320 | 0.1291 |
| SE | 32 | 0.1307 | 0.1264 | 0.1247 | 0.1483 | 0.1397 |
| SE | 33 | 0.1475 | 0.1553 | 0.1567 | 0.1757 | 0.1758 |

Arm arithmetic recomputed from the raw rows (fold gain = arm fold mean − control fold mean; the frozen gate
needs mean ≥ +0.005, ≥3/4 folds positive **per draw**, worst fold ≥ −0.010 and a 0.75–1.25× emission-budget
ratio):

| arm | mean gain | fold gains (NW, NE, SW, SE) | positive folds per draw | worst fold | budget | mean DTI | mean AUC | G1 |
|---|---:|---|---|---:|---:|---|---:|---:|---|
| A1_off (1 col) | +0.00401 | −0.00095, +0.00677, +0.00844, +0.00179 | 2, 3 | −0.00095 | ok | 0.14718 | 0.7935 | FAIL |
| A2_network (2 cols) | −0.00136 | −0.00131, −0.00552, −0.00023, +0.00162 | 0, 3 | −0.00552 | ok | 0.14181 | 0.7894 | FAIL |
| **A3_knick (2 cols)** | **+0.01419** | −0.00095, +0.01946, +0.01531, +0.02292 | **3, 3** | −0.00095 | ok | 0.15735 | 0.7963 | **PASS** |
| **A4_union (5 cols)** | **+0.01287** | −0.00105, +0.01646, +0.01736, +0.01869 | **3, 3** | −0.00105 | ok | 0.15603 | 0.7957 | **PASS** |
| C0_base (control) | — | — | — | — | — | 0.14317 | 0.7883 | — |

Sparse-column (viability) guard: **passed** — the five H43 columns are non-zero on 40.2 % / 70.1 % / 4.05 % /
0.0 % / 52.4 % of footprint pixels against a 0.2 % floor; the column build took 32.0 s.
A2_network (`H43_LNACC`+`H43_OMEGA`) is *negative* — raw drainage density is not the signal; the signal sits
in the **knickpoint residual** (`H43_KNICK`) and in the union.

## 3. What the screen does and does not license

* **Does:** both knickpoint-bearing arms clear the frozen G1 gate with roughly 2.5–2.8× the required effect
  size, in both draws, with the −0.010 worst-fold floor respected by a factor of ~10, and the confirmation
  stage on draws 34/35 is authorized by the runner (it exits before any fit otherwise).
* **Does not:** the SGMC second proxy moves *negative* for both passing arms (A3 −0.00012, 2/4 folds; A4
  −0.00190, 1/4 folds). That is the same proxy conflict that withheld H41 promotion
  (`IR-29-H41-G3-OMISSION`), and it must be carried in every sentence that quotes the +0.014.
* The surface is a **detrended** elevation band of unknown datum: the routing is "down the cached surface",
  a topographic proxy, not a surveyed hydrologic network, and no discharge is claimed.

## 4. Confirmation stage (draws 34/35)

Frozen design: `evidence/h43_screen/design_confirm.json` (git `bd6811e4`, clean tree, draws 34/35).
The runner prints `confirmation authorised for: ['A3_knick', 'A4_union']` as an authorisation *flag* only —
it then runs the **full 5-arm × 4-fold × 2-draw matrix (40 cells) on the fresh draws**, so draws 34/35
replicate the whole screen, including the arms that failed G1. Those two arms are replication controls here,
not promotion candidates; promotion still requires G1 on both draw pairs plus the inherited G3
secondary-proxy requirement. The stage is complete; `scripts/analyze_h43_screen.py` re-derives every gate
from the raw rows into `evidence/h43_screen/analyzer_report.json` (both stages, `integrity_problems: 0`) and
the verdict is recorded in §5 below.

## 5. Confirmation verdict (draws 34/35, 40/40 cells)

Status: **complete**. Raw rows `evidence/h43_screen/cells_confirm.jsonl` (40), runner summary
`evidence/h43_screen/summary_confirm.json`, design `evidence/h43_screen/design_confirm.json` (git
`bd6811e4`, sha256 `54651fe6…`, draw-independent module/input hashes identical to the screen). The
independent checker re-derived every gate from the raw rows and cross-checked the summary:
`evidence/h43_screen/analyzer_report.json` now carries both stages — its `screen` section is
**bit-identical** to the pre-confirmation report (verified by JSON equality) and `integrity_problems: 0`.

| arm | screen mean (d32/33) | **confirm mean (d34/35)** | confirm fold gains (NW, NE, SW, SE) | positive folds per draw | worst fold | mean DTI | mean AUC | SGMC confirm | primary gates (G1+G2) | G3 secondary |
|---|---:|---:|---|---|---:|---:|---:|---|---|---|
| `A1_off` | +0.00401 | −0.00060 | 0.0, −0.00105, −0.00212, +0.00076 | 1, 1 | −0.00212 | 0.13696 | 0.78574 | +0.00113 (2/4) | FAIL | — |
| `A2_network` | −0.00136 | +0.00408 | +0.00745, +0.00307, +0.00254, +0.00327 | 3, 4 | +0.00254 | 0.14164 | 0.78911 | +0.00064 (3/4) | FAIL (mean < +0.005) | — |
| **`A3_knick`** | +0.01419 | **+0.01674** | 0.0, +0.02213, +0.01964, +0.02519 | 3, 3 | 0.0 | 0.15430 | 0.79370 | **−0.00214 (0/4)** | **PASS** | **FAIL** |
| **`A4_union`** | +0.01287 | **+0.01568** | −0.00053, +0.01690, +0.02489, +0.02145 | 3, 4 | −0.00053 | 0.15324 | 0.79164 | −0.00002 (2/4) | **PASS** | **FAIL** |
| `C0_base` | 0.14317 | 0.13756 | — | — | — | 0.13756 | 0.78481 | — | — | — |

Emission budget inside band in every cell (confirm emissions 7,148–9,586 dots), viability guard passed
(`problems: []`), and the NW fold is structurally identical between `A3_knick` and the control on both
confirmation draws (fold gain exactly 0.0) — the replication again lives in NE/SW/SE.

**Verdict: the primary-proxy result replicated on both fresh draws, and the inherited G3 requirement
withholds promotion for every arm — identical in structure to H41.**

1. **Both knickpoint-bearing arms replicated, slightly larger than the screen** (+0.01674 vs +0.01419 for
   `A3_knick`; +0.01568 vs +0.01287 for `A4_union`), each positive in 3/4 folds on both fresh draws, worst
   folds 0.0 and −0.00053 against the −0.010 floor, budgets inside 0.75–1.25×. On the catalogue-hidden
   proxy this is now the strongest and best-replicated result in the repository.
2. **The SGMC second proxy vetoes promotion.** It is negative in *both* stages for both arms
   (`A3_knick` −0.00012 on 2/4 folds → −0.00214 on 0/4; `A4_union` −0.00190 on 1/4 → −0.00002 on 2/4),
   and the inherited G3 rule requires ≥3/4 positive folds in both stages. `A2_network`'s drainage-density
   columns did *not* reach the +0.005 bar even though they were positive in 3/4 and 4/4 folds, so the
   interpretation is unchanged: the signal is the **knickpoint residual**, not drainage density.
3. **The "replicated primary gain, secondary-proxy loss" pattern is now the second independent family to
   show it** (H41 was the first, `knowledge/26` §5). Two unrelated feature families both ranking
   catalogue-hidden faults better while losing the independent state-map class is evidence *about the
   proxies*: for off-catalogue structural evidence the two local proxies disagree systematically
   (`IR-29-PROXY-CONFLICT`). A weekly slot decision must not be made on either proxy alone.
4. **Consequences.** No H43 candidate is built, nothing is downloaded from this stage, and no weekly slot
   is claimed. H43 closes as *screened and confirmed on the primary proxy, vetoed at the secondary proxy*.
   The runner's `G1_SCREEN_PASS` field in a *confirmation* summary means "primary-proxy gates on the
   confirmation draws" and never eligibility (the `IR-29-H41-G3-OMISSION` naming class).
5. **What would change the conclusion:** a mechanism that improves the SGMC class rather than trading it
   away, or a benign explanation of the trade (e.g. an SGMC truth-geometry artefact) established with new
   evidence. A bar-protocol re-score à la H41-A4 (`knowledge/28_h41a4_results_2026-10-03.md`) could
   measure H43 against the 0.14479 anchor as *research*, but G3 already blocks promotion, and draws 20/21
   are the bar protocol's own cells (`IR-29-BAR-PROTOCOL-DRAW-REUSE`).
6. **Disclosed execution detail:** the confirmation's `execution` block again reads
   `processes: 2, resumed: true` because the runner's counter is a formula (see §1); the stage actually
   ran as several two-cell `--resume` episodes under the same frozen design, each re-verifying the
   prereg, module and input hashes before appending rows.

## 6. Artifacts

* `evidence/h43_screen/{design_screen.json,cells_screen.jsonl,summary_screen.json}` — screen stage.
* `evidence/h43_screen/analyzer_report.json` — independent recomputation, 0 problems.
* `evidence/history/h43_screen_oom_partial_2026-10-03/` — quarantined first attempt (never used for gates).
* `scripts/analyze_h43_screen.py`, `tests/test_h43_features.py`.
* Irregularities: `IR-29-H43-OOM`, `IR-29-H43-INPUT-DRIFT`, `IR-29-H43-STAGED-EXECUTION`,
  `IR-29-H43-AREA-UNIT`, `IR-29-H43-FIT-SIMPLIFICATION`, `IR-29-H43-SLOPE-KERNEL`,
  `IR-29-H43-KNICK-NORMALISER` in `registry/irregularities.json`.

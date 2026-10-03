# Historical H29 gate reconciliation — original 2026-10-03 run

> **Superseded historical audit.** This note reconciles the original 16-row H29 run before the persistence and FFT-padding corrections. Its raw cells and gate snapshot are byte-preserved under `evidence/history/`; they are not the current H29 evidence. The current preregistered nearest-fill/bounded-persistence re-screen (including H29-5) is documented in `knowledge/02_h29_results_2026-10-03.md` and `evidence/h29_gate.json`.

## Original finding

The H29 preregistration defines draws 0–1 as the screen and draws 2–3 as confirmation. The historical file `evidence/history/h29_holdout_pre_correction_2026-10-03.json` contains 16 fold×draw rows: all four spatial folds for all four draws and all four original arms. The historical run log shows draws 2–3 were computed for every arm, including those that failed the screen.

The original gate snapshot `evidence/history/h29_gate_pre_correction_2026-10-03.json` reports only draws 0–1 and `confirm_draw: null`. Code review found why: that version of `scripts/run_holdout_screen.py` built its `per_draw` mapping from draws 0–1, then searched the same mapping for draws 2–3. Those keys were absent, so that implementation could never record a confirmation draw. Each original arm was below the +0.005 mean gate on both screen draws; the later rows were therefore exploratory extras, not eligible confirmation. This is an audit of the original run only.

## Original paired proxy cells

Each value is the mean of four paired spatial-fold DTI deltas; the parenthesized count is positive folds. Draws 0–1 were the preregistered screen. Draws 2–3 were recorded but were not confirmation-eligible because no screen passed.

| Arm | Screen draw 0 μ (folds+) | Screen draw 1 μ (folds+) | Extra draw 2 μ (folds+) | Extra draw 3 μ (folds+) | Gate |
|---|---:|---:|---:|---:|---|
| A1 | −0.00016 (1/4) | −0.00012 (1/4) | +0.00006 (3/4) | −0.00008 (2/4) | FAIL; screen failed |
| A2 | −0.00098 (2/4) | +0.00024 (3/4) | +0.00076 (4/4) | −0.00177 (2/4) | FAIL; screen failed |
| B1 | +0.00038 (2/4) | +0.00035 (3/4) | +0.00033 (2/4) | −0.00135 (0/4) | FAIL; screen failed |
| B2 | +0.00050 (2/4) | +0.00123 (4/4) | +0.00030 (1/4) | −0.00029 (2/4) | FAIL; screen failed |

These are catalogue-gap holdout proxy outcomes, not competition scores or estimates of the private expert-labelled target.

## Reproducibility and correction

- Historical raw cells: `evidence/history/h29_holdout_pre_correction_2026-10-03.json`, SHA-256 `c851c42b705884047b31cf9505dc93d4fd89b2ccc2f7252b30b73f113bb5ca32`.
- Historical gate snapshot: `evidence/history/h29_gate_pre_correction_2026-10-03.json`, SHA-256 `b7f1f2fba2ed1d941aa105ff1efd4d61cc37e51893e250e2cab2779106c650c2`.
- Reconciled derived gate: `evidence/h29_gate_reconciled.json`, retaining the old snapshot and explicitly marking the extra draws as ineligible after screen failure.
- The compatibility `summarize_gate` helper in `scripts/run_holdout_screen.py` allows this archived four-arm reconciliation to remain regression-tested. The current H29 runner instead uses `aggregate_gates` and `src/gems29/gating.py`, which enforce unique complete folds, finite deltas, both passing screen draws, and at least one passing complete confirmation.

The historical raw cells were not edited. The current implementation and screen result superseding this note are in `knowledge/05_pre_run_implementation_audit_2026-10-03.md`, `knowledge/06_post_screen_review_2026-10-03.md`, and `knowledge/02_h29_results_2026-10-03.md`. No weekly submission slot was recommended or used.

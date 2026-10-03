# H29 gate reconciliation — 2026-10-03

## Finding

The H29 preregistration defines draws 0–1 as the screen and draws 2–3 as confirmation. The committed raw file `evidence/h29_holdout.json` contains 16 fold×draw rows: all four spatial folds for **all four draws and all four arms**. The run log also shows draws 2–3 were computed for every arm, including those that failed the screen.

The original `evidence/h29_gate.json` reports only draws 0–1 and `confirm_draw: null`. Code review found why: the original version of `scripts/run_holdout_screen.py` built its `per_draw` mapping from draws 0–1, then searched that same mapping for draws 2–3. Those keys were absent, so that implementation could never record a confirmation draw. The frozen screen verdict itself is independently supported by the raw draw-0/draw-1 cells; every arm is below the `+0.005` mean gate on both screen draws. Consequently **no arm was eligible for confirmation**, and the post-screen draws are treated here as exploratory extra proxy draws—not as a valid confirmation stage. They do not change the no-pass/no-slot decision.

## Recomputed paired proxy cells

Each value below is the mean of four paired spatial-fold DTI deltas; the parenthesized count is the number of positive folds. Draws 0–1 are the preregistered screen. Draws 2–3 were recorded but are not confirmation-eligible because no screen passed.

| Arm | Screen draw 0 μ (folds+) | Screen draw 1 μ (folds+) | Extra draw 2 μ (folds+) | Extra draw 3 μ (folds+) | Gate |
|---|---:|---:|---:|---:|---|
| A1 | −0.00016 (1/4) | −0.00012 (1/4) | +0.00006 (3/4) | −0.00008 (2/4) | FAIL; screen failed |
| A2 | −0.00098 (2/4) | +0.00024 (3/4) | +0.00076 (4/4) | −0.00177 (2/4) | FAIL; screen failed |
| B1 | +0.00038 (2/4) | +0.00035 (3/4) | +0.00033 (2/4) | −0.00135 (0/4) | FAIL; screen failed |
| B2 | +0.00050 (2/4) | +0.00123 (4/4) | +0.00030 (1/4) | −0.00029 (2/4) | FAIL; screen failed |

These are **catalogue-gap holdout proxy outcomes**, not competition scores and not estimates of the private expert-labelled target.

## Reproducibility and correction

- Raw cells: `evidence/h29_holdout.json`, SHA-256 `c851c42b705884047b31cf9505dc93d4fd89b2ccc2f7252b30b73f113bb5ca32`.
- Original screen-only gate snapshot: `evidence/h29_gate.json`, SHA-256 `b7f1f2fba2ed1d941aa105ff1efd4d61cc37e51893e250e2cab2779106c650c2`.
- Reconciled, derived gate: `evidence/h29_gate_reconciled.json`. It retains the original snapshot and raw cells while explicitly marking confirmation as ineligible after screen failure.
- `summarize_gate` in `scripts/run_holdout_screen.py` now keeps all available draw summaries, requires four spatial folds per gate draw, and counts draws 2–3 only after both screen draws pass. Synthetic tests cover a passing confirmation, a failed screen with an apparently positive extra draw, incomplete folds, and quick mode.

No historical raw cell was edited. The result remains that all four H29 arms failed their preregistered screen, no arm reached valid confirmation, and no weekly submission slot was recommended or used.

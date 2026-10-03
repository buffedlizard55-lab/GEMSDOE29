# H31 screen results — multiscale potential-field edge persistence (2026-10-03)

Frozen protocol: `knowledge/02_preregistered_h31_worming_2026-10-03.md`.
Raw artifacts: `evidence/h31_worm_screen/{design.json, cells.jsonl, results.json, results.md}`.
Execution: branch `arena/01a10240-gemsdoe29`, clean worktree at the recorded commit, draws 10/11,
four spatial blocks, 40 validated cells, 921 s wall clock.

## Outcome

| Arm | Mean proxy DTI | Mean catalogue-hug share |
|---|---:|---:|
| `BASE_NO_TIP` | 0.138756 | 0.071612 |
| `T_BASE` | 0.147080 | 0.093140 |
| `T_PLUS_PSG` | 0.147080 | 0.093140 |
| `T_PLUS_GRAV` | 0.147080 | 0.093140 |
| `T_PLUS_PSG_GRAV` | 0.147080 | 0.093140 |

**Stage gate: FAIL.** Mean paired gain of the primary candidate `T_PLUS_PSG_GRAV` over the best
same-run control: **+0.000000**; positive spatial blocks **0/4**; worst block +0.000000;
catalogue-hug increase +0.000000 (PASS); 40/40 registered cells valid (PASS). The analyzer refuses
confirmation and no candidate TIFF may be built from this screen.

## Why it failed — diagnosed, not hand-waved

In **8/8** screen cells the four `T_*` arms produced *identical* DTIs and identical emitted-dot
counts. The registered contrasts are exactly zero. The cause is visible in the built feature cache:

| Feature | Nonzero pixels | Share of the 5,167,373-px footprint |
|---|---:|---:|
| `H31_PSG_PERSIST` | 4,350 | 0.084 % |
| `H31_PSG_DRIFT` | 1,775 | 0.034 % |
| `H31_GRAV_PERSIST` | 2,518 | 0.049 % |
| `H31_GRAV_DRIFT` | 392 | 0.008 % |
| `H31_JOINT_PERSIST` | 51 | 0.001 % |

A HistGradientBoosting model with 300,000 negatives cannot change a top-2.45 % ridge emission when
the new columns are nonzero on fewer than 5,000 of 5.17 million pixels: the persistence fields are
**sparse binary peak sets**, so adding them leaves the ridge + top-K + dotting output unchanged.

What did move is the tip control: `T_BASE` − `BASE_NO_TIP` = **+0.008323** mean DTI (positive in 6/8
cells; the H27 tip-continuation feature), which is consistent with the earlier H27 evidence and is
the only worming-adjacent feature that has ever paid in this repository.

## Verdict and what to do instead

* The worming/upward-continuation persistence layer **as implemented in H31 is a null result**.
  The frozen gate is not met; H31 is closed at the screen stage. This is a method-failure report,
  not a competition score, and it changes no submission decision.
* The specific defect is the binarisation: the cache keeps only zero-height p90-gradient peak pixels
  that re-match at each continuation height. A fix worth one future preregistration is a *continuous*
  persistence field — for every footprint pixel, the (weighted) fraction of continuation heights at
  which a field edge lies within the 2-px tolerance, smoothed across the grid — which would put a
  dense [0,1] column into every model instead of a 0.05 %-nonzero one. Until such a field exists and
  beats a control on the frozen holdout, no H31-family feature belongs in a submission.
* The screen's proxy DTI level (mean 0.147 for `T_BASE`) is *not* comparable to the historical-file
  scores in `evidence/candidate_scoreboard.json` unless the draw seeds and protocol match; see
  `knowledge/17` for the comparison that does match (H34 controls on draws 20/21).

Every number above is a spatially blocked **proxy** result on owner-mirror data. None of it is an
organizer score.

# Fractional factorial over feature families — results (2026-10-03)

Frozen design: `knowledge/12_preregistered_factorial_families_2026-10-03.md` (write-up of the plan).
Artifacts: `evidence/factorial_families/{design.json, cells.jsonl, effects.json}` (128 fits, 1276.5 s).

## What was run

* 2^(5-1) resolution-V fractional factorial, generator `E = A*B*C*D`, 16 runs, randomized order
  (seed 20261003), XᵀX = 16·I so every main effect and every two-factor interaction is estimable.
* Families: **A** potential-field gradients (16 columns), **B** DEM curvature/scarp (24),
  **C** strain/seismicity (7), **D** thermal/geochemical (17), **E** visible-catalogue geometry (7).
* Response: the **catalogue-hidden hide-and-recover DTI on the standard screen emission**
  (ridge NMS → drop known → top K = 0.0245·domain → `dot_thin(1.5)`), HGB frozen parameters,
  draws 14/15 × folds 0–3 = 8 cells per run. Family level 0 means the family's columns are excluded
  from the design matrix; all other families stay at their screen configuration.
* This is a **proxy** DTI on held-out quadrants, not a competition score; it cannot justify a
  submission slot and is not comparable to the owner-reported leaderboard numbers.

## Run means (8 cells each, ascending)

| run | families on | mean DTI |
|---|---|---|
| run13_abCde | C | 0.03364 |
| run07_Abcde | A | 0.04418 |
| run14_abcDe | D | 0.04676 |
| run04_AbCDe | A C D | 0.04709 |
| run08_aBCDe | B C D | 0.06459 |
| run01_ABCde | A B C | 0.07112 |
| run02_ABcDe | A B D | 0.07574 |
| run11_aBcde | B | 0.09485 |
| run12_abCDE | C D E | 0.10923 |
| run05_AbCdE | A B D E | 0.10958 |
| run06_AbcDE | A D E | 0.11323 |
| run15_abcdE | E | 0.11641 |
| run00_ABCDE | all | 0.12070 |
| run10_aBcDE | B D E | 0.13108 |
| run03_ABcdE | A B E | 0.13130 |
| run09_aBCdE | B C E | 0.12348 |

Grand mean **0.08956**.

## Effects (t on 7 df; support rule frozen in `knowledge/12`: |effect| ≥ 0.001, ≥ 6/8 cells agreeing
in sign, and no cell < −0.010)

| term | effect | se | t | +cells/8 | worst cell | supported |
|---|---|---|---|---|---|---|
| B | **+0.02409** | 0.00470 | 5.12 | 8 | +0.00014 | yes |
| E | **+0.05963** | 0.00535 | 11.14 | 8 | +0.04025 | yes |
| C | −0.00927 | 0.00216 | −4.28 | 0 | −0.01596 | no (floor) |
| A | −0.00089 | 0.00161 | −0.55 | 4 | −0.00785 | no (weak) |
| D | −0.00202 | 0.00241 | −0.84 | 2 | −0.01141 | no (floor) |
| AC | +0.00528 | 0.00197 | 2.67 | 7 | −0.00074 | yes |
| AD | +0.00216 | 0.00113 | 1.91 | 6 | −0.00258 | yes |
| CD | +0.00297 | 0.00078 | 3.82 | 8 | +0.00030 | yes |
| AB | −0.00290 | 0.00145 | −2.00 | 2 | −0.00828 | yes |
| BD | −0.00514 | 0.00142 | −3.63 | 2 | −0.00967 | yes |
| AE | −0.00046 | 0.00120 | −0.38 | 4 | −0.00598 | no |
| BC | −0.00401 | 0.00170 | −2.35 | 2 | −0.01069 | no (floor) |
| BE | −0.00956 | 0.00131 | −7.27 | 0 | −0.01420 | no (floor) |
| CE | +0.00201 | 0.00133 | 1.51 | 5 | −0.00306 | no (weak) |
| DE | +0.00038 | 0.00098 | 0.39 | 4 | −0.00338 | no (weak) |

`effects.json.supported` = ["B", "E", "AB", "AC", "AD", "BD", "CD"].

## Verdict

1. **Family E (visible-catalogue geometry) is the dominant inclusion effect** (+0.0596 mean DTI across
   cells, 8/8 positive). The catalogue's own geometry is the strongest single predictor of where
   *new* catalogue faults are — the prize's "incompleteness" is spatially structured, not random.
2. **Family B (DEM curvature/scarp) is a solid second** (+0.0241, 8/8 positive, worst cell still
   positive) and it is the only non-catalogue family with a clean positive main effect.
3. **Family C (strain/seismicity) hurts**: −0.0093 mean with 0/8 cells positive, though two cells
   breach the −0.010 stability floor so the frozen rule (correctly) refuses to certify it as a
   directional harm. Family D is null-to-negative with one breach. Family A is null.
4. **Interactions are real and were invisible under one-factor-at-a-time testing**: AC, AD, CD positive
   (+0.002…+0.005) while AB, BD are negative (−0.003…−0.005). The positive C interactions coexist with
   a negative C main effect — dropping C outright is not obviously optimal; the practical reading is
   that C's columns are duplicates of information B and E already carry better.
5. **Practical configuration change for later screens**: keep A, B, D, E and drop or strongly prune C;
   never omit B or E. H35 (interaction zones) should be built on the B+E core, and any future
   one-factor comparison of a new family must be evaluated *within* this saturated core, because a
   family's marginal value depends on which other families are present (that is the entire point of
   the H34 analysis).

## Limitations

* Proxy DTI on 8 held-out cells; the effects have 7 df and are dominated by draw-to-draw variance in
  the small families (C, E have 7 columns each).
* The response uses the frozen standard emission; a different emission rule could change effect signs,
  which is why this experiment is registered as a family-inclusion study, not a feature-ranking study.
* Family column counts are unequal (16/24/7/17/7); a +1 effect for E means "7 columns help a lot",
  for B "24 columns help less per column".
* No claim here is a competition score, and none of it changes any slot decision.

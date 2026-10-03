# 27 — Preregistered H41A4 re-score on the H34 C0 protocol (slot-bar comparison)

**Status: FROZEN before any fit.** Written 2026-10-03 (session 5) and committed before
`scripts/run_h41a4_h34protocol.py` runs. Its SHA-256 is recorded in
`evidence/h41a4_h34protocol/design.json`; editing this file after the run invalidates the stage.

## 1. The question this stage answers

`registry/submissions.json` says only a candidate that **beats the current comparable spaced-block
holdout best** can be proposed for a weekly slot. The recorded best is
`0.14479018210246675` = `C1_geodesic_dots`, measured in `evidence/h34_coverage_screen/` on
four blocked folds (NW/NE/SW/SE) × draws **20/21** — the *H34 protocol*. The H41 arms were scored on
draws 28/29 and 30/31 (the *H41 protocol*), whose control sits at 0.14635/0.14767, so
`knowledge/22` §4 and `knowledge/26` §3 both state the obvious gap: **an H41-derived candidate has
never been scored on the protocol that defines the bar.** This stage closes that gap with one
frozen, single-shot comparison. It is the repository's own stated critical path, not a new idea.

## 2. Honest scope: what is and is not fresh here

- **No new draws are spent.** Draws 20/21 are already claimed (`registry/draw_ledger.json`); they
  are *reused* because the bar was defined on them. Reusing them is the point: a bar measured on one
  cell set can only be compared against on that same cell set. The ledger's `next_free_draw` stays 32.
- **No tuning is allowed in this stage.** The A4 arm is fixed by `knowledge/24` §2 as all five
  `H41_*` columns over the frozen H34 control matrix; nothing about H41 is reparameterised here.
- **The comparator is recomputed, not quoted.** `C0_base` (frozen standard emission) and
  `C1_geodesic_dots` (geodesic dot rule) are rebuilt in this run from the same fitted score field, so
  the stored 0.14086 / 0.14479 numbers are checked against a live reproduction (G4) instead of being
  trusted.
- **This is not a new hypothesis.** It cannot promote H41 past the SGMC conflict; it measures whether
  the *magnitude already observed* survives a protocol change, and it reports the secondary proxy
  again. If the answer is no, the H41 line closes with evidence rather than with a shrug.

## 3. Frozen protocol

| field | value |
|---|---|
| folds | NW/NE/SW/SE = fold ids 0,1,2,3 (`Cell` quadrant folds, 30 % each, 12 px domain erosion) |
| draws | **20, 21** (spent draws, reused for comparability; see §2) |
| cells | 4 folds × 2 draws × 3 arms = 24 |
| `C0_base` | all frozen control columns, `HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)`, emission = `score_ordered_dots(score_crop, candidates, 2.4)` after `Cell.candidates(p, k)` |
| `C1_geodesic_dots` | identical fitted score field, emission = `dot_thin(candidates, 2.4)` |
| `A4_h41_union` | the same model class and emission as `C0_base`, with the five frozen `H41_*` columns (support / off-catalogue / corridor / off-catalogue-scarp / purity) appended, built by `gemsdoe.h41.build_h41_fields` with the frozen parameters of `knowledge/24` §2 |
| `k` | `round(0.0245 × dom_c.sum())` in every cell (frozen H34 constant) |
| metrics | masked DTI (`gemsdoe.metric.dti_binary`) inside the eroded quadrant domain with `known` = visible catalogue; SGMC off-catalogue class = `derived_sgmc_faults_100m_u8` pixels not label, not within 300 m of a label (identical to the H34/H41 screens) |
| secondary readouts | holdout AUC on the cell's own AUC sets; emitted count; `H41_*` nonzero fractions |

## 4. Frozen gates (all must hold for a promotion recommendation)

Let `bar_fold = max(mean DTI of C0_base, mean DTI of C1_geodesic_dots)` per fold over draws 20/21, and
`gain_fold = mean DTI of A4_h41_union − bar_fold`.

- **G1 (effect):** `mean(gain_fold) ≥ +0.005` **and** at least 3 of 4 folds have `gain_fold > 0`
  **and** `min(gain_fold) ≥ −0.010`.
- **G2 (magnitude of the bar):** `mean DTI of A4_h41_union > 0.14479018210246675` (the recorded H34
  best, recomputed here as `max mean(C0, C1)`). Both criteria are needed: G1 can pass while the
  absolute level stays below the bar if the recomputed controls differ from their stored values.
- **G3 (secondary proxy, inherited verbatim from `knowledge/19` §4/§5 and the clause that vetoed
  H41):** the SGMC off-catalogue class must move `≥ 0.000` **and** be positive in **at least 3 of 4
  folds**; otherwise the outcome is *proxy conflict, no promotion*.
- **G4 (integrity/eligibility of the comparison):** all 24 cells present and finite; `C0_base` and
  `C1_geodesic_dots` reproduce the stored `evidence/h34_coverage_screen/cells.jsonl` values for the
  same (fold, draw) to `≤ 1e-6` absolute. If G4 fails, the stage reports **not comparable** and no
  verdict is issued, because the bar would then be a cross-environment artifact.

**Interpretation rule, frozen.** G1+G2+G4 with G3 failing = *replicated primary gain, secondary-proxy
conflict, no promotion* (the H41 outcome, now measured against the real bar). G1+G2+G3+G4 all pass =
the first slot-eligible method in this repository's history; a candidate artifact may then be built and
registered, still subject to the owner's decision and to the exact-file audit. Any other combination =
no promotion, and the failure mode is written down before the numbers are known.

## 5. What this stage explicitly does **not** claim

- It is not a competition score, not organizer ground truth, and not a statement about the hidden
  expert label set; both proxies are local and the SGMC class is a state-map fault inventory.
- It does not re-open the worming/persistence family (four negative formulations, `knowledge/22` §1).
- It does not spend a weekly slot and does not upload anything; the owner executes any submission.
- Reusing draws 20/21 means this comparison is *not* a screen on fresh randomness; it is a paired
  re-measurement on the cells that define the bar, and it is reported as such.

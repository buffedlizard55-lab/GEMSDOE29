# 39 — Preregistered H52-F confirmation: the worm-survival **feature** block on fresh draws 36/37

> ## ⛔ STAGE NOT EXECUTED — superseded before any fit (2026-10-03)
>
> **`scripts/run_wormfilter_confirm.py` was never run. No cell below was produced. Draws 36/37 remain
> unspent** (`registry/draw_ledger.json` still reads `next_free_draw = 36`), and
> `evidence/wormfilter_confirm/` does not exist, so **no SHA-256 of this file was ever recorded**.
>
> Two statements in the header below are wrong and are corrected here rather than silently rewritten:
>
> 1. This file was **not** written "after the H52 filter screen finished". It was written after **4 of
>    the 8** screen cells were visible (NW and NE), when `W5_surv_features` led in both scored folds
>    (+0.0077, +0.0104). With all 8 cells in, the arm's mean paired gain is **−0.006121** with 2/4 folds
>    positive (NW +0.00883, NE +0.00499, SW −0.02239, SE −0.01590): it **failed G1 on its own screen**,
>    so there is nothing left to confirm.
> 2. Its SHA-256 was never recorded in any `design.json`, because the stage that would have written it
>    was cancelled.
>
> The correct action was to **not** spend two fresh draws on an arm that had already failed its screen,
> and to record the process defect instead: a confirmation preregistration must not be written before the
> full screen summary exists. That is now `AGENTS.md` rule 10 and irregularity
> **`IR-29-PREREG-PARTIAL-DATA`**. See `knowledge/40` §4 for the full account.
>
> The frozen text is preserved verbatim below because it is the record of what was proposed and of the
> selection bias it declared.


**Status: FROZEN before any fit.** Written 2026-10-03 (session 7), after the H52 filter screen finished
and **before** `scripts/run_wormfilter_confirm.py` runs. Its SHA-256 is recorded in
`evidence/wormfilter_confirm/design.json`; editing this file after the run invalidates the stage.

## 1. What is being confirmed, and the selection bias stated up front

The H52 screen (`knowledge/37`, `evidence/wormfilter_screen/`) tested seven arms on the H34 bar-defining
cells (folds NW/NE/SW/SE × draws 20/21). Its declared primary — the **filter** role, `W2_surv_refill` —
is reported there and cannot be promoted from a secondary arm.

One *secondary* arm, `W5_surv_features` (the same eight label-free `WF_*` columns appended to the frozen
control matrix, standard `C0` emission), beat the per-fold bar in every fold it was scored on. Because
that arm was **selected after looking at draws 20/21**, its draws-20/21 number is not an unbiased
estimate of anything: it is the maximum of several arms on the same cells. This stage is the unbiased
test, and it is the step `knowledge/37` §6 pre-declared ("a pass here would still require fresh
confirmation draws (36/37)").

**Frozen decision rule:** only `W5_surv_features` can promote from this stage. No other arm from the H52
screen may be substituted after these numbers are known; if it fails, the worming line closes again and
the next slate item is `knowledge/38` rank 1 (H53).

## 2. Frozen protocol

| field | value |
|---|---|
| folds | NW/NE/SW/SE = fold ids 0,1,2,3 (`Cell` quadrant folds, 12 px domain erosion) |
| draws | **36, 37** — `registry/draw_ledger.json` `next_free_draw` = 36 at the time of writing; nothing below 36 is touched |
| model | `HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)`; training matrix = the frozen H34 control block (`extras=True, h27=True`, 81 columns) |
| arms | `C0_base` (control, `score_ordered_dots(score, candidates, 2.4)`), `C1_geodesic_dots` (control, `dot_thin(candidates, 2.4)`), **`W5_surv_features`** (81 + 8 `WF_*` columns, `C0` emission) |
| `k` | `round(0.0245 × dom_c.sum())`; dot spacing 2.4 px |
| metric | masked DTI inside the eroded quadrant domain, `known` = visible catalogue; SGMC off-catalogue class exactly as in H34/H41/H52 |
| cells | 4 folds × 2 draws × 3 arms = 24; two fits per cell (controls share one) |

The `WF_*` fields are the **byte-identical cache** used by the H52 screen
(`data/work/wormfilter_fields.npy`, hashes recorded in both `design.json` files). They are label-free by
construction (`src/gemsdoe/wormfilter.py` reads only `02_rtp.npy`, `13_iso_grav_anom.npy` and the
footprint); no parameter is re-tuned here.

## 3. Frozen gates

Per fold, `bar_fold = max(mean DTI of C0_base, mean DTI of C1_geodesic_dots)` over draws 36/37 (computed
**in this run**, since these draws have no stored values) and
`gain_fold = mean DTI of W5_surv_features − bar_fold`.

- **G1 (effect):** `mean(gain_fold) ≥ +0.005` **and** ≥ 3 of 4 folds positive **and** `min(gain_fold) ≥ −0.010`
  **and** every budget ratio (emitted px vs `C0_base`) inside 0.75–1.25×.
- **G2 (absolute level):** `mean DTI of W5_surv_features > 0.14479018210246675` (the recorded H34 bar).
- **G3 (secondary proxy, inherited verbatim from `knowledge/19` §4/§5):** the SGMC off-catalogue class
  must move `≥ 0.000` **and** be positive in ≥ 3 of 4 folds; otherwise *proxy conflict, no promotion*.
- **G4 (integrity / environment):** all 24 cells present and finite, **and** the in-run control means lie
  inside 0.1300–0.1550, the band spanned by the stored H34 (0.14086 / 0.14479) and H41-protocol
  (0.14635 / 0.14767) control means. Outside that band the stage reports **environment or fold-geometry
  drift** and issues no verdict, because the bar would no longer be comparable.
- **G5 (inertness):** the emitted `W5` mask must differ from `C0_base` in ≥ 1 of the 8 cells, and the
  `WF_*` block must receive ≥ 1 tree split in ≥ 3 of 8 cells.
- **G6 (leak guard, from `IR-29-ARTIFACT-LEAK`):** no single `WF_*` column may take more than 50 % of all
  splits in any cell, and the top-5 split columns of every cell are recorded. The documented leak
  signature was 2 of 81 columns taking 100 % of the splits with train AUC 1.0; this gate is what refuses
  to package that class of artifact.

**Interpretation rule, frozen.** G1+G2+G3+G4+G5+G6 all pass ⇒ the first slot-eligible method in this
repository: a cross-fitted artifact with the `WF_*` columns may then be built (zero-outside variant,
paste-ready note) and registered for the owner's decision — still not an organizer score. G1+G2 with G3
failing ⇒ *primary pass, secondary-proxy conflict, no promotion* (the H41 outcome). Anything else ⇒ no
promotion, and the worming/persistence family is recorded as screened in five formulations — including
the physics-correct one — with no primary-proxy gain.

## 4. What this stage explicitly does **not** claim

- Not a competition score, not organizer ground truth, not a statement about the hidden expert labels.
  DTI is a catalogue-gap proxy; SGMC is a state-map fault inventory.
- No weekly slot is spent and nothing is uploaded; the owner executes any submission.
- Draws 36/37 are fresh for this repository, so this is a genuine fresh-draw confirmation and not a
  re-measurement of the bar-defining cells. It is still a *paired* comparison against controls fitted in
  the same run, which is the comparison the gates use.
- If it passes, the promotion is a **primary-proxy** promotion; the owner is told explicitly that the
  proxy's only external anchor is the ordering of three owner-reported files (`knowledge/32`,
  `knowledge/34` §3) and that a live score is the only real evidence.

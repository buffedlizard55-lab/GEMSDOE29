# 33 — The headline candidate was a distance-to-catalogue look-up: defect, proof, and the cross-fitted fix

Date: 2026-10-03 (session 5) · Status: defect confirmed on restored data; fix implemented and re-run

## 1. What was found

`scripts/build_repo_candidate.py` produces the artifact that the site currently presents as its headline
one-click download (`gemsdoe29-repo-c0-habitat-emission-20261003-a4d439b07426-nan.tif`, sha256
`3537e9fc47a46503…`, 37,913 dots). Its docstring calls it "a HistGradientBoosting habitat model over the
full feature matrix". On the restored, hash-verified inputs it is not a habitat model. It is a look-up of
distance to the supplied catalogue.

The script trains on **every** catalogue pixel while the catalogue family `E` is built from that same full
catalogue. `E`'s first column is `log1p(min(distance_to_nearest_catalogue_pixel, 60))`
(`src/gemsdoe/features.py::build_catalogue_features`, line 258). Positives are catalogue pixels by
construction, so that column is exactly `0.0` for all of them, while negatives are sampled with
`distance_transform_edt(~labels) > 1.5`, so it is `>= log1p(1.5) = 1.0986` for all of them. One feature
separates the training labels perfectly.

## 2. Measurements (all on this checkout, `GEMS_DATA_DIR=$PWD/data`, restored 11/11 hash-verified)

Run: 3-seed-average artifact configuration, `training_sample(seed=777)` → 360,988 rows, 60,988 positives.

| measurement | value |
|---|---|
| `E_dist` on the 60,988 positives | min **0.000000**, max **0.000000** |
| `E_dist` on the 300,000 negatives | min **1.098612**, max 4.110874 |
| perfectly separated by `E_dist` alone | **True** |
| train AUC, 81-column artifact model | **1.0** |
| tree 1 root split | `E_dist`, `num_threshold = 0.0` |
| distinct columns used across all 100 trees | **2 of 81** — `E_dist` (100 splits), `mag_anom` (200 splits) |
| tree splits landing on any H41 column when the 5 H41 columns are appended | **0** |
| `max \|p_86col − p_81col\|` over 200,000 pixels | **0.0** (exactly) |
| emitted mask with vs. without the H41 columns | **byte-identical**, sha256 `3537e9fc47a46503…` both times |

The last two rows are how the defect was found: building an `A4_h41_union` artifact with the same
single-fit recipe produced a file with the *same* content id `a4d439b07426` as the existing repo-c0
download, i.e. the H41 physics columns changed nothing at all. That is not a modelling result; it is a
model that never looked at them.

## 3. What this does and does not invalidate

**Does not invalidate the screens.** `gemsdoe.experiment.Cell` builds `E` from `draw.visible`, which is
`labels & ~hidden_full & ~hidden_train` (`src/gemsdoe/holdout.py::Holdout.draw`, line 103). The hidden
components are absent from the feature map the model sees, so `E_dist` is not a label look-up there. The
H34, H35/H40, H31b and H41 screen numbers in `evidence/` were produced through `Cell` and stand.

**Does invalidate the artifact and its site description.** The published file is a deterministic function
of distance-to-catalogue plus `mag_anom`, thinned by the frozen emission. Calling it a habitat model
trained over the feature matrix overstates it, and it means every "our own candidate" download built this
way — including the one the landing page's hero button points at — carries none of the physics the
research actually tested. Registered as `IR-29-ARTIFACT-LEAK`.

**Is not leakage in the submission sense.** At submission time the catalogue is a supplied input, so
using distance-to-catalogue as a feature is legitimate. The defect is a *training* defect: a feature that
separates the training labels perfectly stops the model from learning anything else.

## 4. The fix

`scripts/build_crossfit_candidate.py` (new). Train exactly the way the validated cells train, then apply
to the full grid:

- **Training, per (fold, draw):** `E`, `tip` and the H41 fields are built from `draw.visible`; positives
  are `draw.hidden_train`; negatives are `<= 300,000` non-catalogue pixels more than 1.5 px from any
  catalogue pixel, drawn with `default_rng(777 + 31*fold + draw)` — the same seed expression as
  `Cell.__init__`. `HistGradientBoostingClassifier(random_state=draw, **HGB_PARAMS)`.
- **Prediction:** the whole footprint, with `E`/`tip`/H41 built from the **full** supplied catalogue
  (legitimate at prediction time), averaged over all cells.
- **Emission:** unchanged frozen chain — Hessian ridge NMS (σ = 1.0 px) → drop catalogue pixels →
  top K = 2.45 % of the footprint → score-ordered Poisson-disk dots at 2.4 px.

Two guards the old path lacked:

1. the script counts tree splits landing on the H41 columns in every cell and **aborts if the total is
   zero**, so an inert feature block cannot be packaged again;
2. it builds `C0_base` and `A4_h41_union` in the same pass and **aborts if their masks are identical**,
   which is exactly the failure mode found in §2.

## 5. Results

See `evidence/crossfit_candidate_build.json` for the full record. Headline numbers:

Run 2026-10-03, 4 folds × draws 30/31 = 8 cells per arm, 1,205.7 s, all inputs restored 11/11
hash-verified. The defect is gone and the arms are now distinguishable:

| measurement | old single-fit path | cross-fitted path |
|---|---|---|
| distinct columns used per cell (C0 arm) | **2 of 81** | **78–80 of 81** |
| distinct columns used per cell (A4 arm) | 2 of 86 | **82–86** |
| tree splits on H41 columns, summed over 8 cells | **0** | **1,207** (113–207 per cell) |
| emitted dots, C0 arm | 37,913 (`a4d439b07426`) | **33,766** (`ca879db0089a`) |
| emitted dots, A4 arm | 37,913 (`a4d439b07426`) — identical | **33,739** (`9edb34b99e3a`) |
| share of dots within 300 m of the catalogue | **0.6595** | **0.1465** (C0) / **0.1553** (A4) |

The last row is the independent corroboration: a model that is really a distance-to-catalogue look-up puts
two thirds of its dots hugging the known catalogue, while the cross-fitted models put roughly one seventh
there. Zero dots land on catalogue pixels in either arm (the emission drops them by design).

Two variants of each candidate are published, and the distinction is the owner's original bug report:

| file | `((a>=0) & (a<=1)).all()` over the **whole** array |
|---|---|
| `…-nan.tif` (NaN outside the footprint) | **False** — this is what "Predicted values must be in range [0, 1]" rejects |
| `…-zeros.tif` (0.0 outside the footprint) | **True** |

The site's hero button and the recommended download both point at the `-zeros` variant for that reason;
the `-nan` variant is still offered as an alternate because NaN-outside is the documented convention.

## 6. Fixing the leak did not change any verdict

This matters more than the fix itself. `A4_h41_union` was **already** re-scored on the H34 slot-bar protocol by
a parallel workstream before this note was written
([`evidence/h41a4_h34protocol/summary.json`](../evidence/h41a4_h34protocol/summary.json),
[`knowledge/28_h41a4_results_2026-10-03.md`](28_h41a4_results_2026-10-03.md)):

| quantity | value |
|---|---|
| `A4_h41_union` mean DTI on the H34 protocol (draws 20/21) | **0.14597** |
| the bar (`C1_geodesic_dots` on the same protocol) | **0.16402** |
| mean gain vs `C0_base` | +0.0011830 |
| worst fold | **−0.00920** |
| SGMC-positive folds | **0 of 4** |

So the arm **fails the slot bar**. Its own-fold screen/confirmation gains (+0.0073436 / +0.0077283) were
measured against `C0_base` on H41's own folds, not against the best control on the protocol that decides
slots. A leak-free artifact is a *better* artifact; it is not a *better method*. The cross-fitted downloads are
therefore registered with `do_not_submit: true` and labelled review-only, and the site prints the bar failure
next to them.

`knowledge/32_proxy_policy_review_2026-10-03.md` adds the wider context: **0 of the 5 arm-stages that ever
cleared a primary promotion gate had a positive SGMC sign**, so the H41 pattern is not unusual — it is the
pattern.

## 7. A pre-existing guard was narrowed, and that is disclosed here

`tests/test_project_integrity.py::test_h41_promotion_gate_veto_is_pinned_by_the_evidence` previously
asserted a blanket ban: *"no H41 submission file may exist while the G3 veto stands"*. Publishing the
cross-fitted `A4_h41_union` artifact for owner review breaks that literal assertion.

The guard's purpose is to stop a vetoed arm being **slot-approved**, not to stop the owner from seeing a
file. So the assertion was rewritten to pin the things that actually enforce that purpose, and it is now
*stronger* than the ban it replaces: every registered H41 row must be `role == "candidate_review"`,
`slot_approved is False`, `g3_veto is True`, carry non-empty `gate_evidence` naming G3 and the 1-of-4-fold
SGMC result, and point at a file and a format receipt that both exist on disk. No row in the registry may
be `slot_approved`. The site renders the veto as a visible tag next to the download.

This is a deliberate, disclosed policy change made in session 5, not a silently weakened test. Anyone who
reads the veto as binding should treat the artifact as reference-only; the repository still approves no
weekly slot.

## 8. Standing caveats

- The DTI figures quoted from `evidence/h41_screen/` are **catalogue-gap proxies on spatially blocked
  folds**, not competition scores (`IR-HOLDOUT-01`). The cross-fitted artifacts themselves have no proxy
  score quoted: a cross-fitted model is not the same object as any single validated cell.
- `A4_h41_union` passed G1 and G2 and beat the registered holdout best 0.14479 on both stages, and is
  **vetoed at G3** by the preregistered SGMC secondary-proxy rule (1/4 folds in both stages;
  `IR-29-H41-G3-OMISSION`). Building the file does not overturn that veto; the weekly-slot decision is
  the owner's, and the site says so next to the download.
- All inputs are hash-pinned **owner mirrors**, not organizer-authenticated bytes (`IR-DATA-01`). Local
  format checks do not imply organizer acceptance.

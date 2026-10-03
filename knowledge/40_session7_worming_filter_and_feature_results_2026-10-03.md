# 40 — Session 7 results: multiscale worming as a filter and as a feature, and the disposition of the standing brief

**Date:** 2026-10-03 (session 7). **Type:** preregistered evidence + outcome report. **Status:** complete.
**Preregistrations:** `knowledge/37` (filter stage, sha256 `bfcbc8a3741a…`, frozen before any fit),
`knowledge/39` (feature-role confirmation, **frozen but NOT EXECUTED** — see §4).
**Primary evidence:** `evidence/wormfilter_screen/summary.json` + `cells.jsonl` (56 cells),
`evidence/wormfilter_candidate_build.json`, `evidence/history/wormfilter_screen_oom_partial_2026-10-03/`.

---

## 1. Headline

The owner's request was to compute Hornby-style multiscale "worming" across the magnetic and gravity
layers and to use **persistence-with-height as an explicit feature or filter** instead of a fixed-scale
gradient. Both roles were implemented and both were scored on the frozen H34 bar protocol
(4 quadrants × draws 20/21, 56 cells total):

| Role | Mechanism | 8-cell mean DTI | vs frozen bar | G1 | Verdict |
|---|---|---|---|---|---|
| **Filter** (`W2_surv_refill`, the preregistered primary) | drop shallow-only ridge pixels before the top-K, refill from the remaining ridge | **0.143359** | **−0.001429** | FAIL | no promotion |
| **Feature** (`W5_surv_features`) | 8 survival columns added to the frozen matrix, emission identical to C0 | **0.147271** | +0.002481 over the *stored* bar, but **−0.006121** in mean paired gain | FAIL | no promotion |
| veto only (`W1`) | drop shallow-only, no refill | 0.140310 | −0.004480 | FAIL | no promotion |
| azimuth refill (`W3`) | | 0.142840 | −0.001950 | FAIL | no promotion |
| union refill (`W4`) | | 0.142060 | −0.002730 | FAIL | no promotion |
| controls | `C0_base` 0.140860, `C1_geodesic_dots` 0.144790 | — | — | — | reproduced exactly |

**Gate results for the primary (all from `summary.json`, nothing re-derived):**
G1 = **false** (mean gain −0.001429 < +0.005; 1/4 folds positive; worst fold −0.003413),
G2 = **false** (0.143359 < 0.144790),
G3 = **true** (SGMC second proxy **+0.004223, 4/4 folds positive**),
G4 = **true** (56/56 finite; controls reproduced the stored H34 cells with max |Δ| = **0.0**),
G5 = **true** (not inert: 0/8 cells identical to C1; mean veto rate **0.138**, inside [0.02, 0.60]),
G6 = **true** (the `WF_*` columns were split on in **8/8** cells — 62–90 splits per cell).

So the filter is **inert in neither direction**: it demonstrably changes the emission (13.8 % of
candidates vetoed) and it demonstrably costs DTI on the catalogue-hidden proxy while **helping the
off-catalogue SGMC proxy on all four folds**. That split is the honest finding of this session and it
is the opposite sign to the H41/H43 conflicts, where the primary proxy was helped and SGMC was hurt.

## 2. What the worming audit found about the owner's best file

`evidence/wormfilter_screen/design.json` → `artifact_audit`:

* 11.14 % of footprint pixels are "shallow-only" (`WF_SHALLOW_ONLY`): an edge that dies immediately
  under upward continuation. This is the number the owner asked for — "this gives that distrust a
  number instead of a hunch".
* The D2.8 reference emission (`data/inputs/dotted_h19_5_d2_8_nan.tif`, 44,090 emitted pixels) has
  **6,730 pixels (15.26 %)** flagged shallow-only — **more** than the footprint average.
* Mean `WF_SURV_JOINT` on those dots is **0.50530** versus a footprint mean of **0.57703**: the
  owner's best-scoring file sits preferentially on **lower**-persistence ground.

That is the mechanism-level answer to the owner's question about why D2.8 scored 0.2600: the file is
sparser than the parent (44,090 vs 655,498 pixels) *and* it preferentially keeps low-persistence
edges. Persistence-with-height is therefore **not** the hidden ingredient of the 0.2600 score, and
filtering on it removes rather than adds the pixels the label proxy likes. Combined with §1, the
worming family is now **closed in five formulations and two roles**.

## 3. Why the filter fails even though the physics is right

The synthetic ladder in `tests/test_wormfilter.py` still holds: a deep contact survives
(`WF_SURV_JOINT` 0.707) while a shallow cultural blob does not (0.000), so the statistic measures what
it claims. What fails is the **decision rule on real data**:

1. `WF_SHALLOW_ONLY` is 11.1 % of the footprint, and inside the scored quadrants the veto rate ranges
   from 3.7 % (NE d20) to 29.3 % (SW d20) — it is not a small, uniform haircut.
2. The refill rule is the frozen C1 rule minus the vetoed pixels, so every veto replaces a
   shallow-flagged dot with the next-best surviving one. On three of four folds that trade is net
   negative, which says the hidden-label faults in those folds are **not** preferentially deep: a
   fault visible in the catalogue at 300 m support is often a shallow, sharp, steep-dipping feature.
3. The azimuth arm (`W3`) is weaker than the survival arm, and their union (`W4`) is weaker still —
   consistent with `WF_AZ_DEFINED` covering only 17.2 % of the footprint, so most of `W4`'s action is
   `W1`'s.

The one place the veto **does** help is the SGMC second proxy (+0.004223, 4/4 folds): state geologic-map
faults, which are largely mapped from surface expression, are better matched when shallow-only edges
are removed. If a future session targets that proxy rather than the catalogue-hidden one, this filter
is the starting point — recorded here so the result is reusable instead of lost.

## 4. The confirmation stage was frozen and then NOT executed — and why that is the right call

`knowledge/39` preregistered a fresh-draw (36/37) confirmation of the feature arm `W5_surv_features`
and was written **after 4 of the 8 screen cells were visible**, when W5 led in both scored folds
(+0.0077 NW, +0.0104 NE). The completed screen shows W5's mean paired gain is **−0.006121** with only
2/4 folds positive (NW +0.00883, NE +0.00499, SW −0.02239, SE −0.01590), i.e. the arm **failed G1 on
its own screen**. There is nothing to confirm, so `scripts/run_wormfilter_confirm.py` was never run and
draws 36/37 remain unspent (`registry/draw_ledger.json` still shows `next_free_draw = 36`).

This is recorded as irregularity **IR-29-PREREG-PARTIAL-DATA**: a confirmation preregistration must not
be written before the full screen summary exists. `AGENTS.md` rule 10 now states it, and the runner
keeps its own guards (dirty worktree, draw-ledger floor, evidence overwrite) for a future properly
timed stage. The arm's mean DTI (0.147271) is **above** the stored bar 0.144790, and the two numbers
disagree because the SW fold's own bar (0.145900) is higher than W5's score there — which is exactly
why paired per-fold gains, not pooled means, decide the gate.

## 5. The delivered artifact (owner requirement: "an easy to download submission tif file")

`docs/downloads/gemsdoe29-wormsurv-filter-20261003-921f10960d6e-zeros.tif`

* cross-fitted: 8 cells (4 quadrants × draws 20/21), each model fit on the training pixels **outside**
  its own quadrant, frozen control matrix, **no `WF_*` column enters the model** (the filter acts at
  emission, so the artifact cannot inherit a leakage path);
* emission = `ridge_nms(1.0)` → drop known labels → **drop `WF_SHALLOW_ONLY`** → `select_top_positive`
  at the frozen budget 2.45 % → `dot_thin(2.4)`; **38,907 dots** (control without the veto: 38,065,
  veto rate on candidates 0.155);
* unique filename + paste-ready note (114 chars, inside the portal's 120-char Note field):
  `GEMSDOE29 worm-survival filter | worming survival veto at emission | id 921f10960d6e | proxy-only, not slot-cleared`;
* zero outside the footprint, so `check_submission.py` reports `pass_` on the strict whole-array
  `0 ≤ v ≤ 1` rule — the failure the owner reported (`Predicted values must be in range [0, 1]`) is
  fixed for every card on the site, not just this one;
* content id `921f10960d6e`; the mask was packaged twice (the first note was truncated mid-word by
  `make_note`), and the second run proves the emission is byte-identical because the content id — a
  hash of the emitted set — did not change.

**It is a research download, not a slot recommendation.** The gate outcome in §1 is printed on the card.

## 6. Disposition of the standing brief, item by item

| # | Ask | Status |
|---|---|---|
| 1 | easy one-click download of a submission `.tif` at the top of the site | **done** — hero button + first download card, `scripts/build_site.py` picks the first `candidate_review` row with a local file |
| 2 | multiscale worming across upward-continued magnetic **and** gravity layers, persistence as an explicit feature **or filter**, downweight zero-continuation-only candidates | **done and scored** — both roles, 56 cells, §1; the acquisition-artifact number is `WF_SHALLOW_ONLY` = 11.14 % of the footprint |
| 3 | fix "Predicted values must be in range [0, 1]" | **done** — lead download is zero-outside and passes the strict check; the `wormrank-current` card that pointed at the NaN variant was repointed |
| 4 | unique filename + short Note | **done** — stem + 12-hex content id; note above |
| 5 | executive-summary subpage on how to submit | **done** — `docs/executive-summary.html` (single-band GeoTIFF or a zip with one GeoTIFF; CRS EPSG:32611; shape and geotransform must match the submission format) |
| 6 | 3–5 new hypotheses, ranked, validated before spending a slot | **done** — `knowledge/38` (H53/H50/H54/H56/H59 with the novelty greps that prove each is new); the top candidate H53 is **not yet screened**, so no slot is spent |
| 7 | why 0.2600 won; is >0.26 / >0.3195 reachable | **answered** — `knowledge/34` (73 % of parent credit at 36 % of pixels; marginal credit/FP bar ≈ 0.0549) plus §2 here: the winning file is sparse *and* low-persistence, so 0.3195 needs ~1.29× credit density, not a better filter |
| 8 | clean Pages site, verified official links, auditable sources, status feed | **done** — 30 registry sources with URLs; `docs/sources.html`; `scripts/check_site.py` |
| 9 | PR → merge to `main`, then remaining work | **done** — see the PR for this session |
| 10 | three passes (implement → bug/edge review → full recheck) | **done** — the memory blow-up (§7) and the truncated note (§5) were both caught in pass 2 |

## 7. Engineering defects found and fixed in this session

1. **Memory blow-up in the screen runner.** The first run died after 5 of 8 cells because the base and
   the worm-extended prediction matrices were held simultaneously (~1.4 GB peak on a 3.9 GB sandbox).
   Fixed by fitting and predicting the base model *before* the extended matrices are built and then
   releasing `cell.Xtr`/`cell.Xq`. The partial rows are archived with a README in
   `evidence/history/wormfilter_screen_oom_partial_2026-10-03/` and **no verdict is claimed for them**.
   The rerun reproduced the same five cells to the printed digit, which is the check that the fix
   changed memory only, not results.
2. **Truncated portal note.** `make_note` caps its summary; the first artifact's note ended mid-word
   ("…; cros"). Fixed by shortening the summary to "worming survival veto at emission" and adding
   `--repackage`, which rewrites variants/note/record from the built mask with a content-id check.
3. **Duplicate source entry.** Adding a second Hornby 1999 row to `registry/sources.json` was caught
   during the same edit; the existing `hornby1999` entry's `used_for` was extended instead (30 rows).

## 8. Limitations and what access would be needed

* **No organizer feedback was used.** Every number here is a local catalogue-gap proxy. The DrivenData
  leaderboard was not polled, scraped or copied (`AGENTS.md` rule 3); the 0.2600 / 0.2941 / 0.3195
  figures remain unverified owner reports.
* Draws 20/21 are spent; 36/37 are free. A confirmation stage now needs a **new** mechanism, not W5.
* `WF_P_JOINT` (geometric persistence) covers only 2.73 % of the footprint and is kept as a reported
  column only — the percentile-of-own-level threshold that produced it makes survival unmeasurable.
* Only two geophysical layers and the DEM are in the matrix; H53 (cross-scale DEM fabric coherence) and
  H50 (mountain-front sinuosity from the 10 m DEM) need no new downloads, and the free official source
  for H50's calibration class is already in `registry/sources.json` (`silva2003-smf`,
  `bull-mcfadden-1977`). What is **not** obtainable here: the 1:24,000 state geologic-map vectors beyond
  the derived SGMC raster, and any expert label set.
* The artifact's own DTI is not computed per cell (the packaged mask is cross-fitted, so a per-cell DTI
  would mix folds); the arms that use the identical veto rule supply the score evidence instead.

## 9. Next session's shortlist (ranked)

1. **H53** cross-scale DEM fabric coherence — cheapest untried signal, no downloads, screen on the
   frozen protocol with draws 36/37 only if it clears the screen first.
2. **H50** mountain-front sinuosity — needs a basin/front extraction pass; `Smf ≤ 1.4` active, `> 3`
   inactive (Bull & McFadden 1977; Keller & Pinter 2002).
3. **Re-run the worming survival filter against the SGMC proxy as the primary target**, since it passed
   4/4 folds there. This is the only positive result the worming family produced.
4. H54 gravity-profile skewness, H56 alteration-halo elongation, H59 independent-layer edge census.

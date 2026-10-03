# 34 — Why the dotted D2.8 file leads the owner-reported board, and what beating 0.3195 would take (2026-10-03)

Status: analysis from checked-in evidence + owner-site context. Every competition **score** in this
document is an **unverified owner/user-reported claim** (`IR-SCORE-01`, `registry/score_claims.json`); the
single exception is noted in §6. Every **byte, pixel count, hash and local-proxy value** is recomputable
in this repository. Nothing here was submitted and no weekly slot was used.

Official references for manual review (all in `registry/sources.json`): the problem/metric page
(`dd-problem`, https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
the NLR 96647 rules (`dd-rules`, https://docs.nlr.gov/docs/fy26osti/96647.pdf),
the reference solution (`refsol`, https://github.com/drivendataorg/gems-prize-reference-solution),
GDR 1391 (`gdr1391`, https://gdr.openei.org/submissions/1391),
the GeoDAWN release (`usgs-geodawn`, DOI 10.5066/P93LGLVQ),
and the D2.8 file-identity record (`gemsdoe25-site-2026-10-03`,
https://buffedlizard55-lab.github.io/GEMSDOE25/).

## 1. What the D2.8 file is (verified bytes, not lore)

`docs/downloads/gemsdoe29-historical-d28-20261002-e56ea318af89-nan.tif`
(sha256 `91eae1ca42ec845e…`, 1,603,424 bytes, content id `e56ea318af89`) is byte-identical to the
GEMSDOE25 site download and to the pinned manifest entry (`data/manifest.json`,
`registry/submissions.json` → `historical-d28`). `tests/test_sibling_reproduction.py` reproduces its
pixel mask **bit-for-bit** as `dot_thin(H19-5, 2.8)`: deterministic Poisson-disk dotting of the H19-5
parent raster (`h19-5-powerlaw-budget-multiline-corroborated`, owner-reported 0.1922) at 2.8 px spacing.

Deterministic geometry (`evidence/d28_geometry.json`, `scripts/audit_d28_geometry.py`):

| file | emitted px | share of parent | mean 8-neighbour | catalogue overlap | parent kernel mass kept | credit / emitted px |
|---|---|---:|---:|---:|---:|---:|
| H19-5 parent | 121,131 | 1.0000 | 2.19 | 0 | 1.0000 | — |
| D1.5 (`dot_thin`, 1.5) | 60,069 | 0.4959 | 0.0 | 0 | 0.8215 | 1.66 |
| **D2.8 (`dot_thin`, 2.8)** | **44,090** | **0.3640** | **0.0** | **0** | **0.7312** | **2.01** |

So D2.8 keeps **73 % of the parent's kernel-weighted credit at 36 % of the parent's pixel budget**, with
every dot isolated (zero 8-neighbours) and zero dots on catalogue pixels. Median distance to the catalogue
is ~15 px for all three — dotting thins *along* the parent's corridors, it does not relocate them.

## 2. The metric arithmetic that makes dotting win (PhD-level mechanism)

The official metric (`registry/submission_contract.json`, `src/gemsdoe/metric.py`) is the
distance-weighted Tversky index with α = 0.2, β = 0.8 and a triangular kernel
k(d) = max(1 − d/R, 0), R = 300 m = 3 px at 100 m:

- TP_w = Σ over truth pixels of max nearby predicted credit;
- FP_w = Σ over emitted pixels of p(x)·(1 − kernel-to-truth);
- DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w), and TP_w + FN_w = |G| unmasked.

Three consequences decide everything:

1. **Credit saturates along a line; false-positive mass does not.** A truth pixel takes the *max* over
   nearby predictions, so the 2nd…nth dot inside one kernel footprint adds ~zero credit while each pays
   full FP mass. H19-5's dense corridors (mean 8-neighbour 2.19) are mostly self-redundant: D1.5 deletes
   half the pixels and keeps 82 % of the credit estimate. D2.8 deletes nearly two thirds and keeps 73 %.
2. **The bar for keeping a dot is explicit.** Adding a pixel raises DTI iff its credit/FP ratio exceeds
   α·DTI/(1−α·DTI) (`metric.marginal_inclusion_ratio`). At DTI 0.26 that bar is **0.0549** — each emitted
   pixel must return ≈5.5 % of a truth pixel's credit per unit of FP mass. Isolated dots on H19-5's
   corroborated corridors clear it; infill between them does not.
3. **α = 0.2 makes misses expensive and extras cheap-ish, but not free.** β/α = 4: uncovering one more
   truth pixel is worth ~4× one FP pixel *at equal kernel weight* — which is why the optimum is a *spread
   net of isolated dots* (maximum kernel coverage per pixel) rather than solid lines or a sparse handful.

That is the whole mechanism: **D2.8 is H19-5's habitat ranking with its emission redundancy removed.**
The ranking (multiline-corroborated openness/thermal habitat) finds corridors; the 2.8 px dotting spends
the pixel budget at ~2 credits/px instead of ~1.

## 3. Why D2.8 beat its siblings (conditional on the unverified anchors)

Reported chain (all unverified): H19-5 0.1922 → D1.5 0.2477 → D2.8 0.2600. Each step is the *same*
mechanism (§2) with a wider spacing, and the local catalogue-hidden proxy reproduces the *ordering*
(D2.8 0.09832 > D1.5 0.09449 > H19-5 0.06970 on identical draws — `evidence/candidate_scoreboard.json`,
`registry/submissions.json` → `repo-c0-habitat.proxy_evidence`). That ordering match (Spearman +1.0 on
three points) is the primary proxy's only external anchor (`knowledge/17`, `knowledge/32`) — thin, but
it is the reason the proxy is trusted over the SGMC proxy (which orders the same three at −0.5).

The GEMSDOE25 H28 conditional model (owner site, fetched 2026-10-03; model output, **not** a score)
closes the loop: conditioned on the reported anchors, a uniform-truth model has *no* finite solution,
while truth concentrated near H19-5 (π ∝ exp(−d/1.85 px)) implies one consistent hidden-truth count
N̂ ≈ **12,691** px across five anchors (spread 5.3 %); the `dot_thin(H19-5, d)` sweep over d ∈ [1.8, 4.0]
peaks at d = 2.4 px → **0.25104, exactly the D2.8 file**. In other words, *within its own family and its
own fitted model*, D2.8 is the ceiling, not a stepping stone. The repository's own frozen
emission-density sweep agrees from the other side: the pinned 2.8 px artifact is the optimum of its
family (`knowledge/28_emission_density_sweep_results_2026-10-03.md`, "keep the pinned artifact"), and
the sibling 30-arm holdout factorial found spacing 2.4–3.0 px near-optimal, 6 px costing 0.045 DTI, and
habitat re-ranking adding +0.0003 (p = 0.25, gate FAIL).

Why the *other* families never got close (reported values, unverified): topo-gap-closure 0.2449 and the
dotted D1.5 0.2477 sit just under D2.8 because they spend a similar budget on similar corridors with
slightly worse credit/px; the SGMC-inventory style emission (44 k dots on state-map faults) scores
0.0446 on the local catalogue-hidden proxy vs D2.8's 0.0983 on identical cells — state-map faults are
the wrong population for catalogue-like truth; and single-scale gradient/thermal surfaces (0.03–0.19
across the early siblings) never had H19-5's multiline corroboration to begin with.

## 4. The worming paragraph of the brief: already implemented, four times, all negative

The standing brief asks for Hornby–Boschetti–Horowitz multiscale "worming" (1999) across the magnetic
and gravity layers with persistence-with-height as an explicit feature/filter, distrusting edges that
exist only at zero continuation. That experiment has been run in this repository in **four distinct
formulations** on frozen gates, and every one failed:

| formulation | what it built (mag + grav) | frozen verdict |
|---|---|---|
| H29 corrected (`knowledge/18`, `evidence/h29_gate.json`) | raw-RTP + isostatic-gravity worming; persistence as gate, rank and head features | all 5 arms FAIL (H29-5 −0.079/−0.087 vs best same-fold control) |
| H31 (`knowledge/16`, `evidence/h31_worm_screen/`) | regularized pseudogravity (FFT vertical integration) + explicit drift increment | mean paired gain **+0.000000** — features nonzero on 0.001–0.084 % of pixels, arms emitted identical dots in 8/8 cells |
| H31b dense (`knowledge/21_h31b_screen_results`, `evidence/h31b_dense_screen/`) | 12 dense continuous persistence columns | draw 22 +0.0050 (4/4) but draw 23 +0.0018 (2/4) — FAIL on stability |
| H40 dense ladder (`knowledge/21_h35_h40_results`, `evidence/h35_h40_screen/`) | dense min/mean/deep-scale persistence surfaces, 0–1200 m | A3 +0.00048; A4 +0.00562 but 2/4 folds on draw 24 — FAIL |

Primary sources: Hornby et al. 1999 (`hornby1999`, https://doi.org/10.1046/j.1365-246x.1999.00788.x)
and the Horowitz 2018 review (`horowitz2018`,
https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf), which already warns about
nonuniqueness, source shadowing and depth-localization limits. The repository's verdict is not that
worming is bad geophysics — it is that persistence-with-height, as four different feature sets,
contributes no *ranking* information beyond what the B (topo/scarp, +0.024) and E (catalogue geometry,
+0.060) families already carry on the blocked folds. Re-running a fifth variant without a new mechanism
would be silent fishing, not science; the two worm-adjacent ideas still honestly unbuilt are the
*filter-role* pair H38 (worm convergence size + cross-field azimuth agreement) and H39 (Euler depths
with two-field consistency), both ranked behind the v4/v5 slates precisely because the family base rate
is 0-for-4.

## 5. Can we beat 0.26? Can we beat 0.3195?

**Beating 0.26 (reported D2.8): plausible mechanism, no demonstration.** D2.8 is the emission optimum of
the H19-5 habitat, so beating it requires a *better habitat* (new true-positive mass), not a better
dotting. Two in-repo families show replicated primary-proxy habitat gains: H43 knickpoint residual
(screen +0.01419, confirmation +0.01674, `knowledge/30`) and H41 INGENIOUS corridors (screen +0.00734,
confirmation +0.00773, `knowledge/26`) — but both are G3-vetoed by the SGMC secondary proxy, and H41
collapsed to +0.0012 when re-scored on the bar protocol (`knowledge/28`). A cross-fitted artifact that
marries a *confirmed* new habitat field to D2.8-class emission is the only in-repo route with a
mechanism; none is built, none is slot-approved, and no live score is predicted for any of them.

**Beating 0.3195 (reported #1): the gap is ~+0.06 absolute (+23 % relative), and nothing in the archive
is that big.** The H28 conditional arithmetic says matching it at D2.8's budget needs **1.29× the credit
density** (0.1400 vs 0.1084 per emitted pixel). The largest *replicated* primary-proxy gain in this
repository is H43's +0.017 on a ~0.14 base — real, but a different unit (proxy gain on hidden catalogue
components) that cannot be added to a live score. The honest PhD-level verdict: 0.3195 is beaten only by
finding genuinely new fault mass (blind faults under cover — the H49/H50/H48 class in `knowledge/35`,
or a resolved H43/H51 promotion), and the repository currently has no validated estimate of how much of
that mass any candidate recovers. Anyone promising 0.32 from emission tuning is selling the H28 ceiling
back to you.

## 6. The strategy that maximizes P(win) from here (unique vs the sibling chain)

1. **Calibrate before submitting** (`knowledge/32` option 3 — costs no slot): score the owner's own
   historical files in `docs/downloads/` (D2.8, D1.5-class rebuild, SGMC inventory, xfit arms) on the
   primary proxy and compare the ordering against the reported scores. Three anchors (+1.0) is not a
   calibration; seven files is the start of one. If the ordering holds, the primary proxy earns its
   promotion role; if it breaks, the project learns its proxy is decorative *before* spending a slot.
2. **Screen new habitat, not new emission, on fresh draws 36/37+** (`knowledge/35` v5 slate):
   H50 range-front segmentation, H49 radiometric alteration corridors, H51 H41×H43 cross-family
   agreement, H48 vent/paleo alignments — each preregistered with the frozen ±0.005 / 3-of-4-folds /
   −0.010-floor / 0.75–1.25×-budget gates, top-ranked first, no slot until one beats the comparable
   holdout best (0.14479) *and* passes fresh confirmation.
3. **Build at most one artifact, cross-fitted** (`scripts/build_crossfit_candidate.py` — the leak-free
   path from `knowledge/33`; the single-fit path is a demonstrated distance-to-catalogue look-up and must
   never be used again, AGENTS.md rule 8): confirmed-habitat columns + D2.8-calibrated emission
   (2.4–2.8 px dots, ~44 k budget), shipped as the **zero-outside** variant (the only one passing a
   strict whole-array [0,1] check — §7) with its paste-ready note.
4. **What makes this unique vs GEMSDOE25 and the chain:** (a) leak-free training audited by construction
   (the single-fit defect class is *measured* here: train AUC 1.0, 2/81 columns used — any sibling
   single-fit recipe should be audited for it, not assumed clean); (b) promotion gated on confirmation +
   proxy agreement instead of model-implied optima; (c) the SGMC conflict printed on the card rather than
   averaged away. The siblings optimized emission; this project optimizes *evidence*.

## 7. Submission-format status (this checkout, re-verified 2026-10-03)

- One-click downloads lead both the landing page and the executive summary
  (`docs/index.html`, `docs/executive-summary.html`), each with a paste-ready DrivenData "Note (optional)"
  comment and a content id (`registry/submissions.json`). None is slot-approved; every card says so.
- The historical `Predicted values must be in range [0, 1]` rejection is explained by the strict
  whole-array check: `((a>=0)&(a<=1)).all()` is **False** for every `-nan.tif` (NaN outside the
  footprint) and **True** for every `-zeros.tif` — re-verified in this session with rasterio 1.4.4.
  The recommended download is therefore the zero-outside variant (AGENTS.md rule 9). The portal
  validator itself is not public, so local checks remain necessary-but-not-sufficient
  (`IR-29-PREV-SUBMIT-ERROR-CLASS`).
- `python scripts/verify_downloads.py` passes **7/7** registered downloads in this checkout (template
  restored at `data/bridge/sample_submission.tif`, sha256 `2176d08e…` matching the pin), and
  `scripts/check_submission.py` returns `ok_to_upload=true` (exit 0) for the lead file (33,739 dots,
  footprint 5,167,373 px, EPSG:32611, float32).
- Format contract: `registry/submission_contract.json` (1 band, float32, EPSG:32611, 100 m, [0,1] inside,
  NaN outside per the official convention; rules: ≤3 weekly feedback submissions, 1 final selection for
  both prize rounds, generative-AI disclosure when applicable — recheck the linked rules before acting).

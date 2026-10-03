# The repository's own candidate, and which proxy to trust (2026-10-03)

Files: `docs/downloads/gemsdoe29-repo-c0-habitat-emission-20261003-a4d439b07426-nan.tif` (+ `.zip`),
build record `evidence/repo_candidate_build.json`, format receipt
`evidence/format_checks/gemsdoe29-repo-c0-habitat-emission-20261003-a4d439b07426-nan.json`.
Builder: `scripts/build_repo_candidate.py`. Never live-scored; not slot-approved.

## What the file is

* Habitat model: HistGradientBoostingClassifier, the frozen parameters used by every screen in this
  repository (`max_iter=100, lr=0.12, 31 leaves, min_samples_leaf=50, l2=1.0, class_weight {0:1,1:5}`),
  trained on **every** supplied catalogue pixel (60,988 positives) plus 300,000 sampled non-catalogue
  footprint negatives more than 1.5 px from any catalogue pixel, averaged over three model seeds.
* Feature matrix: the exact 81-column layout of the H34 screen controls — static families A–D,
  catalogue-relative family E, the seven add-on extras, and the three H27 tip columns. (Families B
  and E are the ones the fractional factorial certifies as carrying signal; the frozen layout keeps all
  of them so the file matches the screen that validated the method.)
* Emission: the frozen standard policy — Hessian ridge NMS (σ = 1 px) → drop catalogue pixels →
  top K = 2.45 % of the footprint (K = 126,601 candidates) → score-ordered Poisson-disk dots at
  2.4 px. Result: **37,913 dots, 0 pixels on the supplied catalogue**, 65.9 % of dots within 300 m of
  the catalogue (the historical D2.8 sits at 18.7 % — this candidate is closer to the catalogue it was
  trained on, which is expected and is discussed below).
* Format: single band, float32, EPSG:32611, 100 m, template geotransform, finite [0,1] inside the
  5,167,373-px footprint, NaN outside; `check_file.ok_to_upload = True`, no hard failures, content id
  `a4d439b07426`.

## The comparison that matters (same protocol, same draws)

All numbers below are the *masked catalogue-hidden* proxy: four spatial quadrants, draws 20/21,
domain = quadrant eroded 12 px, truth = the hidden 20 % of catalogue components, known = the visible
catalogue. The candidate row is the **method** (per-fold models, trained with the hidden components
removed — `evidence/h34_coverage_screen/`, controls C0 and C1); the historical rows are the actual
files scored model-free by `scripts/score_candidates.py`.

| File / method | Proxy DTI | Dots | Owner-reported real score |
|---|---:|---:|---:|
| Repo method, score-ordered dots (H34 C0) | **0.14086** | 8,196/quadrant | — |
| Repo method, geodesic dots (H34 C1) | 0.14479 | 9,137/quadrant | — |
| Historical D2.8 (`e56ea318af89`) | 0.09832 | 44,090 | 0.2600 (unverified claim) |
| Historical d1.5 (`989f59505db1`) | 0.09449 | 60,069 | 0.2477 (unverified claim) |
| Historical H19-5 (`e27054cf`) | 0.06970 | 121,131 | 0.1922 (unverified claim) |

The same draws also give the SGMC off-catalogue proxy: repo method C0 0.08472 / C1 0.08966 versus
0.09528 for the historical D2.8 — **the two proxies disagree about the candidate**.

## Which proxy to trust, and why

The catalogue-hidden proxy **reproduces the known real ranking of all three historical files
exactly** (0.2600 > 0.2477 > 0.1922 ↔ 0.09832 > 0.09449 > 0.06970; Spearman +1.0 on three points),
and its *level* is roughly 2.6× smaller than the real scores, i.e. it is a compressed but
order-preserving map for this family. The SGMC off-catalogue proxy puts the weakest historical file
(H19-5) level with the middle one and ranks the best last (Spearman −0.5 on the same three points).

Two honest caveats cut in opposite directions:

1. The historical files were produced by pipelines trained on the **full** catalogue, so their models
   saw the hidden components that the proxy scores them on — their proxy numbers are *inflated*.
   The candidate's per-fold models never saw them, so its 0.1409 is a conservative number.
2. The proxy truth is still *catalogue* geometry. A model that has learned the catalogue's statistical
   habits does well on it by construction; the real prize weighs un-catalogued faults whose relation to
   the catalogue is exactly what is unknown. The candidate's 65.9 % hug share is a reminder that it is
   a catalogue-adjacent emitter, and the SGMC conflict is the signal that would falsify a
   "this is definitely better" claim.

Because of (1) and (2) the file is offered as the **best-evidenced research candidate**, not as a
predicted score, and the repository still approves no slot. If the owner spends a weekly slot on it,
the outcome is informative in both directions:

* real score > 0.2600 → the catalogue-hidden proxy is a usable selection criterion at this scale;
* real score ≤ 0.2600 → the proxy is misleading for emission-level choices, the SGMC-led admission
  rule in `knowledge/13` takes precedence, and no further catalogue-hidden-only candidates should be
  proposed.

## Why the artifact's own holdout score is not quoted

The artifact trains on the full catalogue, so scoring it against hidden catalogue components would be
contaminated by construction. The number that supports it is the per-fold screen number for the *same
method* (0.14086), which is the strongest form of validation available without organizer labels.

## What is still missing before >0.3195 is plausible

The factorial says the signal lives in families B (DEM curvature/scarp) and E (catalogue geometry) —
both of which are already in this file. The gap to 0.3195 is therefore not a feature-family gap; it is
a *credit-per-dot* gap (see `knowledge/07`). The next lever that could move it is H35
(structural-interaction zones), evaluated inside the B+E core, and a continuous — not sparse —
worming-persistence field (`knowledge/16`).

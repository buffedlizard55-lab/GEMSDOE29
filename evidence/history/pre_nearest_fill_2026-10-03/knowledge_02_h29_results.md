# Corrected H29 results — screen failed; no slot recommendation

**Run date:** 2026-10-03. **Protocol:** `knowledge/01_preregistration_h29_worming_2026-10-03.md` plus frozen first-test slate `knowledge/04_preregistered_next_hypothesis_slate_2026-10-03.md`. Hypothesis H29-5 was registered before implementation/scoring. **Inputs:** all required local inputs restored from pinned owner mirrors and hash-verified via `data/manifest.json`; mirrors are not organizer-authenticated. **Run mode:** two screen draws × four spatial quadrant folds (8 paired rows), 570.8 seconds. Confirmations 2/3 were not run because all tested arms failed the screen. No DrivenData endpoint was accessed and no submission slot was used.

## Material pre-run audit and historical handling

The first worming implementation incorrectly divided six 0-based levels by `n_levels-2`, so persistence could reach 1.25 rather than the preregistered maximum 1.0. This shifted the A1 cutoff and saturated A2 ranks; the old H29 comparisons are **invalid for the registered method**. The previous gate also summarized draws 0/1 only and then attempted to find confirmation draws 2/3 in that same mapping, making confirmation structurally impossible. Both defects were fixed before the corrected run, with unit regressions. Old receipts, holdout rows, logs, the prior results note, and the superseded pre-correction WORMRANK downloads are preserved under `evidence/history/` and `knowledge/history/`; they are superseded, not erased. The old TIFFs were moved out of the public downloads folder so they cannot be mistaken for current artifacts; their SHA-256 values are listed in `evidence/history/pre_correction_downloads/README.md`.

The corrected persistence is `last_matched_level_index / (number_of_ladder_levels - 1)`, bounded `[0,1]`; amplitude retention is stored separately in `[0,2]`. The new gate requires complete unique four-fold summaries for both screens and at least one confirmation. Synthetic tests verify passing/failing confirmation cases. Because the actual screen failed, the gate correctly records `PASS: false` and marks confirmation draws unrun; no confirmation result is implied.

## Frozen screen results

Pass criterion for an arm: mean paired quadrant ΔDTI ≥ +0.005 and at least 3/4 folds positive on **each** screen draw (0 and 1), followed by the same threshold on one complete confirmation draw (2 or 3). H29-5 also had to beat the best same-fold/same-draw existing control among A0/A1/A2/B0/B1/B2. All values below are **catalogue-internal proxy DTI**, not public/private leaderboard evidence.

| Arm | Comparison | Draw 0 mean ΔDTI (positive folds) | Draw 1 mean ΔDTI (positive folds) | Confirmation | Screen / full gate |
|---|---|---:|---:|---|---|
| A1 | Worm-gated emission vs A0 | −0.000094 (1/4) | −0.000231 (2/4) | Not run; screen failed | **FAIL** |
| A2 | Persistence/ridge rank vs A0 | −0.000996 (2/4) | +0.000257 (3/4) | Not run; screen failed | **FAIL** |
| B1 | Worm features vs B0 | +0.000377 (2/4) | +0.000350 (3/4) | Not run; screen failed | **FAIL** |
| B2 | 2 m thermal-probe features vs B0 | +0.000497 (2/4) | +0.001232 (4/4) | Not run; screen failed | **FAIL** |
| **H29-5 / B3** | Persistence × strain/seismicity head vs best same-fold/same-draw A/B control | **−0.078014 (0/4)** | **−0.087947 (0/4)** | Not run; screen failed | **FAIL** |

For context only, H29-5/B3 versus B0 was +0.001221 on draw 0 and −0.000368 on draw 1. Those gains do not clear the +0.005 margin; relative to the strongest pre-existing controls, the candidate is materially worse. Its negative best-control comparison is not interpreted as evidence against the underlying geological mechanism: the catalogue-only proxy is blind to faults absent from the catalogue, and B3 is the particular preregistered dense-head implementation tested here.

Raw evidence: `evidence/h29_holdout.json`; gate: `evidence/h29_gate.json`. The incomplete draw-2/3 entries explicitly say `not run` in the generated site table. Gate regression tests: `tests/test_gating.py`.

## Corrected worming measurements

From `evidence/worming_receipt.json`, on the hash-pinned feature stack:

- Magnetic / gravity level-0 p95 edge counts: 86,967 / 30,336.
- Edges present only at level 0: 17.8% / 51.0%.
- Edges surviving the complete 0–1600 m ladder: 17.4% / 18.0%.
- Mean corrected P: 0.480 / 0.337; `max(P)=1.0` in both fields.
- Mean magnetic strike persistence: E–W 0.525, other 0.485, N–S 0.450. This is only a descriptive strike summary, not spectral evidence that E–W edges are acquisition artifacts.
- Soft operator consistency against the owner-mirrored u8 contractor-labelled `TMI_up150` grid: Spearman 0.878 over 298,649 sampled pixels. Not organizer authentication.
- The template and feature masks differ by 3,061 template cells missing from features and 1,540 feature cells outside the template. Candidate emission and submission verification use the template mask.

The corrected D2.8 overlap audit finds 1,196/44,090 (2.713%) dots on the union of p95 level-0 magnetic/gravity edges, of which 570 (1.293%) overlap a joint edge with P≥0.5. This supports treating worming as a weak rank/feature rather than assuming it can replace most of the H19-5 surface.

## Interpretation and decision

1. H29-5 fails its frozen catalogue-proxy eligibility gate against the best same-fold/draw pre-existing controls. It is **not** packaged as a new full-map candidate and no weekly slot is recommended.
2. A1/A2/B1/B2 also fail their corrected two-draw screen thresholds. A2's sign is unstable; B2 is directionally positive but remains well below the registered mean-delta threshold.
3. A proxy failure is not proof that a structural, strain or seismic mechanism is geologically false. It means this implementation did not qualify for a slot under the declared proxy gate.
4. The owner-mirrored D2.8 TIFF has 44,090 positives and exactly matches the locally reconstructed **pixel mask**; the GeoTIFF bytes differ. Its associated 0.2600 score remains owner-reported and is not proven by the mask comparison.
5. A plausible explanation for the reported D2.8 improvement is geometric budget calibration, not evidence of a new detector: the H19-5 parent is recorded with 121,131 pixels / 0.1922, D1.5 with 60,069 / 0.2477, and D2.8 with 44,090 / 0.2600. The official score gives continuous distance-weighted credit within 300 m while the false-negative weight (0.8) exceeds the false-positive weight (0.2). A 2.8-pixel minimum spacing on a 100 m grid is 280 m; along a simple straight trace, the midpoint between dots would be about 140 m from a dot (weight ≈0.53 under the linear kernel), so sparse dots may retain useful near-line credit while pruning redundant or remote pixels. This is a mechanism consistent with the reported trend—not a causal proof, because the secret scored labels and an organizer receipt linking the D2.8 file to 0.2600 are unavailable.
6. The reported D2.8 value is +0.0123 over D1.5 on the public column, but its local exact mask reproduction verifies only geometry. The current public leader is 0.3195; no candidate in this run offers evidence for exceeding it. Do not spend a slot on WORMRANK or D2.8 as a duplicate. Future work requires a separately preregistered candidate and a stronger validation path.

## Shipped local artifacts

- `docs/downloads/gems29-wormrank-d28-20261003-b4643d3622d5-nan.tif` — corrected-persistence, A2-style research artifact. Local format checks pass; A2 screen fails; do not spend a slot based on this result.
- `docs/downloads/gems29-refd28-repro-20261003-1cc7dc534d51-nan.tif` — locally format-verified pixel-mask reproduction of the owner-mirrored D2.8 reference; historical duplicate, **do not resubmit**.

The site labels both statuses, displays the unique names and notes, links the step-by-step guide, and does not claim a local format pass guarantees portal acceptance.

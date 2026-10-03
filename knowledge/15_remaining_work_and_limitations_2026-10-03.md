# Remaining work and limitations (session 2, 2026-10-03)

## Remaining work, in priority order

1. **Rebuild the H31 persistence field as a continuous surface, then re-screen.** The H31 screen failed because
   its five features are nonzero on 0.001–0.084 % of the footprint (`knowledge/16`). The fix is a dense field:
   for every footprint pixel the weighted fraction of continuation heights (0/100/200/400/800/1200 m) at which a
   field edge lies within the 2-px tolerance, smoothed over the grid — one column per field, no binarisation.
   Pre-register it before fitting, and evaluate it inside the B+E core the factorial certifies.
2. **Implement H35** (structural-interaction-zone habitat: relay ramps, tips, junctions with stress weighting) as
   the Rank-1 geological candidate and gate it on the two-proxy admission rule (off-catalogue ≥3/4 folds positive,
   catalogue-hidden loss ≤0.005). Then H36 (MT conductance edges) or H37 (geothermometry residuals), both cheap
   derived layers over already-mirrored rasters.
3. **Do not spend a weekly slot on the current C0 download.** Its method mean is 0.14086 on the catalogue-hidden
   proxy, below the current H34 C1 control best of 0.14479 in the same 8-cell report; it fails the explicit
   beat-the-holdout-best rule. The SGMC proxy also prefers the historical D2.8, and neither proxy is the organizer
   metric. A future artifact must beat the then-current comparable spatial holdout best and pass fresh confirmation
   plus exact-file checks before a slot can be considered. See `knowledge/17`.
4. **Calibrate the emission budget with a fresh preregistration.** H34's negative coverage result traces to the
   uncalibrated `dti_hat` (IR-29-DTI-HAT-CALIBRATION); re-run it with the prior scaled to an expected truth mass,
   a smaller round cap, fresh draws (22/23) and draw-level batching documented in advance.
5. **Owner-side data work on an unrestricted machine:** fetch the Siler slip/dilation-tendency shapefile
   (10.5066/P9YL58W6), the Peacock & Bedrosian conductance maps (10.5066/P9TWT2LU) and extra 3DEP 1 m tiles, then
   mirror them with hashes so H35–H39 can be tested here.
6. **Refresh the site, the status feed and this document** after any of the above, and keep the executive-summary
   download block consistent with `registry/submissions.json`.

## Limitations that bound every claim in this repository

* **No organizer ground truth.** All scores here are proxies. The competition's private expert labels and the
  final-round expanded labels are not observable from this environment, and no leaderboard content is stored
  (DrivenData terms).
* **All historical score numbers are unverified owner/user reports** (0.3195, 0.2941, 0.2477, 0.2600). They are
  never fit targets, never gate values, and never presented on public pages.
* **The two proxies disagree** (IR-29-PROXY-CONFLICT). Conditional on unverified owner/user score claims and file
  associations, the catalogue-hidden proxy matches the reported ordering of three historical files (Spearman +1.0
  on three points) while the SGMC proxy differs (−0.5). Three unauthenticated points are not a calibration curve;
  the historical files' models also saw the hidden components, inflating their catalogue-hidden proxy scores.
* **The new candidate is catalogue-adjacent.** 65.9 % of its dots lie within 300 m of the supplied catalogue, and it
  was trained on every catalogue pixel; its own holdout score would be contaminated, so the number that supports it
  is the per-fold screen number for the same method (0.14086), not a score of the shipped file.
* **Data provenance.** The competition rasters are hash-pinned owner mirrors, not organizer-authenticated downloads
  (IR-DATA-01). Pins prove byte integrity against recorded revisions, nothing more.
* **Sandbox network** reaches only GitHub and PyPI, so free official external layers cannot be fetched here
  (IR-29-SANDBOX-NET); hypotheses are written so they can run on mirrored layers once restored.
* **Compute.** Two cores, ~4 GB RAM, no GPU: the reference solution's U-Net MC-CV ensemble approach is out of reach
  in this environment; the experiments here are gradient-boosted trees on 100 m rasters.
* **Temporary files.** No large raster is committed. H29/core inputs are restored under ignored `<repo>/data`
  by `scripts/restore_data.py` (it does not honor `GEMS_DATA_DIR`); the separate H31 manifest uses
  `scripts/restore_h31_data.py` and `GEMS_DATA_DIR`. Fresh checkouts must restore and verify the appropriate
  manifest before local reproduction. The committed H29/H31 raw evidence remains the authoritative record of
  the failed screens; do not rerun confirmation.
* **Novelty.** "Not tried" means not found in the reviewed repositories (this project's history and the owner's
  sibling repositories), not a claim about other competitors' work.

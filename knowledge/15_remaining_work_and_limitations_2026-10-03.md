# Remaining work and limitations (session 2, 2026-10-03)

## Remaining work, in priority order

1. **Finish and report the factorial** (`scripts/run_fractional_factorial.py`, running). Then freeze the
   supported family set and use it in every later habitat model; the write-up is `knowledge/14_...`.
2. **Calibrate the emission budget.** H34's negative result is caused by an uncalibrated `dti_hat`
   (IR-29-DTI-HAT-CALIBRATION). Re-run the coverage arm with the prior scaled to an expected truth mass
   and with a smaller `round_cap`, on fresh draws (22/23) and a fresh preregistration, before any claim
   that the coverage rule helps.
3. **Implement H35** (interaction-zone habitat) as the Rank-1 geological candidate and gate it on the
   two-proxy admission rule (off-catalogue class ≥3/4 folds positive; catalogue-hidden loss ≤0.005).
4. **Implement one of H36/H37** — both are cheap derived-layer transforms over already-mirrored rasters
   and can share the same screen.
5. **Fix the H31 runner's branch guard** (`scripts/run_h31_worming.py::require_clean_fixed_branch`
   hard-codes `arena/01a10075-gemsdoe29`) and, if the guard is satisfied, run the H31 screen so the
   worming item stops being "unfitted".
6. **Owner actions that cannot be automated here:** fetch the external layers (Siler slip/dilation
   shapefile, Peacock & Bedrosian conductance maps, extra 3DEP 1 m tiles) on an unrestricted machine;
   confirm the masking semantics in the official forum; decide and execute any weekly submission.
7. **Site refresh with the factorial verdict** and the final download list once the run lands.

## Limitations that bound every claim in this repository

* **No organizer ground truth.** All scores here are proxies. The competition's private expert labels
  and the final-round expanded labels are not observable from this environment, and no leaderboard
  content is stored (DrivenData terms).
* **All historical score numbers are unverified owner/user reports** (0.3195, 0.2941, 0.2477, 0.2600).
  They are never fit targets, never gate values, and never presented on public pages.
* **The two proxies disagree** (IR-29-PROXY-CONFLICT): catalogue-hidden favours the historical emission,
  SGMC off-catalogue favours the off-catalogue inventory by ~6x. Until the masking semantics and the
  private target's character are confirmed, any candidate recommendation is conditional on that choice.
* **Data provenance.** The competition rasters are hash-pinned owner mirrors, not organizer-authenticated
  downloads (IR-DATA-01). Pins prove byte integrity against recorded revisions, nothing more.
* **Sandbox network** reaches only GitHub and PyPI, so free official external layers cannot be fetched
  here (IR-29-SANDBOX-NET); the hypotheses are written to run on mirrored layers.
* **Compute.** Two cores, ~4 GB RAM, and no GPU: the reference solution's U-Net MC-CV ensemble approach
  is out of reach in this environment; the experiments here are gradient-boosted trees on 100 m rasters.
* **Temporary files.** All restored data, work arrays and logs live under `/tmp` and do not persist
  between sessions; rerun `scripts/restore_h31_data.py --group all` and `scripts/prepare_data.py`.
* **Novelty.** "Not tried" means not found in the reviewed repositories (this project's history and the
  owner's sibling repositories), not a claim about other competitors' work.

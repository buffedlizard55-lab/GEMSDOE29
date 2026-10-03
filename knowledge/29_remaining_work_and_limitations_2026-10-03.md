# 29 — Session-5 remaining work and limitations (2026-10-03)

Companion documents: `knowledge/27` (frozen bar-protocol preregistration), `knowledge/28` (its results),
`knowledge/22` (session-4 disposition), `knowledge/25` (v4 slate), `evidence/pipeline_verification.json`
(the data/pipeline receipt).

## 1. What this session finished and verified

1. **The standing data blocker is cleared on evidence, not on assertion.** `bash
   scripts/download_competition_data.sh --group all` restored and hash-verified **22/22 manifest entries**
   (11 core + 11 H31-group; 14 distinct files, six pinned in both layouts) into the ignored `data/` tree; `scripts/prepare_data.py` built the aligned
   arrays (footprint 5,167,373 px, labels 60,988 px, 19 bands, 54.6 s); `build_features.py` / `build_addons.py`
   produced the 64-column static block and the 5 add-on columns.
2. **The full train → inference → validate path was proved end to end.** A new
   `scripts/verify_pipeline.py --reproduce` re-ran the registered candidate build and compared hashes:
   **byte-identical** to the registered artifact (`sha256 3537e9fc47a46503…`, 1,591,482 bytes, 37,913 dots),
   with `check_submission.py` returning `ok_to_upload = true` (exit 0). Receipt:
   `evidence/pipeline_verification.json`.
3. **One frozen experiment ran on those bytes and produced a decisive negative** (`knowledge/28`): the H41
   union arm, re-scored on the H34 C0 protocol that defines the slot bar, landed at 0.14597316 with a mean
   paired gain of +0.001183 (frozen bar +0.005), worst fold −0.009202, and the SGMC second proxy at −0.007180
   with 0/4 folds positive. The two frozen controls reproduced the stored session-2 H34 cells **bit-for-bit**
   (max |Δ| = 0.0), so the failure is a property of the H41 columns, not of the environment.
   **Consequence: no candidate file, no weekly slot, next free draw still 32, and the H41/worming family's
   promotion path is closed.**
4. **Two pass-2 defects found and fixed:** the documented download verifier covered only 2 of 5 registered
   artifacts (`IR-29-VERIFY-DOWNLOADS-COVERAGE` — now 5/5 ok plus the two H29 builds at 28 checks each), and a
   register mitigation named a script that does not exist (`IR-29-REGISTER-STALE-SCRIPT`). The executive-summary
   page now explains the historical `[0,1]` rejection from the register, without claiming a verified root cause.
5. **Repository state:** 150 tests pass, `ruff check src scripts tests` clean, `check_site.py` OK,
   `build_draw_ledger.py --check` current, `verify_downloads.py` 5/5 + 28+28 checks with 0 failures.

## 2. Remaining work, in priority order

1. **H43 (DEM drainage organization) — the top unbuilt candidate.** The full implementation plan is written in
   `knowledge/25` §H43 (priority-flood fill, D8 accumulation, stream-power envelope residual and knickpoint
   excess, five columns in [0,1] with the ≥0.2 % nonzero guard). It needs no download, so it is buildable and
   screenable with the data now staged. Preregister it in the `knowledge/24`/`knowledge/27` style on **fresh
   draws 32/33** (the ledger's next free pair) before any fit. If it fails its frozen gates, write the failure
   down like the others.
2. **Fold-geometry robustness.** Every verdict in this project shares the same four 30 % quadrant folds, so all
   seven screen verdicts are correlated through that geometry (`knowledge/22` §4). A frozen geometry swap
   (different quadrant boundaries and/or five folds) is the cheapest way to test whether any *conclusion*
   depends on the fold partition — it changes no draws and no features. This is now more attractive than any
   new feature family, because the H41 case shows a "significant" gain that does not survive a change of cells.
3. **Do not spend a slot below the bar.** `registry/submissions.json` still contains no slot-approved file. The
   rule stands: beat the comparable spatially blocked holdout best on its own protocol, pass fresh confirmation
   and the exact-file audit, and only then consider a weekly slot. The owner decides; the repository recommends
   none today.
4. **Owner-side data (unchanged, blocked here by `IR-29-SANDBOX-NET`):** Siler slip/dilation-tendency shapefile
   (10.5066/P9YL58W6), Peacock & Bedrosian conductance maps (10.5066/P9TWT2LU), extra 3DEP 1-m tiles, and the
   GeoDAWN flight-path binary for H33/H46. Each is free and official; none is reachable from this sandbox.
5. **Site/CI housekeeping — partly done in session 5.** `scripts/check_site.py` now runs as its own step in
   both `.github/workflows/pages.yml` (before the Pages artifact is uploaded) and `.github/workflows/ci.yml`,
   so a stale status page, a score-claim leak, a leaderboard link or a broken local link fails the build
   instead of waiting for a manual check. The `draw_inventory` prose is still not a structured registry
   (`knowledge/22` §5).

## 3. Limitations that bound every claim (standing, re-affirmed)

* **No organizer ground truth.** Both local metrics are proxies: the primary is exact masked DTI against hidden
  components of the supplied catalogue; the secondary is a state-geologic-map fault inventory. Neither is the
  competition's expert-labelled test set, and no leaderboard content is stored or polled.
* **Score claims remain unverified owner/user reports** (0.3195, 0.2941, 0.2477, 0.2600). They are never fit
  targets, gate values, or site content.
* **Owner-mirror bytes are not organizer-authenticated** (`IR-DATA-01`). Hash pins prove integrity against a
  recorded revision; the mirror template itself contains 60,988 label-like ones inside its footprint
  (`IR-TEMPLATE-01`), so template pixel values are never copied into a prediction.
* **Draw reuse is now recorded for the H34 cells** (`IR-29-BAR-PROTOCOL-DRAW-REUSE`): the H41 columns have been
  fitted on draws 20/21, so those cells can never serve as a fresh test for that family again.
* **Compute:** two cores, ~3 GB RAM, no GPU. Screens are gradient-boosted trees on 100 m rasters; the reference
  solution's U-Net ensemble is out of reach in this environment.
* **The H41 mirror carries centroids, not polylines**, so any H41-family result is km-scale prior shaping, never
  dot placement on a trace (`knowledge/26` §3).
* **Novelty** is limited to the reviewed repositories (this project and the owner's siblings), not to all
  competitors.

## 4. Three-pass record for this session

* **Pass 1 (implement + verify):** restored and hash-verified the data; built the caches; reproduced the
  registered candidate byte-identically; froze and ran the bar-protocol stage; wrote its evidence and analyzer
  report.
* **Pass 2 (bugs, edge cases, wrong assumptions):** extended the download verifier to all registered artifacts
  (finding: 3 of the 5 registered artifacts were uncovered) and confirmed 5/5 ok; fixed the stale script name in the register; stopped the
  exec-summary callout from emitting a doubled period; kept the frozen preregistration byte-identical after the
  run (its hash is pinned by `design.json`). Full test suite, ruff, `check_site`, draw-ledger drift check and
  `verify_downloads` all pass.
* **Pass 3 (recheck against the standing brief):** one-click GeoTIFF download and paste-ready note at the top of
  the landing page and the executive summary — present; submission guide subpage — present and now carries the
  `[0,1]` rejection explainer; prompt preserved in `README.md` and pinned by a test; ranked candidate slate with
  named free sources and obtainability statements — present (`knowledge/25`, `registry/hypotheses.json`);
  worming/persistence — screened in four formulations and closed with reasons; factorial experiment — complete
  and reported; why-0.2600 analysis and the strategy document — present (`knowledge/07`, `knowledge/13`); status
  feed — regenerated from script-written JSON, no manual checking required for anything except the owner's own
  portal actions; irregularities — now 51 registered entries, all with status and action.

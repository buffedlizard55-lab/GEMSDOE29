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

## 2. What the merged `main` added after this session's first close-out

A parallel session branch (`arena/01a10342-gemsdoe29`, merged as PR #14) landed between this session's two
pushes. This session verified the merged tree rather than assuming it: 22/22 manifest entries hash-verify,
the template grid matches, caches are complete, and the registered candidate rebuilds **byte-identically**
(`scripts/verify_pipeline.py --reproduce`, 95.0 s, `sha256 3537e9fc47a46503…`) — the receipt is regenerated in
[`evidence/pipeline_verification.json`](../evidence/pipeline_verification.json). Two things changed in the
project's position, and both are recorded in the registers rather than in prose:

* **H43 was implemented and screened on fresh draws 32/33** (40 cells, `knowledge/30`): `A3_knick +0.01419`
  and `A4_union +0.01287` cleared the frozen primary gate — the largest primary gains in the archive — while
  `A1_off +0.00401` and `A2_network −0.00136` failed. Its frozen confirmation on draws 34/35 is **in flight**
  (10 of 40 rows archived) and no process is running, so resuming it is the first scientific task of the next
  session. The next free draw is **36** (`registry/draw_ledger.json` is the only authority).
* **Draws 20/21 are now fitted twice by design**: the H41-A4 bar-protocol re-score reused the spent H34 cells
  for comparability, which is a deliberate reuse rather than a fresh screen — disclosed as
  `IR-29-BAR-PROTOCOL-DRAW-REUSE` and recorded in the ledger's stage list.

## 3. The pass-3 finding: the promotion rule cannot currently be satisfied

Recomputing both proxies from every archived raw cell (23 arm-stages, six stages;
[`evidence/proxy_agreement_review.json`](../evidence/proxy_agreement_review.json),
[`knowledge/32`](32_proxy_policy_review_2026-10-03.md)) shows that **none of the five arm-stages that ever
cleared a primary promotion gate had a positive SGMC sign** — H41 screen `A1`/`A4`, H41 confirmation `A4`,
H43 screen `A3`/`A4`. Since `knowledge/19` §5 makes an SGMC conflict grounds to withhold promotion, the
repository's own rule has blocked every arm its calibrated proxy favoured. The two proxies are also anchored
differently: `knowledge/17` records Spearman **+1.0** for the primary against the only three unverified
owner-reported scores and **−0.5** for the SGMC proxy against the same three. This is registered as
`IR-29-PROXY-VETO-PATTERN` and put to the owner as a decision (keep the veto / demote it to a risk flag /
preregister a calibration study first) — **no label, gate or candidate status was changed here**, and the
recommendation is the conservative one: calibrate first, using the owner's own submission history in
`docs/downloads/` as extra anchors. Until that decision, nothing is slot-approved.

## 4. Remaining work, in priority order

1. **Finish the H43 confirmation on draws 34/35.** The screen passed G1 on `A3_knick +0.01419` and
   `A4_union +0.01287` (the largest primary gains in the archive), the frozen confirmation was launched from a
   clean tree at `bd6811e` and **stopped after 10 of 40 rows**; no process is running. Resume it with the
   documented staged invocation (`scripts/run_h43_screen.py --confirm --resume --max-cells 2`, see
   `knowledge/30` §1 and `IR-29-H43-STAGED-EXECUTION`), never with a fresh design file, then record the verdict
   in `knowledge/30` §5. This is the only in-flight experiment in the repository.
2. **Decide the proxy policy (blocking every promotion).** `knowledge/32` / `IR-29-PROXY-VETO-PATTERN`: no arm
   that ever cleared a primary gate has had a positive SGMC sign, and only the primary proxy has an external
   anchor (+1.0 vs the SGMC proxy's −0.5 on the same three unverified points). Recommended order: preregister
   the calibration study using the owner's own submissions in `docs/downloads/` as extra anchors, then, if it
   holds, demote the SGMC proxy to a published risk flag. Without this decision the repository cannot
   recommend anything, no matter how well the primary proxy scores.
3. **Fold-geometry robustness.** Every verdict in this project shares the same four 30 % quadrant folds, so all
   seven screen verdicts are correlated through that geometry (`knowledge/22` §4). A frozen geometry swap
   (different quadrant boundaries and/or five folds) is the cheapest way to test whether any *conclusion*
   depends on the fold partition — it changes no draws and no features. This is now more attractive than any
   new feature family, because the H41 case shows a "significant" gain that does not survive a change of cells.
4. **Do not spend a slot below the bar.** `registry/submissions.json` still contains no slot-approved file. The
   rule stands: beat the comparable spatially blocked holdout best on its own protocol, pass fresh confirmation
   and the exact-file audit, and only then consider a weekly slot. The owner decides; the repository recommends
   none today.
5. **Owner-side data (unchanged, blocked here by `IR-29-SANDBOX-NET`):** Siler slip/dilation-tendency shapefile
   (10.5066/P9YL58W6), Peacock & Bedrosian conductance maps (10.5066/P9TWT2LU), extra 3DEP 1-m tiles, and the
   GeoDAWN flight-path binary for H33/H46. Each is free and official; none is reachable from this sandbox.
6. **Site/CI housekeeping — partly done in session 5.** `scripts/check_site.py` now runs as its own step in
   both `.github/workflows/pages.yml` (before the Pages artifact is uploaded) and `.github/workflows/ci.yml`,
   so a stale status page, a score-claim leak, a leaderboard link or a broken local link fails the build
   instead of waiting for a manual check. The `draw_inventory` prose is still not a structured registry
   (`knowledge/22` §5).

## 5. Limitations that bound every claim (standing, re-affirmed)

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

## 6. Three-pass record for this session

* **Pass 1 (implement + verify):** restored and hash-verified the data; built the caches; reproduced the
  registered candidate byte-identically; froze and ran the bar-protocol stage; wrote its evidence and analyzer
  report.
* **Pass 2 (bugs, edge cases, wrong assumptions):** extended the download verifier to all registered artifacts
  (finding: 3 of the 5 registered artifacts were uncovered) and confirmed 5/5 ok; fixed the stale script name in the register; stopped the
  exec-summary callout from emitting a doubled period; kept the frozen preregistration byte-identical after the
  run (its hash is pinned by `design.json`). Full test suite, ruff, `check_site`, draw-ledger drift check and
  `verify_downloads` all pass.
* **Pass 3b (after the parallel merge landed):** `scripts/verify_pipeline.py --reproduce` was re-run on the
  merged tree (22/22 manifest entries, template, caches, byte-identical rebuild in 95.0 s); the
  proxy-policy review above was computed from every archived raw cell and registered as
  `IR-29-PROXY-VETO-PATTERN` with a decision asked of the owner; the CI now runs `scripts/check_site.py` in
  both the Pages build and the test job, so no site invariant depends on a manual check; and the review
  script's out-of-tree `--out` path bug was caught by its own new test and fixed (`170 passed`).
* **Pass 3 (recheck against the standing brief):** one-click GeoTIFF download and paste-ready note at the top of
  the landing page and the executive summary — present; submission guide subpage — present and now carries the
  `[0,1]` rejection explainer; prompt preserved in `README.md` and pinned by a test; ranked candidate slate with
  named free sources and obtainability statements — present (`knowledge/25`, `registry/hypotheses.json`);
  worming/persistence — screened in four formulations and closed with reasons; factorial experiment — complete
  and reported; why-0.2600 analysis and the strategy document — present (`knowledge/07`, `knowledge/13`); status
  feed — regenerated from script-written JSON, no manual checking required for anything except the owner's own
  portal actions; irregularities — now 51 registered entries, all with status and action.

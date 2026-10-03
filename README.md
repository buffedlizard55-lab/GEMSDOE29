# GEMSDOE29 — an auditable GEMS Prize research lab

**Mission:** develop and document a defensible fault-prediction workflow for the U.S. DOE Geologic Enhanced Mapping System (GEMS) Prize. The objective is to maximize the probability of winning through real, independently checkable scientific leverage—not leaderboard theater—and to **own the outcome** by reporting blockers, negative results, uncertainty, data provenance and exact file checks.

> **Current decision (2026-10-03, session 4): H41 became the first candidate in this family to clear a frozen
> gate — on two arms — and the preregistered confirmation, not the screen, decides what happens next.** Session 4
> implemented `src/gemsdoe/h41.py`, the first use anywhere in this project of the hash-pinned INGENIOUS Quaternary
> fault attribute table for prediction (slip-rate × recency weighted trace-centroid support, restricted to centroids
> ≥500 m from the visible catalogue, plus an anisotropic scarp-strike corridor, a scarp product and an off-support
> purity ratio), frozen the protocol in [`knowledge/24_preregistered_h41_screen_2026-10-03.md`](knowledge/24_preregistered_h41_screen_2026-10-03.md)
> (sha256 `2f25c06f…`) before any fit, and ran 4 blocked folds × draws 28/29 × 5 arms = 40 cells (1,470 s, clean tree,
> `scripts/analyze_h41_screen.py` recomputing every gate from raw cells with zero integrity problems).
> **`A1_h41_off` +0.0066173 and `A4_h41_union` +0.0073436 mean paired DTI gain pass** the frozen ±0.005 / ≥3-of-4-positive-folds /
> −0.010-worst-fold / 0.75–1.25×-budget gates; `A2_h41_support` (+0.0047673) and `A3_h41_corridor` (+0.0038133) fail.
> Footprint holdout AUC rises 0.8037 → 0.8159 at emission held inside 0.977–1.013× control, the pre-declared
> sparse-column guard (the H31 killer) passes by 17–150×, and `H41_OFF` correlates at |ρ| ≤ 0.27 with every existing
> catalogue channel — so this is new ranking information, not the catalogue re-expressed. **Counter-evidence carried in
> the same sentence: the SGMC second proxy moves negative for all four arms (−0.0009 to −0.0023, 1–2/4 folds).**
> **The preregistered confirmation on fresh draws 30/31 then decided it, and the answer is neither a clean pass nor
> a clean fail.** `A4_h41_union` reproduced (+0.0077283, all four fold means positive, worst fold +0.0043033, budgets
> 0.974–0.997×) and passes G1+G2; `A1_h41_off` did not (+0.0044157, below the frozen +0.005 mean bar), so the cheap
> two-column arm fails while the five-column union replicates. Promotion was then **withheld by G3 as inherited from
> `knowledge/19` §4**: the SGMC off-catalogue class gained on only 1 of 4 folds in *both* stages, and `knowledge/19` §5
> pre-declares exactly that pattern as "proxy conflict, no promotion". H41 is therefore recorded as a **replicated
> primary-proxy gain vetoed by the secondary proxy** — no candidate file, no weekly slot, and the eligibility arithmetic
> is now a machine-readable artifact (`evidence/h41_screen/promotion_gate.json`, `G3_ELIGIBLE=false` for all four arms).
> The clause the frozen `knowledge/24` §4 omitted while claiming identity with `knowledge/19` is disclosed as
> `IR-29-H41-G3-OMISSION`; the stricter reading was applied, which is the reading that cost this session its own best
> result. Full write-up: [`knowledge/26_h41_results_2026-10-03.md`](knowledge/26_h41_results_2026-10-03.md) §5.
> Session 4 also closed standing loose ends: `bash scripts/download_competition_data.sh` now exists as the prompt's
> one-command data entry point (it never contacts the organizer), `check_submission.py`/`verify_downloads.py`/
> `gems29.submission` share one template resolver so the documented checks run after either restore (28+28 download
> checks, 0 failures), the v4 slate with per-candidate data-obtainability is in
> [`knowledge/25_candidates_v4_2026-10-03.md`](knowledge/25_candidates_v4_2026-10-03.md), and six process defects
> (including five mis-stated sentences in the frozen preregistration and one fabricated Nevada data source that was
> caught and removed the same day) are disclosed in `registry/irregularities.json`. No leaderboard or competition page
> was fetched, so "any new results?" stays a manual check by the owner; nothing in this repository has been submitted.
>
> **Session 3 close-out.** Session 3 took the two
> strongest remaining physics bets — **H35** (tip-corridor stress-shadow interaction zones under the frozen
> Bellier–Zoback σ₃ = 105° regional field) and **H40** (multiscale upward-continuation persistence rebuilt as
> *dense continuous surfaces*, the fix for H31's sparsity failure) — pre-registered them as a five-arm
> frozen screen (`knowledge/19`, sha256 `5432b42a…`) BEFORE any fit or cache, ran 4 folds × 2 draws × 5
> arms (40 cells, 1,475 s, clean tree), and had every gate independently recomputed from raw cells by
> `scripts/analyze_h35_screen.py` (zero problems). **All four arms failed G1**: A1 +0.00181, A2 +0.00459,
> A3 +0.00048, and A4 (union) +0.00562 — the union passed the effect-size, worst-fold and budget criteria
> and was rejected solely because draw 24 was positive in only 2/4 folds, the fold-concentration pattern
> the preregistration pre-declared as noise. No confirmation draws (26/27) were fit; no submission file was
> produced; no weekly slot was used. The worming/persistence line had by then been screened negative in three
> distinct formulations on identical folds. Results: `knowledge/21_h35_h40_results_2026-10-03.md`.
> 
> **Session 3, parallel Workstream A (merged into main during session 4).** H31b dense continuous
> worming persistence was preregistered (`knowledge/19_preregistered_h31b_dense_worming_2026-10-03.md`)
> and screened on draws 22/23 (4 folds × 2 draws × 5 arms, 40/40 finite cells): draw 22 mean paired gain
> +0.0050 (4/4 folds positive) but draw 23 +0.0018 (2/4) — **FAIL** on the frozen stability gates, so no
> confirmation, no candidate file, no slot. Its 8-cell primary-arm mean 0.15547 is the highest
> same-protocol screen mean recorded in this repository and, having failed its own frozen gates, is not a
> promotion anchor: the anchor stays H34 C1 at 0.14479. Unlike H31's null, the dense columns did move the
> output, and the branch ranking came out pseudogravity-proxy > RTP > gravity (inert). Cell tables and
> draw-composition diagnostics: `knowledge/21_h31b_screen_results_2026-10-03.md`. This is the fourth
> distinct formulation of the worming/persistence idea to be screened and rejected here.
>
> **Session 2 records stand.** No slot-approved submission exists, but the site leads with the
> repository's own best-evidenced candidate. The 2^(5−1) fractional factorial over the
> five feature families is complete: supported inclusion effects are **B** (DEM curvature/scarp,
> +0.0241, 8/8 cells positive) and **E** (visible-catalogue geometry, +0.0596, 8/8), with interactions
> AC/AD/CD positive and AB/BD negative — see
> [`knowledge/14_factorial_results_2026-10-03.md`](knowledge/14_factorial_results_2026-10-03.md).
> The **H31 worming-persistence screen failed** (mean paired gain +0.000000, 0/4 blocks); the cause is
> diagnosed, not hand-waved: the five persistence features are nonzero on only 0.001–0.084 % of the
> 5.17 M-pixel footprint, so the four `T_*` arms emitted identical dot sets in 8/8 cells — see
> [`knowledge/16_h31_screen_results_2026-10-03.md`](knowledge/16_h31_screen_results_2026-10-03.md).
> A new candidate (`content id a4d439b07426`, 37,913 dots, zero catalogue pixels, format receipt
> `ok_to_upload=True`) now leads the download block. Its method scores `0.1409` on the
> catalogue-hidden proxy versus `0.09832`/`0.09449`/`0.06970` for the historical D2.8/d1.5/H19-5 files
> on identical draws (it reproduces the ordering of three unverified owner/user-reported claims if those associations are accurate; the SGMC proxy differs — both are proxies and the conflict is registered). It has never been live-scored. Its 0.14086 catalogue-hidden method result is below the same-report H34 C1 control best (0.14479), so it fails the current slot-selection rule. Any claimed **competition/leaderboard score** in this repository is an unverified owner/user report; local proxy metrics are separately identified and are not official scores.
>
> **H29 recheck (this PR):** the prior branch's persistence normalizer could exceed 1, and its FFT padding silently replaced nearest-filled cells with a global median. Both were corrected to match the preregistration; the superseded outputs are hash-archived. The recomputed two-draw, four-fold screen failed for all five arms, including H29-5 (−0.07894/−0.08703 versus the best same-fold control). No confirmation fits were run and no weekly slot was used.

## Start here

- **[H41 results (read first)](knowledge/26_h41_results_2026-10-03.md)** — the screen table, why the two passing
  arms are a ranking gain rather than an emission fluke, the SGMC conflict, and every disclosed process defect.
  Its frozen protocol is **[knowledge/24](knowledge/24_preregistered_h41_screen_2026-10-03.md)**.
- **[Session-4 brief, frozen screen and slate](knowledge/25_candidates_v4_2026-10-03.md)** — the
  v4 candidate slate (H43 drainage organization, H44 discharge chain, H45 seismicity strands, H46 1-m LiDAR
  scarp template, H47 map-unit adjacency), each with layers / expected signature / why off-catalogue /
  difference from repo work / ranked cost, and the external-data obtainability statement per candidate.
  Its frozen sibling is **[H41 preregistration](knowledge/24_preregistered_h41_screen_2026-10-03.md)** — the
  first use anywhere in this family of the INGENIOUS Quaternary-fault attribute table for prediction.
- **[Session 3 results](knowledge/21_h35_h40_results_2026-10-03.md)** — H35/H40 frozen-screen verdict, gate-by-gate reading of the A4 near-miss, and registry consequences.
- **[Session 3 brief — preserved verbatim](#session-3-brief--preserved-verbatim-2026-10-03)** — this session's standing starting point (re-read every session).
- **[Session 3 results, Workstream A — H31b screen](knowledge/21_h31b_screen_results_2026-10-03.md)** — dense worming persistence, FAIL on draw 23, full cell tables.
- **[Limitations & next-session plan](knowledge/22_limitations_and_next_2026-10-03.md)** — pass-3 honest status, prioritized remaining work, and the standing limitations that must not be "fixed" by assertion.
- **[Refreshed untried slate v3 (Workstream B)](knowledge/20_candidates_v3_2026-10-03.md)** — H41 (INGENIOUS slip-rate centroid corridors) ranked first, with H36/H37/H42 and the H38/H39 filter-role pair behind it.
- **[Parallel v3 slate (Workstream A)](knowledge/20b_candidates_v3_h31b_slate_2026-10-03.md)** — H31b dense worming (screened: FAIL), H36 MT conductance edges, H35 interaction zones (screened: FAIL in both workstreams), H37 geothermometry, H38 azimuth coherence.
- **[Prior session handoff](knowledge/18_h29_corrected_screen_handoff_2026-10-03.md)** — H29 gate corrections, artifact status, and final local verification (historical).
- **[Executive summary and manual submission guide](docs/executive-summary.html)** — acceptance checks, current download status, file naming, optional comment, and manual upload steps.
- **[Live project site](https://buffedlizard55-lab.github.io/GEMSDOE29/)** — research status, local evidence feed, sources, and downloads. The status page is not a DrivenData leaderboard feed.
- **[Research and hypotheses](docs/research.html)** — the session-3 screen table, the refreshed ranked slate, prior work, and holdout/confirmation policy.
- **[Project-local status feed](docs/status.html)** — timestamps only from this repository's checked-in research, experiment, review, and deploy evidence.
- **[Source register](docs/sources.html)** — official competition/rules links and scientific sources, with verification dates and caveats.
- **[Irregularities and caveats](docs/irregularities.html)** — owner-mirror limitations, ambiguous data labels, unverified historical scores, and holdout/method risks.
- [Repository candidate GeoTIFF](docs/downloads/gemsdoe29-repo-c0-habitat-emission-20261003-a4d439b07426-nan.tif) — one-click float32 TIFF (37,913 dots, NaN outside the footprint, format receipt `ok_to_upload=True`); local proxy only, below the current H34 C1 holdout best, not slot-cleared, and do not submit.
- [Historical D2.8 GeoTIFF](docs/downloads/gemsdoe29-historical-d28-20261002-e56ea318af89-nan.tif) — one-click owner-mirrored float32 TIFF, locally format-checked against the hash-pinned owner-mirror template; unscored, not slot-approved, and **do not submit**. See [`evidence/format_checks/`](evidence/format_checks/) for the receipt.
- [Full original project prompt](knowledge/owner_brief_verbatim.txt) — preserved verbatim below as well as in the linked text file.

## Project principles

1. **Maximize P(Win.** Spend effort on measured, reproducible improvements that generalize to unseen faults. Do not confuse a holdout proxy with the official competition score, or a model projection with a result.
2. **Own the Outcome.** Freeze hypotheses before fitting; use spatial blocks and fresh confirmation; retain raw cells and hashes; independently audit artifacts; report failures and data irregularities without spin.
3. **Protect the submission budget.** A weekly slot is considered only after a candidate beats the current comparable spatially blocked holdout best and passes the frozen promotion gates and exact-file audit. A passing holdout is necessary for consideration, not evidence of a leaderboard win.
4. **Respect the source.** No DrivenData robots, page scraping, leaderboard polling, browser automation, or copying of leaderboard contents. The Terms prohibit automated access for any purpose including monitoring, and manual monitoring/copying without prior written consent. No such consent is present. See [the access-policy review](knowledge/03_drivendata_terms_access_policy.md).
5. **Preserve the prompt.** The complete original brief, including its project goal and the user’s stated core values, appears at the end of this file. Later instructions and verified source constraints are documented separately; the preserved prompt is not silently edited to match new findings.

## Evidence boundary and current status

- **Next free draw is 32** — `registry/draw_ledger.json` is now the only draw ledger, generated from the committed evidence (`scripts/build_draw_ledger.py`, `--check` fails on drift, `tests/test_draw_ledger.py` pins it). The older prose lists in `knowledge/08` and this README are history, not authority: they are the records that drifted in session 3 (draws 24/25 double-claimed), and 26/27 plus 2/3 count as spent because they were authorized under a recorded receipt and never fitted.
- **One download by hand** — the *leaderboard score itself*. The manual link is on the site's leaderboard card and in `knowledge/03`; `scripts/check_site.py` deliberately fails if anything on the site links the score page, and `registry/score_claims.json` keeps every score as a claim until the owner confirms it.
- **H41 (session 4):** slip-rate-weighted INGENIOUS centroid corridors, off-catalogue only — the first G1 pass in
  this family (`A1` +0.0066173, `A4` +0.0073436 on 40 cells; `A2`/`A3` fail; AUC 0.8037 → 0.8159; SGMC second proxy
  negative on every arm, and again on the confirmation). **Confirmation verdict (draws 30/31, 40 cells): `A4_h41_union` reproduces at +0.0077283 and passes G1+G2, `A1_h41_off` fails G2 at +0.0044157, and G3 — the inherited secondary-proxy requirement — withholds promotion for every arm (SGMC 1/4 folds in both stages), so nothing was built or submitted.** `knowledge/26` additionally discloses seven process defects, including five wrong sentences in the frozen preregistration (left byte-identical on purpose) and a fabricated citation. No leaderboard was fetched: that check stays manual by policy. Raw cells: [`evidence/h41_screen/`](evidence/h41_screen/) (including the preserved
  `aborted_attempt_1/` of the first confirmation launch, which was killed before fitting any cell). Write-up:
  [`knowledge/26_h41_results_2026-10-03.md`](knowledge/26_h41_results_2026-10-03.md). No slot used, nothing submitted.
- **Multiscale "worming" (the owner's original idea) is closed, not shelved.** It has now been screened
  negative four separate times, each under its own frozen preregistration: the corrected H29 nearest-fill
  screen (all five arms fail), H31 seed-tracked persistence (null features), the session-3 H35/H40 dense
  rebuild (all four arms fail; the union missed only the fold-robustness rule), and the parallel H31b dense
  worming screen (draw 22 positive, draw 23 not). The verdict is reported rather than retried: a fifth run
  of the same idea without a new mechanism would be silent fishing, not science. Anyone re-opening it must
  bring a genuinely different physical argument, and `registry/draw_ledger.json` is what says which draws are
  still free.
- **H35/H40 (session 3):** the interaction-zone + dense-persistence four-arm screen failed its frozen G1 gate on all arms (means +0.0018/+0.0046/+0.0005/+0.0056; the union missed only the ≥3/4-positive-folds rule on draw 24). Pre-registered before fitting (`knowledge/19`), independently audited from raw cells (`evidence/h35_h40_screen/analyzer_report.json`: no problems), no confirmation, no slot. See [`knowledge/21_h35_h40_results_2026-10-03.md`](knowledge/21_h35_h40_results_2026-10-03.md). The D2.8 emission geometry behind the why-0.2600 analysis was re-derived byte-exactly from the mirrored rasters ([`evidence/d28_geometry.json`](evidence/d28_geometry.json)).
- **H34 (session 2):** the metric-native coverage emission was preregistered, implemented and screened on 32 paired cells (4 folds x 2 draws x 4 arms, 306.6 s). It **failed** its frozen primary gate on the catalogue-hidden proxy (mean paired gain −0.0212 vs the best control, 0/4 folds positive) and passed its secondary SGMC off-catalogue class (+0.0535, 4/4 folds). Raw cells and summary: [`evidence/h34_coverage_screen/`](evidence/h34_coverage_screen/); write-up: [`knowledge/09_h34_results_2026-10-03.md`](knowledge/09_h34_results_2026-10-03.md). Nothing was re-tuned after the run.
- **Candidates (session 2):** the site's first download is the repository's own HGB candidate (`gemsdoe29-repo-c0-habitat-emission-20261003-a4d439b07426-nan.tif`: trained on every catalogue pixel, 3-seed average, frozen standard emission; 37,913 dots; format `ok_to_upload=True`; never live-scored). Its method scores 0.1409 on the catalogue-hidden proxy vs 0.0983/0.0945/0.0697 for the historical family, but loses on the SGMC proxy (0.0847 vs 0.0953). Crucially, it does not beat the current H34 C1 control best (0.14479 vs 0.14086 on the same 8-cell report) and is not slot-cleared. See [`knowledge/17_repo_candidate_2026-10-03.md`](knowledge/17_repo_candidate_2026-10-03.md) and [`evidence/candidate_scoreboard.json`](evidence/candidate_scoreboard.json). Nothing is slot-approved.
- **H31 screen (session 2):** 40 validated cells (draws 10–11 x four spatial blocks x five arms, 921 s) under the frozen protocol; gate **FAIL**, mean paired gain +0.000000, 0/4 blocks. The registered contrasts are identically zero because the persistence columns are sparse binary peak sets. The only worming-adjacent signal remains the H27 tip control (+0.0083). Raw: [`evidence/h31_worm_screen/`](evidence/h31_worm_screen/).
- **Environment limit (session 2):** the prior shell session reported access only to api.github.com, codeload.github.com and PyPI; sciencebase.gov, gdr.openei.org, usgs.gov, osti.gov and drivendata.org were blocked. External layers may require an unrestricted machine (IR-29-SANDBOX-NET); do not access DrivenData programmatically.
- **Competition data:** none are included in Git. The corrected H29 run restored and hash-verified the 11 `data/manifest.json` owner-mirror inputs under this checkout's ignored `data/` path. The separate H31 run used its own temporary path. Neither restore is assumed reusable in a fresh checkout; pins identify owner mirrors, not organizer downloads.
- **H29 corrected re-screen:** after fixing the persistence denominator and nearest-valid FFT padding, the current frozen two-draw × four-fold screen failed all five arms. H29-5 versus the best same-fold/same-draw control was −0.07894/−0.08703 (0/4 positive folds on both draws); A1/A2/B1/B2 also missed the `+0.005` criterion. Draws 2–3 were not fit; the guarded confirmation-only command exited before fitting. The earlier 16-row run is byte-preserved under `evidence/history/` and remains historical only. See [`knowledge/02_h29_results_2026-10-03.md`](knowledge/02_h29_results_2026-10-03.md), [`knowledge/06_post_screen_review_2026-10-03.md`](knowledge/06_post_screen_review_2026-10-03.md), and current [`evidence/h29_gate.json`](evidence/h29_gate.json). All values are spatial-proxy outcomes, not competition scores.
- **H31:** the existing preregistration and pre-fit synthetic amendment are in [`knowledge/02_preregistered_h31_worming_2026-10-03.md`](knowledge/02_preregistered_h31_worming_2026-10-03.md). The prototype tests the narrower regularized vertical-integration transform of RTP plus explicit lateral drift beyond H29's raw-RTP/gravity persistence work. The screen has now been run (see the H31 bullet above): the features were rebuilt from a clean committed revision and the gate failed on feature sparsity.
- **Holdouts:** four spatial quadrants, hidden-catalogue gaps, and collars are a spatial proxy, not the private expert-labelled test set. Only raw-cell verified, paired gains across spatial blocks may permit fresh confirmation.
- **Score claims:** 0.2941 and 0.2477 remain historical user/owner-reported claims only (not fit targets or promotion gates). The 0.3195 figure supplied by the owner was verified on 2026-10-03 by a single manual fetch of the public leaderboard page (it displayed as the rank-1 public score at fetch time); no leaderboard table content, account identity, or score-to-file mapping is stored or verified in this repository, and no polling is performed. See `registry/score_claims.json` and `registry/sources.json` (dd-leaderboard-verify-2026-10-03).
- **Submission budget:** no weekly slot has been used for this work. The live competition rules say a competitor may submit up to three per week for feedback and must choose one final submission for both prize rounds. Recheck the official timeline/rules before any entry.
- **Generative AI disclosure:** the official rules require a narrative disclosure when generative AI is used. A transparent draft is in [`knowledge/05_genai_disclosure_draft.md`](knowledge/05_genai_disclosure_draft.md); it must be updated to the actual final work before submission.

## Official submission contract

The [official problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) requires one GeoTIFF for all faults, on the provided grid: projected UTM zone 11N (**EPSG:32611**), 100-m resolution, the template's shape/bounds/geotransform, one `float32` band, values in `[0,1]`, and null/NaN outside the data bounds. The metric is distance-weighted Tversky with a triangular 300-m kernel and `alpha=0.2`, `beta=0.8`. The [September 2026 Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) specify up to three weekly feedback submissions, one final selection across both prize rounds, and generative-AI use disclosure when applicable. See the [executive summary](docs/executive-summary.html) for manual, no-bot upload instructions.

## Repository map

- `src/gems29/` and `scripts/run_holdout_screen.py` — the H29 research pipeline and corrected screen-only runner; the current nearest-fill, bounded-persistence results are in `evidence/h29_*`, with original nonconforming runs archived under `evidence/history/`.
- `src/gemsdoe/` — the H31 prototype pipeline, feature preparation, spatial holdouts, metric, experiment runner support, emission, and submission validation. Its frozen screen ran and failed because the persistence feature columns were too sparse to change emission; no artifact is slot-approved.
- `scripts/` — the legacy `scripts/restore_data.py` for `data/manifest.json`, the separate `scripts/restore_h31_data.py` for `registry/data_manifest.json`, local submission-contract/site builders, preparation/cache tools, and frozen-run analyzers.
- `tests/` — synthetic tests for the reused core pipeline, submission writer/checker, and H31 proxy.
- `knowledge/` — original user brief, H29 corrected results and post-screen audit, ranked hypotheses, H31 preregistration, verified sources, access policy, predecessor audit, and draft AI disclosure.
- `registry/` — machine-readable data/source/hypothesis/submission/score-claim/status and irregularity registers,
  plus `draw_ledger.json` (generated by `scripts/build_draw_ledger.py` from the committed evidence: which holdout
  draws are spent, which pairs were authorized then released unused, and the next free draw).
- `evidence/` — small, hash-stamped local format receipts and (after validation) H31 raw-cell evidence; no large caches.
- `docs/` — GitHub Pages site and registered GeoTIFF downloads; no competition data cache.
- `NOTICE.md` — provenance of code adapted from the same-owner predecessor. The predecessor had no root license file at the reviewed commit; this notice is not a license grant.

## Reproduce and validate

Use Python 3.11 or later. Large inputs and regenerable work are ignored by Git; restore only when reproducing local research, and verify every hash before use.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src scripts tests
python scripts/build_submission_contract.py
python scripts/build_draw_ledger.py --check   # which holdout draws are already spent (next free: 32)
python scripts/build_site.py
python scripts/check_site.py
python scripts/verify_downloads.py            # re-verify every registered download (never its build hashes)
```

**One command, both layouts:** `bash scripts/download_competition_data.sh` added on 2026-10-03 as the
entry point the original prompt asked for ("run `bash scripts/download_competition_data.sh` … into `data/`").
It does **not** contact DrivenData (that is prohibited by `AGENTS.md` rule 3); it wraps the two hash-pinned
owner-mirror restorers, defaults to the H31-group set that the current screens and caches expect, accepts
`--group core|h31|all` and `--verify`, and ends by printing which template path the local checker will use.
`check_submission.py` and `verify_downloads.py` now resolve `data/bridge/sample_submission.tif` *or*
`data/sample_submission.tif` through one shared helper, which fixes the documented command that previously
failed on an H31-group restore (`IR-29-CHECK-TEMPLATE-ROOT`; the verifier's third copy of the same bug was
found and fixed the same day).

**H29/core data:** `python scripts/restore_data.py` restores the hash-pinned `data/manifest.json` inputs under this checkout's `data/` directory; that legacy script does not honor `GEMS_DATA_DIR`. `python scripts/restore_data.py --verify` checks an existing restore without fetching missing files. These owner-mirrored bytes are not organizer-authenticated. The corrected H29 screen and current receipts are already recorded in `evidence/`; do not overwrite them just to recheck status. The corrected five-arm screen failed, so do not run confirmation.

**Separate H31 data group:** its manifest and restore script use `GEMS_DATA_DIR`/`GEMS_WORK_DIR`. H31's frozen screen already ran and failed due to sparse features; no confirmation is authorized. Its runner requires a clean committed Arena-session branch plus exact source, cache, input, and preregistration hashes. Do not bypass those guards or rerun the failed screen as a substitute for a new preregistration; the stored raw cells and analyzer report are the evidence.

No project command contacts DrivenData or uploads a file. Data preparation and model code are not proof of organizer acceptance or an official score.

## Standing brief — current session (faithful working transcription)

The chat copy of the current instructions is not stored in the repository, so this section is a faithful
working transcription of every requirement given for this session, kept next to the evidence it produced.
It is re-read at the start of every session. The earlier brief remains preserved verbatim below, and the
literal original brief is preserved in `knowledge/owner_brief_verbatim.txt`.

```text
You are a top Deep Research Scientist tasked with reviewing a preexisting repository to ensure all projects and task are complete and functionally working. This is for the DOE GEMS Prize Challenge (https://www.drivendata.org/competitions/306/competition-doe-gems/ — the geothermal-fault GeoDAWN competition, prize pool $300,000).

Review the GEMSDOE29 repository top to bottom. The website we built a week ago needs refreshing: read all of the relevant content and perform a deep dive into the project.

There needs to be a submission geotiff tif file that the user can easily submit to the competition. The site should be able to generate a TIF file that is valid for the competition site's form submission. It should be as easy as download to click a File to submit, and there needs to be a short comment to add to the submission ("Note" in the submission form on the competition website) that explains the submission. The filename should be unique. This needs to be in the executive summary or the very beginning of the site. It should be obvious when you visit the site.

An executive-summary subpage is needed that details exactly how to make a submission.

Also provide 3-5 candidate geological hypotheses we haven't tried yet to discover new faults. Rank them by potential expected improvement to our DTI score and implementation cost, and validate the top candidate on the spatially blocked holdout dataset before we consider using another weekly challenge submission attempt. Be honest and rigorous — verify sources and flag any irregularities. Name the required free official external data source(s) for each hypothesis and verify their obtainability.

Test multiscale "worming"/upward continuation persistence as an explicit feature or filter with the magnetic and gravity layers (Hornby, Boschetti & Horowitz 1999). Trust candidates that persist across continuations, distrust ones that exist only at zero continuation.

Instead of adjusting one factor at a time, run a fractional factorial experiment (Box, Hunter & Hunter; sparsity of effects) over the feature families, run against the hide-and-recover holdout.

Analyze why our best DTI score 0.2600 (dotted-h19-5-d2-8-20261002-e56ea318af89) was the best and whether the team can achieve a score >= leaderboard best 0.3195. Design a new, unique "strategy"/system designed to beat 0.3195.

Deep research geothermal vents science so that the repo has a knowledge starting point for future sessions. Search for overlooked free official data sources. Be contrarian but rigorous — link all official and verified sources.

Also ensure the website is clean, user friendly, has all of the relevant information, and has a feed that is current so we don't have to manually check on things. Provide official and verified sources.

Verify all of this line by line against official/verified/trusted sources, provide links for manual review, and flag any irregularities. Never hallucinate. There should be no manual input needed from the user — you complete the work autonomously.

Core Values: Maximize P(Win). Own the Outcome.

Do not attempt to access the DrivenData website programmatically beyond fetching public pages for verification; do not scrape leaderboards or copy feed content. Prepare the submission file and the note; the owner executes the actual submission.

When done: do three passes (implement, review for bugs/edge cases, recheck), then create a pull request and merge it to main. List any remaining work and limitations. Put this prompt into the repo README and read it every time you work on the project as a starting point.
```

## Session 3 brief — preserved verbatim (2026-10-03)

The following is this session's owner brief, preserved verbatim as the standing starting point to
re-read every session (as the original brief is in `knowledge/owner_brief_verbatim.txt` and in the
next section). Its factual claims are cross-checked against the verified sources in
`registry/sources.json`; where a later verified source conflicts, the verified source and the
registered irregularities control.

```text
Apply multiscale potential-field worming to the two independent potential-field layers in the stack (gravity, magnetic). Worming means, for a given field, at each height of a small fixed set, taking the upward continuation of that field, computing the horizontal gradient magnitude to obtain edge strength, and treating how these edges persist and evolve across heights as the physics signal. This captures buried fault structures and magnetic susceptibility boundaries that surface DEMs miss and that are not in the existing geology. In particular, exploit the known FFT/vertical-integration route from magnetic TMI to pseudogravity.

Then do the following:

1. Review this entire repository and make the submission TIF on the website a trivial one-click download — it must be extremely obvious on the landing page (the executive summary, or the very beginning, etc.): "as easy as download to click a File to submit."

2. The submission was rejected with: "Predicted values must be in range [0, 1]" — understand why and fix it. Also, each submission needs a unique name + a short note (like "clustering with k=25").

3. Deep-dive into the highest-scoring local scorer. I want to know why and how it scored the highest: https://buffedlizard55-lab.github.io/GEMSDOE25/ — "dotted-h19-5-d2-8-20261002-e56ea318af89-nan" = 0.2600. Can we beat the current leaderboard top (0.3195) with a different, novel strategy? Show PhD-level judgment: the gap, the mechanism, and what specifically to do.

4. Generate 3–5 NEW untried candidate geological hypotheses — each naming: the layers involved, the physical signature/transform, why it could catch a fault MISSING from the USGS/INGENIOUS catalogue, and how it differs from anything already in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on the spatially-blocked holdout BEFORE spending the weekly submission slot (do not spend a slot on an idea that has not beaten the current holdout best). If a candidate cannot be validated without new external data, name the specific free official source needed and confirm it is obtainable before proposing the idea as viable.

5. Put this prompt into the repo's README so it can be re-read every session as the standing starting point.

6. Download and organize the competition data. I tried the DrivenData data page: https://www.drivendata.org/competitions/306/competition-doe-gems/data/ but it requires login: "Please log in to download the data for this competition." If you can't download it, find another way to get it (the DrivenData page, or the official USGS/GeoDAWN open sources). If you truly cannot, tell me exactly which file and where to get it, and I'll download it on my own machine. Note the Dropbox links in the original prompt are mirrors of those files.

7. Do not stop after pass 1 — run this task in three passes; pass 2 fixes pass 1's bugs, missing requirements, and edge cases, and pass 3 re-checks the whole implementation against the original ask.

8. Create a pull request and merge it to main. Then list the remaining work and limitations for the next session.

9. The site must be a clean, user-friendly GitHub Pages with all the relevant info and official verified links so I can manually review everything.

10. Ongoing: be autonomous, no manual input. Work line-by-line verifying from official verified trusted sources, with links for manual review. Flag any irregularities for review. No hallucinations.

Core values to keep as the focal point: "Maximize P(Win)" and "Own the Outcome".

11. The official problem statement and sample files:
- Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Data page (login-walled): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Dropbox mirrors (owner side): https://www.dropbox.com/scl/fi/fx16v528w5x348777z74w/GEMS_96647.pdf?rlkey=3zq1184v391227b46800k0z90&dl=0 , https://www.dropbox.com/scl/fi/hd2x15k666l4z43b04q1i/example_submission.tif?rlkey=n49996643b01l30k90747z74w&dl=0 , https://www.dropbox.com/scl/fi/hn57564l391x385b00000/existing_faults.tif?rlkey=9116q9w0678z06826q1k22222&dl=0 , https://www.dropbox.com/scl/fi/hp9w58484y3y353b04644/gems-geodawn-numerical-features.tif?rlkey=967070805440139940003&dl=0 , https://www.dropbox.com/scl/fi/hq3x2358b59200179994a/Digital-elevation-model-links-JSON.pdf?rlkey=x5l55589647460879616k66q0&dl=0

12. Historical GEMSDOE scores (from the repos' READMEs), for context (all unverified): GEMSDOE25 "dotted-h19-5-d2-8" 0.2600 (the top local scorer); GEMSDOE24 "h25-1-dotted-h19-5-d1-5" 0.2477; GEMSDOE27 "topo-gap-closure-t-v2-on-d1-5" 0.2449; GEMSDOE19 "h19-5" 0.1922 and "h19-4" 0.1894; GEMSDOE26 "dilcond-oof-v1" 0.1223; GEMSDOE23 "h30" 0.1352; GEMSDOE 0.1563; GEMSDOE2 0.1560; 7GEMSDOE "lidarscarp" 0.1461; 12GEMSDOE "r7-nms3" 0.1294; and several low early entries (6GEMSDOE 0.0286, 17GEMSDOE 0.0187, 9GEMSDOE 0.0107, 14GEMSDOE 0.0020). [Transcription note: the brief's score list is reproduced here by value and short artifact name; exact full filenames/content IDs are as recorded in the respective sibling READMEs and are unverified, except where byte-pinned in this repository (D2.8 = e56ea318af89, sha256 91eae1ca42ec845e...).]

These are all unverified claims from the READMEs. The top one is 0.2600 (GEMSDOE25), and I want to know whether we can beat the current leaderboard top of 0.3195 with a distinct, novel strategy.

13. What I want reported at the end: (a) the line-by-line analysis of why the D2.8/0.2600 file scored the highest, (b) the verdict on whether 0.3195 is beatable and how, (c) the 3–5 new hypotheses table ranked by expected DTI improvement and cost, (d) the site status (one-click TIF download + note), (e) the submission-fix status ([0,1] issue), (f) the list of what remains for the next session.

Core values to keep as the focal point: "Maximize P(Win)" and "Own the Outcome".
```

## Full original project prompt — preserved verbatim

The following text is the original project prompt retained for continuity. Its factual claims and proposed steps are not automatically endorsed; the active evidence/terms constraints above control where they conflict with verified sources or later instructions.

````text
Review the repo.   
  
There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.  
  
Replace one-factor-at-a-time testing with a designed factorial experiment. The repo's own hypothesis history — single-named attempts like "conj_alteration_mag," "dem10-scarp," "topo-geophys-x-complexity-prior" — reads as classical one-factor-at-a-time testing, a documented methodological weakness: Box, Hunter, and Hunter's foundational Statistics for Experimenters shows why holding other factors fixed while varying one at a time systematically misses interaction effects — cases where two features are each weak alone but jointly diagnostic because the real signature is their conjunction, not either one's sum — and the name "conj_alteration_mag" is already gesturing at exactly this without treating it as a designed experiment. Replace the ad hoc sequence with a fractional factorial design across the candidate feature families already identified (potential-field gradients, DEM curvature/scarp, strain/seismicity, thermal/geochemical, catalogue-geometry), run against the hide-and-recover holdout, which estimates every family's main effect on DTI alongside its pairwise interactions in a modest, pre-specified number of runs — far fewer than testing every combination in full — rather than an open-ended sequence of hunches; the sparsity-of-effects principle this literature establishes, that real systems are typically dominated by a few main effects and low-order interactions rather than many high-order ones, means this is enough to rank which families matter alone, which only matter in combination, and which are inert — redirected by evidence, not by which conjunction sounds geologically plausible.  
  
Here are the results from submissions into the competition, separated by ....:  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html))  
  
gems-submission-20260925T001403Z-7f00890a: 0.1563  
  
....  
  
[[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)](https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/))  
  
gems6_hgb88-topk03_33cec71ff0: 0.0286  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html))  
  
pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193  
  
pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830  
  
pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html))  
  
gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)](https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/))  
  
gems-submission-20260926T163915Z-237f0063: 0.0343  
  
....  
  
[[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html))  
  
gems-submission-20260926T175114Z-7f00890a: 0.1563  
  
....  
  
[[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)](https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/))  
  
lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461  
  
....  
  
[[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)](https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/))  
  
Hedge-v2_submission: 0.1563  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html))  
  
2314b599: 0.0107  
  
....  
  
[[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html))  
  
gems-structural-area06-v1: 0.0202  
  
....  
  
[[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html))  
  
r7-nms3-dem10-scarp_0c9199f14e62:0.1294  
  
r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294  
  
....  
  
[[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html))  
  
gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782  
  
....  
  
[[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html))  
  
GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020  
  
....  
  
[[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)](https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/))  
  
17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187  
  
....  
  
[[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)](https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/))  
  
H19-C_20260930T212401Z_c11e495e: 0.0297  
  
....  
  
[[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html))  
  
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894  
  
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)](https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/))  
  
h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461  
  
h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921  
  
H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280  
  
h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839  
  
....  
  
[[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)](https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/))  
  
20261001_r13-lattice-s5_v2_nan-outside:0.0904  
  
....  
  
[[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html))  
  
h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855  
  
h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976  
  
h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)](https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/))  
  
h19-4-reference-20260930-691e4dfa: 0.1894  
  
....  
  
[[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html))  
  
h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890  
  
h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan:  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html))  
  
h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002  
  
h23-b-dti-optimal-emission-10pct-20261002-86176698-nan:   
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)](https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/))  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)](https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/))  
  
h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477  
  
....  
  
25GEMSDOE SCORE:  
  
....  
  
26GEMSDOE SCORE:  
  
....  
  
27GEMSDOE SCORE:  
  
....  
  
WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:  
  
24GEMSDOE SCORE:  
  
h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477  
  
Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2477?  
  
Answer the question using Phd level experience, knowledge, and judgement.   
  
The following is the leaderboard for the competition:  
  
[[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/))  
  
   
  
We need to quickly look at the results and results from the GEMSDOE websites above.  
  
Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.  
  
Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above.  We need to come up with distinct and unique strategies to score higher in this competition leaderboard.  We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents.  We should store all of our information and knowledge that we can gather from official verified sources.  This will serve as a starting point for other projects as well.  We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for.  So it's important to be contrarian but be smart about it.  We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents.  We need to do deep research and critical thinking and come up with new hypothesis to test.  
  
The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.  
  
   
  
[[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html))  
  
gems-submission-20260925T001403Z-7f00890a: 0.1563  
  
....  
  
[[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)](https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/))  
  
gems6_hgb88-topk03_33cec71ff0: 0.0286  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html))  
  
pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193  
  
pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830  
  
pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html))  
  
gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)](https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/))  
  
gems-submission-20260926T163915Z-237f0063: 0.0343  
  
....  
  
[[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html))  
  
gems-submission-20260926T175114Z-7f00890a: 0.1563  
  
....  
  
[[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)](https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/))  
  
lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461  
  
....  
  
[[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)](https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/))  
  
Hedge-v2_submission: 0.1563  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html))  
  
2314b599: 0.0107  
  
....  
  
[[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html))  
  
gems-structural-area06-v1: 0.0202  
  
....  
  
[[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html))  
  
r7-nms3-dem10-scarp_0c9199f14e62:0.1294  
  
r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294  
  
....  
  
[[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html))  
  
gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782  
  
....  
  
[[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html))  
  
GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020  
  
....  
  
[[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)](https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/))  
  
17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187  
  
....  
  
[[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)](https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/))  
  
H19-C_20260930T212401Z_c11e495e: 0.0297  
  
....  
  
[[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html))  
  
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894  
  
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)](https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/))  
  
h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461  
  
h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921  
  
H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280  
  
h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839  
  
....  
  
[[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)](https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/))  
  
20261001_r13-lattice-s5_v2_nan-outside:0.0904  
  
....  
  
[[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html))  
  
h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855  
  
h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976  
  
h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)](https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/))  
  
h19-4-reference-20260930-691e4dfa: 0.1894  
  
....  
  
[[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html))  
  
h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890  
  
h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan:  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html))  
  
h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002  
  
h23-b-dti-optimal-emission-10pct-20261002-86176698-nan:   
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)](https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/))  
  
....  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)](https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/))  
  
h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477  
  
....  
  
25GEMSDOE SCORE:  
  
....  
  
26GEMSDOE SCORE:  
  
....  
  
27GEMSDOE SCORE:  
  
....  
    
  
WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:  
  
24GEMSDOE SCORE:  
  
h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477  
  
Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2477?  
  
Answer the question using Phd level experience, knowledge, and judgement.   
  
The following is the leaderboard for the competition:  
  
[[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/))  
  
0.3195	is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website.  It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.    
  
Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use.  It should solve the problem of having to manually check everything ourselves and having an up to date current feed.  
  
Review the repo.   
  
The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.  
  
Our Core Values  
  
Maximize P(Win)  
  
“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.  
  
Own the Outcome  
  
We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.  
  
Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
    
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
We need to focus on being able to generate a submission into the competition.    
  
The site should be able to generate a TIF file that is required for submission.  It should be as easy as download to click a File to submit into the competition.  This needs to be in the executive summary or the very beginning of the site.  it should be obvious when you visit the site.  
  
I tried to submit the document that i downloaded from the site but it returned this error on the submission form:  
  
"Predicted values must be in range [0, 1]"  
  
Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25  
  
Here is the submission page when i click submit file  
  
New submission  
  
File to submitNo file chosen  
  
You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.  
  
Note (optional)  
  
A short comment to help you or your team tell submissions apart later e.g. clustering with k=25  
  
Create a executive summary subpage that explains exactly how to make a submission into the contest.  
  
Work on the next steps from the previous sessions first.  
  
The goal of this project is to place top of the leaderboard in this competition.  The following is the competition:  
  
[[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/))  
  
We need to create a project that can compete and place top of the leaderboard.  We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.    
  
This is the guidelines we need to follow.[[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)](https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/))  
  
Get familiar with the problem through the overview and problem description,[[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). You might also want to reference additional resources available on the about page,[[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)).  
  
Download the data from the data,[[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)), tab.    
  
Create and train your own model. This reference solution,[[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)](https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)) implements a simple approach.  
  
Use your model to generate predictions that match the submission format.  
  
Tell me what are you limitations and what you need access to during this project.  We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.    
  
this pdf outlines how submissions must be entered into the competition.    
  
[[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)](https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf))  
  
You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information.  this must be done autonomously and must be constantly reviewed and improved upon.  Provide suggestions and improvements and implement them.  
  
❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)) (verified redirect to login)  
  
See below for links from the above site.  See attached files for links from the above site.  
  
[[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)](https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391))  
  
Download competition data from [[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)) (requires login) to data/  
  
See links below for competition data:  
  
[[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;amp;st=wz4kofki&amp;amp;dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;st=wz4kofki&amp;dl=0)](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;st=wz4kofki&amp;dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0))  
  
[[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;amp;st=8junzdyw&amp;amp;dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;st=8junzdyw&amp;dl=0)](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;st=8junzdyw&amp;dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0))  
  
[[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;amp;st=rnino7ya&amp;amp;dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;st=rnino7ya&amp;dl=0)](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;st=rnino7ya&amp;dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0))  
  
[[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;amp;st=zj1lag1r&amp;amp;dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;st=zj1lag1r&amp;dl=0)](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;st=zj1lag1r&amp;dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0))  
  
[[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;amp;st=srhhir10&amp;amp;dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;st=srhhir10&amp;dl=0)](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;st=srhhir10&amp;dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0))  
  
Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
Site creation  
  
Create a github page for this repo that has clean ui, user friendly, simple and easy to use.  It should be organized and clean.    
  
It should include all relevant information in an easy to read format with official verified links as sources for review.  Work line by line verify everything no hallucinations.  
  
**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).  
  
you need to complete the above task by yourself.  Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
Run this task through multiple passes.  
  
Pass 1: Implement the task completely and verify the result.  
  
Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.  
  
Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.  
  
Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request.  Work line by line verify everything no hallucinations.  
  
Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.

````

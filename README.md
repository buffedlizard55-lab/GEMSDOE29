# GEMSDOE29 — an auditable GEMS Prize research lab

**Mission:** develop and document a defensible fault-prediction workflow for the U.S. DOE Geologic Enhanced Mapping System (GEMS) Prize. The objective is to maximize the probability of winning through real, independently checkable scientific leverage—not leaderboard theater—and to **own the outcome** by reporting blockers, negative results, uncertainty, data provenance and exact file checks.

> **Session 5 (2026-10-03): the standing data blocker is cleared, and its first experiment is a decisive
> negative.** `bash scripts/download_competition_data.sh --group all` restored and hash-verified **22/22 manifest
> entries** (11 in `data/manifest.json` + 11 in `registry/data_manifest.json` — 14 distinct files, six of
> them pinned in both layouts) into the ignored `data/` tree; `python scripts/prepare_data.py` built the aligned
> arrays (footprint 5,167,373 px, labels 60,988 px, 19 bands, 54.6 s); `build_features.py` / `build_addons.py`
> produced the 64-column static block and the 5 add-on columns; and a new
> [`scripts/verify_pipeline.py --reproduce`](scripts/verify_pipeline.py) wrote
> [`evidence/pipeline_verification.json`](evidence/pipeline_verification.json): both manifests verify, the
> template grid matches, the caches are complete, and the registered candidate **rebuilds byte-identically**
> (`sha256 3537e9fc47a46503…`, 1,591,482 bytes, 37,913 dots, `ok_to_upload=true`). The full
> train → inference → validate path therefore runs here, end to end, on the pinned bytes. The session then spent
> that capability on the gap `knowledge/22` §4 left open: the H41 union arm was **re-scored on the H34 C0
> protocol** whose `C1_geodesic_dots` control is the recorded slot bar (0.14479018). Under a new frozen
> preregistration ([`knowledge/27`](knowledge/27_preregistered_h41a4_h34protocol_2026-10-03.md), sha256
> `af1d8188…`, committed before the run) the arm measured **0.14597316** with a mean paired gain of only
> **+0.001183** against the frozen **+0.005** bar (worst fold −0.009202; 3/4 folds positive), and the SGMC second
> proxy **lost on all four folds** (−0.007180). The two frozen controls reproduced the stored session-2 H34 cells
> **bit-for-bit** (max |Δ| = 0.0), so the comparison is not an environment artifact: H41's earlier +0.0073/+0.0077
> means were **draw-specific**, the family's line is **closed for promotion**, no candidate file was built and no
> weekly slot was used. Every number is recomputed from the raw cells by
> [`scripts/analyze_h41a4_h34protocol.py`](scripts/analyze_h41a4_h34protocol.py) (problems: none); the write-up is
> [`knowledge/28_h41a4_results_2026-10-03.md`](knowledge/28_h41a4_results_2026-10-03.md). Nothing is slot-approved,
> and that stage consumed no draws: the next free draw was still 32 when it finished (the parallel H43 stage then
> claimed 32/33 and reserved 34/35 — [`registry/draw_ledger.json`](registry/draw_ledger.json) is the only
> authority — see the draw-ledger bullet further down). Pass 2 closed two process defects it found: the
> documented download verifier covered only two of the five registered artifacts
> ([`IR-29-VERIFY-DOWNLOADS-COVERAGE`](registry/irregularities.json), now **5/5 ok** plus the two H29 builds at
> 28 checks each with 0 failures) and one register mitigation named a script that does not exist in this
> repository (`IR-29-REGISTER-STALE-SCRIPT`). The executive-summary page now explains the historical
> `[0, 1]` rejection from the register itself, with the honest caveat that the portal validator is not public.
> Remaining work and limitations: [`knowledge/29`](knowledge/29_remaining_work_and_limitations_2026-10-03.md).
>
> **Session 5, parallel workstream (2026-10-03): the published headline candidate was a distance-to-catalogue
> look-up, and the fix is a cross-fitted builder — but fixing it did not change any verdict.** Building an
> `A4_h41_union` artifact with the existing recipe produced a file **byte-identical** to the published repo-c0
> candidate (sha256 `3537e9fc47a46503…`, content id `a4d439b07426`), i.e. the H41 physics changed nothing. The
> cause is measured, not guessed: `scripts/build_repo_candidate.py` builds catalogue family `E` from the same
> full catalogue its positives come from, and `E`'s first column `log1p(min(dist_to_catalogue, 60))` is
> **exactly 0.0 on all 60,988 positives** and **≥ 1.098612 on all 300,000 sampled negatives** — train AUC
> **1.0**, tree-1 root split `E_dist` at threshold `0.0`, and only **2 distinct columns used across all 100
> trees** (`E_dist` 100 splits, `mag_anom` 200). Independent corroboration: that artifact placed **65.95 %** of
> its dots within 300 m of the known catalogue. The screens in `evidence/` are **unaffected** — `Cell` builds
> `E` from `draw.visible`, which has the hidden components removed. The fix,
> `scripts/build_crossfit_candidate.py`, trains per (fold, draw) exactly as the validated cells do (features
> from `draw.visible`, positives = `draw.hidden_train`, negatives ≤300 k at >1.5 px, seed `777+31·fold+draw`),
> applies the models to the whole footprint with `E` from the full catalogue (legitimate at prediction time),
> averages over 4 folds × draws 30/31, and runs the unchanged frozen emission. It now uses **78–86 columns per
> cell with 1,207 H41 splits**, catalogue-hugging falls to **≈15 %**, and the two arms are distinct: `C0_base`
> 33,766 dots (`ca879db0089a`) and `A4_h41_union` 33,739 dots (`9edb34b99e3a`). It **aborts** if no split lands
> on an H41 column or if the arms come out identical — the guard the old path lacked. **The honest bottom
> line:** the leak-free A4 artifact is still **not** slot-recommended. Re-scored on the H34 slot-bar protocol it
> reaches **0.14597 against a bar of 0.16402** (worst fold −0.00920, SGMC positive on 0/4 folds) and G3
> withholds promotion; its own-fold +0.0073/+0.0077 gains were measured against `C0_base`, not against the best
> control. Fixing the leak changed the artifact, not the verdict. Separately, the owner's reported
> `Predicted values must be in range [0, 1]` rejection is reproduced exactly: `((a>=0)&(a<=1)).all()` over the
> **whole** array is **False** for every `-nan.tif` and **True** for every `-zeros.tif`, so both variants ship
> and the zero-outside file is the recommended format. All four new files have **zero hard-check failures**.
> Registered [`IR-29-ARTIFACT-LEAK`](registry/irregularities.json); full write-up and the disclosed narrowing of
> one test assertion: [`knowledge/33`](knowledge/33_artifact_leakage_and_crossfit_2026-10-03.md).
>
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

- **[Why D2.8 leads and what beating 0.3195 takes (read first)](knowledge/34_d28_why_it_won_and_path_past_03195_2026-10-03.md)** — the owner-reported D2.8 lead is emission-redundancy removal (73 % of the parent's kernel credit at 36 % of its pixels; the H28-conditional optimum of its own family), the brief's worming paragraph is already implemented in four failed formulations (H29/H31/H31b/H40 — closed, not retried), and the ~+0.06 gap to the reported #1 needs new habitat mass no validated estimate yet provides. Strategy: calibrate proxies on the owner's own files, screen v5 habitat on fresh draws, build at most one cross-fitted artifact.
- **[Candidate slate v5](knowledge/35_candidates_v5_2026-10-03.md)** — four grep-verified-new hypotheses (H50 range-front segmentation ranked first, H49 alteration corridors, H51 cross-family agreement, H48 vent/paleo alignments) with layers / signature / why-off-catalogue / difference-from-repo / obtainability each, plus the frozen H50 validation plan on draws 36/37 — queued, not run, no slot until it beats 0.14479.
- **[Session-6 audit record](knowledge/36_session6_review_intake_2026-10-03.md)** — one-click TIF + `[0,1]` fix re-verified in this checkout (7/7 downloads pass), prompt disposition table, the H43 register defect (`IR-29-H43-REGISTRY-STALE`, fixed), remaining work, three-pass log.
- **[H43 results](knowledge/30_h43_drainage_results_2026-10-03.md)** — the drainage-network screen on
  draws 32/33 (40 cells): `A3_knick` **+0.01419** and `A4_union` **+0.01287** pass the frozen G1 gate with the
  emission budget in band and the worst fold ≈ −0.001, while `A1_off` (+0.00401) and `A2_network` (−0.00136) fail —
  so the signal is the **knickpoint residual**, not drainage density. The SGMC second proxy is negative on both
  passing arms, the staged execution and the design-file rewrite are disclosed in §1, and the preregistered
  confirmation on draws 34/35 **replicated both arms more strongly** (+0.01674 / +0.01568, 3/4 positive folds per
  draw, worst folds 0.0 / −0.00053) — then the inherited G3 secondary-proxy rule vetoed promotion, exactly as for
  H41, because the SGMC class is negative in both stages (2/4 → 0/4 and 1/4 → 2/4 folds). H43 closes with no
  candidate and no slot; its frozen protocol is
  **[knowledge/29](knowledge/29_preregistered_h43_screen_2026-10-03.md)**.
- **[Session-5 note](knowledge/31_session5_data_and_emission_2026-10-03.md)** — the data-placement receipt (the
  standing blocker, closed), the emission-density sweep (negative: keep the pinned artifact) and the H43 execution
  record, with every re-check command.
- **[Proxy-policy review (session 5, decision requested)](knowledge/32_proxy_policy_review_2026-10-03.md)** —
  recomputed from every archived raw cell: **0 of the 5 arm-stages that ever cleared a primary promotion gate
  had a positive SGMC sign**, and only the primary proxy has an external anchor (+1.0 vs the SGMC proxy's −0.5
  on the same three unverified owner-reported points). Registered as `IR-29-PROXY-VETO-PATTERN` with three
  options for the owner; **no label or gate was changed**. Evidence:
  [`evidence/proxy_agreement_review.json`](evidence/proxy_agreement_review.json).
- **[H43b results — Workstream B & head-to-head comparison](knowledge/37_h43b_mass_conserving_drainage_results_2026-10-03.md)** —
  parallel Session-5 implementation (`src/gemsdoe/h43b.py`, frozen in
  **[knowledge/27b](knowledge/27b_preregistered_h43b_screen_2026-10-03.md)**, `evidence/h43b_screen/`) that seeds
  Barnes–Lehman–Mulla priority-flood at the true footprint boundary (`17,865` outlets, `876,389` raised cells,
  `0` trapped interior cells, `100 %` mass conservation across `5,167,373` pixels, `max_acc_px = 824,820` vs `109`
  in Workstream A), fits `108` per-basin repeated-median log–log $S\text{–}A$ envelopes, and separates
  `A3_h43_scarp_free` (without `H43_CHANNEL_SCARP`) from `A4_h43_union`. On the same draws `32/33` (`40` cells in a
  single uninterrupted process, `analyzer_report.json` `integrity_problems: []`), `A4_h43_union` gained **`+0.0039976`**
  and was positive in **all 4 quadrant fold means** (`NW +0.00387, NE +0.00350, SW +0.00642, SE +0.00220`, worst
  fold `+0.0021960`, `0.00100` short of G1's `+0.005` bar), while `A3_h43_scarp_free` (`+0.0019365` primary)
  **passed the SGMC $\ge 3/4$ positive-folds gate (`+0.0013560`, 3/4 folds)**, isolating `H43_CHANNEL_SCARP` as the
  column that trades SGMC score for primary range-front score.
- **[Artifact leakage and the cross-fitted fix (session 5, parallel workstream)](knowledge/33_artifact_leakage_and_crossfit_2026-10-03.md)** —
  the measured defect in the single-fit artifact path (`E_dist` separates the training labels perfectly, 2 distinct
  columns used out of 81), why the screens are unaffected, the cross-fitted protocol, the `-nan` vs `-zeros`
  answer to the `Predicted values must be in range [0, 1]` rejection, and the disclosed narrowing of one test
  assertion (§7). Registered `IR-29-ARTIFACT-LEAK`.
- **[H41-A4 vs the slot bar (session 5)](knowledge/28_h41a4_results_2026-10-03.md)** — the frozen re-score on the
  draws that define the bar, the bit-for-bit control reproduction that validates the comparison, and why the
  family's promotion path is now closed. Frozen protocol:
  **[knowledge/27](knowledge/27_preregistered_h41a4_h34protocol_2026-10-03.md)**.
- **[Data/pipeline receipt](evidence/pipeline_verification.json)** — 22/22 manifest entries hash-verified, caches
  complete, candidate rebuilt byte-identically (`scripts/verify_pipeline.py --reproduce`).
- **[Remaining work and limitations (session 5)](knowledge/29_remaining_work_and_limitations_2026-10-03.md)** —
  what the data blocker's clearance changed, the priority list for the next session, the standing limitations, and
  the three-pass record.
- **[H41 results](knowledge/26_h41_results_2026-10-03.md)** — the screen table, why the two passing
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

- **Data blocker cleared and verified (session 5):** 22/22 manifest entries hash-verified in this
  checkout (11 core + 11 H31-group), aligned caches built, template grid checked, and the registered candidate
  rebuilt byte-identically — the receipt is [`evidence/pipeline_verification.json`](evidence/pipeline_verification.json),
  produced by [`scripts/verify_pipeline.py`](scripts/verify_pipeline.py) (`--reproduce` re-runs the build). Session 5
  also wrote its own placement receipt ([`evidence/data_placement_receipt.json`](evidence/data_placement_receipt.json),
  re-checkable with `python scripts/record_data_placement.py --check`). The inputs remain hash-pinned owner mirrors,
  not organizer-authenticated bytes (`IR-DATA-01`); `data/` is ignored by Git.
- **H41-A4 vs the slot bar (session 5):** frozen preregistration
  [`knowledge/27`](knowledge/27_preregistered_h41a4_h34protocol_2026-10-03.md), 24 cells on the spent draws 20/21,
  `A4_h41_union` 0.14597316 with mean paired gain **+0.001183** (bar +0.005) and SGMC **−0.007180 (0/4 folds)**;
  the frozen controls reproduced the stored H34 cells **exactly** (max |Δ| = 0.0). Verdict: **no promotion, no
  candidate built, no slot** — [`knowledge/28`](knowledge/28_h41a4_results_2026-10-03.md),
  [`evidence/h41a4_h34protocol/`](evidence/h41a4_h34protocol/).
- **Next free draw is 36** — `registry/draw_ledger.json` is now the only draw ledger, generated from the committed evidence (`scripts/build_draw_ledger.py`, `--check` fails on drift, `tests/test_draw_ledger.py` pins it). Draws 32/33 were fitted by the H43 screen and 34/35 by its completed confirmation (both recorded in the ledger, which now also marks `h43_confirmation` COMPLETE); the next free pair is 36. The older prose lists in `knowledge/08` and this README are history, not authority: they are the records that drifted in session 3 (draws 24/25 double-claimed), and 26/27 plus 2/3 count as spent because they were authorized under a recorded receipt and never fitted.
- **One download by hand** — the *leaderboard score itself*. The manual link is on the site's leaderboard card and in `knowledge/03`; `scripts/check_site.py` deliberately fails if anything on the site links the score page, and `registry/score_claims.json` keeps every score as a claim until the owner confirms it.
- **H43 (session 5):** drainage-network organization on the cached detrended surface — priority-flood fill → D8
  accumulation → binned-median log-log stream-power fit → knickpoint residual, plus off-catalogue and
  channel/scarp columns (`src/gemsdoe/h43.py`). Frozen at `knowledge/29` (sha256 `919210d9…`), screened on
  draws 32/33 across the four blocked folds and five arms: **`A3_knick` PASS +0.01419** (fold gains
  −0.0010/+0.0195/+0.0153/+0.0229, 3/4 positive folds in both draws, worst fold −0.00095) and
  **`A4_union` PASS +0.01287**; `A1_off` (+0.00401) and `A2_network` (−0.00136) FAIL. Control mean 0.14317,
  passing-arm means 0.15735/0.15603, emissions 7.3–7.5 k dots per cell (budget in band), viability guard passed,
  and `scripts/analyze_h43_screen.py` recomputed every gate from the raw rows with **integrity_problems: 0**.
  The **SGMC second proxy is negative on both passing arms** (A3 −0.00012 on 2/4 folds, A4 −0.00190 on 1/4) — the
  same proxy conflict that vetoed H41 — so this is a screen pass, not a promotion. The first launch was OOM-killed
  at 23/40 rows and its partial stage is quarantined under `evidence/history/h43_screen_oom_partial_2026-10-03/`;
  the completed stage ran as four verified process episodes, and the design-file rewrite that happened before the
  keep-design guard existed is disclosed with the exact evidence in `knowledge/30` §1
  (`IR-29-H43-DESIGN-REWRITE`, `IR-29-H43-STAGED-EXECUTION`). Raw cells: [`evidence/h43_screen/`](evidence/h43_screen/).
  The preregistered confirmation on draws 34/35 was launched from a clean tree at `bd6811e` and completed 40/40 cells:
  both arms replicated more strongly (A3 +0.01674, A4 +0.01568; 3/4 positive folds per draw; worst folds 0.0 and
  −0.000533; budgets in band; analyzer `integrity_problems: 0`, screen section bit-identical to the pre-confirmation
  report), and the inherited G3 rule then withheld promotion because the SGMC second proxy is negative in both stages
  — the second independent family (after H41) with the replicated-primary/secondary-proxy-loss signature.
  **No H43 candidate exists, no file is slot-approved, and no weekly slot has been used.**
- **Data placement (session 5):** the original brief's blocker — "run the data download script and prepare the
  data" — is closed locally with a re-checkable receipt. `bash scripts/download_competition_data.sh` restored the
  hash-pinned owner mirrors, `python scripts/prepare_data.py` rebuilt the footprint/label/band caches (5,167,373
  footprint pixels, 60,988 catalogue pixels, 19 bands), and `python scripts/record_data_placement.py` wrote
  `evidence/data_placement_receipt.json`: 22/22 pinned manifest entries byte-correct (11/11 H31 group, 11/11 core),
  `problems: []`, **`organizer_authenticated: false`** (owner mirrors, not organizer bytes — `IR-DATA-01`).
  `--check` re-verifies without rewriting. See `knowledge/31` §2.
- **Emission density (session 5):** the frozen sweep (`knowledge/27`) returned a **negative**: on a proxy that
  reproduces the reported ladder order (solid 0.06970 < d1.5 0.09449 < d2.8 0.09832), the pinned 2.8-px artifact is
  the **maximum** of its family — every denser row loses 0.0038–0.0286 and every sparser row 0.0028–0.0267, the
  score-aware placement variant loses 0.0043, and the rule returns `admissible: []` with "keep the pinned artifact"
  (`knowledge/28`, `evidence/emission_sweep/`). Two side findings are registered: the spacing parameter is
  quantised by an integer disc (`IR-29-SPACING-QUANTISATION`) and the repository-candidate file scores 0.327 on the
  file-level proxy purely from training leakage, which is why the sweep never ranks model-derived artifacts.
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
python scripts/record_data_placement.py --check   # re-verify the session-5 data placement receipt (no rewrite)
python scripts/build_draw_ledger.py --check   # which holdout draws are already spent (next free: 36)
python scripts/build_site.py
python scripts/check_site.py
python scripts/verify_downloads.py            # re-verify every registered download (never its build hashes)
python scripts/verify_pipeline.py --reproduce # hash-verify the restored inputs + rebuild the candidate (~2 min)
```

**One command, both layouts:** `bash scripts/download_competition_data.sh` added on 2026-10-03 as the
entry point the original prompt asked for ("run `bash scripts/download_competition_data.sh` … into `data/`").
It does **not** contact DrivenData (that is prohibited by `AGENTS.md` rule 3); it wraps the two hash-pinned
owner-mirror restorers, defaults to the H31-group set that the current screens and caches expect, accepts
`--group core|h31|all` and `--verify`, and ends by printing which template path the local checker will use.
A review pass on 2026-10-03 corrected its final resolver probe from the retired `gems29.paths` package to the
active `gemsdoe.paths` package; this was checked with shell syntax validation and a regression test, but no
restore is claimed in this sandbox because competition authentication/data access is unavailable.
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

## Session 6 intake — preserved working note (2026-10-03)

The session-6 brief restates the standing brief (worming-as-filter, one-click TIF + note, executive
summary, `[0, 1]` fix, why-D2.8/beat-0.3195 analysis, 3–5 new ranked hypotheses with obtainability,
holdout validation before any slot, prompt-in-README, three passes, PR + merge). It is not pasted in
full a third time; the standing transcription and the session-3 verbatim brief below remain the
authoritative texts (both preserved byte-identically — the owner-brief block is pinned by
`tests/test_project_integrity.py::test_full_owner_brief_is_preserved_in_readme`). Session 6's new
deliverables: **[knowledge/34](knowledge/34_d28_why_it_won_and_path_past_03195_2026-10-03.md)**
(why the owner-reported D2.8 leads, the 4×-negative worming disposition, the path past 0.3195),
**[knowledge/35](knowledge/35_candidates_v5_2026-10-03.md)** (v5 slate: H50/H49/H51/H48 ranked, with
the frozen H50 validation plan on draws 36/37), and
**[knowledge/36](knowledge/36_session6_review_intake_2026-10-03.md)** (audit record, three-pass log,
remaining work). Register changes: H43 status corrected (`IR-29-H43-REGISTRY-STALE`), v5 slate filed
(`registry/hypotheses_v5_2026-10-03.json`), status-feed event appended. No experiment ran, no slot
was used, nothing is slot-approved.

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

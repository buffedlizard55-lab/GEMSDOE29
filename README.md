# GEMSDOE29 — DOE GEMS Prize (#306): multiscale worming lab & submission site

> **Read this entire README, including the verbatim Project Charter below, at the start of every session.**
> The site renders every number from this repo's own JSON evidence; nothing on the pages is hand-typed.
> **Live site:** https://buffedlizard55-lab.github.io/GEMSDOE29/ — first screen: one-click submission TIF + note to paste.

## Core Values (verbatim, from Arena team — the focal point of every build, research, suggestion and implementation decision)

> **Maximize P(Win)** — "Maximize the Probability of Winning": our decision making framework. In every decision,
> we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set
> aside our emotions and make tough decisions in order to maximize P(Win). "Maximize P(Win)" frees us from
> constraints and clarifies that we must put Arena first.
>
> **Own the Outcome** — We own results end to end — not just our individual slice of the work. When problems arise
> and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success
> as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Standing working rules (owner): *Work line by line verifying from official verified trusted sources, provide links
for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for
review. No hallucinations. Run every task through three passes (implement+verify; bug/edge review; full recheck
against the original request). Create a pull request and merge it.*

## Status — 2026-10-03 (this session)

* **Repo review finding (IR-29-EMPTY-REPO, critical):** `GEMSDOE29` began as a single commit containing
  `# GEMSDOE29` — no pipeline/site existed despite the inherited prompt assuming one. Everything below was
  rebuilt this session from the verified sibling lineage (GEMSDOE, 19, 24, 25, 26, 27 cloned read-only).
* **Data blocker resolved:** the "place competition data in `data/`" task is DONE here — `training_features.tif`
  (418,912,844 B) reassembled from 5 hash-verified parts, sha256 `4371c82e…bc5` **byte-exact** vs the pin,
  plus labels/template/parent rasters/LiDAR/GeoDAWN extensions/2 m probe archive, all pinned in
  `data/manifest.json` (`python3 scripts/restore_data.py` → `ALL VERIFIED`). They remain **owner mirrors, not
  organizer-authenticated** (IR-29-SIBLING-LINEAGE).
* **The science asked for is implemented:** Fourier upward-continuation worming (Hornby/Boschetti/Horowitz 1999
  ladder 0–1600 m on `rtp` + `iso_grav_anom`, worm tracking, persistence rasters, acquisition-line audit) in
  `src/gems29/worming.py`; operator cross-checked against the official contractor `TMI_up150` grid (Spearman
  0.878) and unit-tested against the analytic dike depth-shift identity; screened under a frozen gate
  (`knowledge/01_preregistration_h29_worming_2026-10-03.md`).
* **Key measured facts on the real grid** (`evidence/worming_receipt.json`): 51.0 % of gravity level-0 edges and
  17.8 % of magnetic ones exist at zero continuation only (the distrust population, now a number); E–W-striking
  edges are *more* persistent than N–S (0.656 vs 0.562) → the naive line-aliasing filter is refuted on this grid
  (IR-29-LINE-PERSISTENCE-INVERSION); only ≈2.7 % of the live-scored 44,090-px emission dots sit on p95 edges
  (IR-29-PARENT-OFF-EDGES) → worming enters as re-ranking/features, not as a hard gate.
* **Why 0.2600 scored 0.2600:** not a better detector — the H19-5 solid (0.1922) thinned by Poisson-disk 2.8 px
  to 44,090 dots; overlapping credit kernels waste pixels under the metric's max-within-300 m / sum-FP structure.
  This repo reproduces the d1.5 (0.2477) mask bit-for-bit and the d2.8 44,090-px count exactly
  (`tests/test_sibling_reproduction.py`). The geometry lever is exhausted at ≈0.255–0.260 (GEMSDOE27 live
  inversion); beating public-#1 0.3195 (DARD, 12 subs; read from the leaderboard 2026-10-03, public column)
  requires detector concentration > 5.7× blind. See `registry/live_scores.json`.
* **Frozen gate verdict (2026-10-03):** all four arms FAIL the pre-registered +0.005 sparse-proxy bar —
  A1 gate −0.0001/−0.0001, A2 rank −0.0010/+0.0002, B1 worm-features +0.0004/+0.0004, B2 thermal-features
  +0.0005/+0.0012 (4/4 folds one draw; still 1/4 of margin). No slot recommended, none spent; the two
  shipped TIFs carry their status on the download card. Full write-up: `knowledge/02_h29_results_2026-10-03.md`.
* **Answer to "can we beat 0.26 / 0.3195?":** not by re-arranging this surface (exhausted ≈0.255–0.260,
  independently re-verified here); beating 0.3195 requires detector concentration > 5.7× blind. This session
  proved worming-persistence and probe-residuals in their SIMPLE forms are not that jump — and registered the
  sharper versions (notch, corridors, soft prior, GPU U-Net) for the next sessions.

## How to use the site / submit (also at `docs/executive-summary.html`)

1. Home page → big download button (`gems29-…-nan.tif`, plus `.zip` and `-zeros.tif` fallbacks).
2. DrivenData → *My Submissions* → attach file → paste the unique name + Note shown on the site (≤200 chars).
3. The writer + `scripts/verify_downloads.py` guarantee: single-band float32, EPSG:32611, 3730×3292, 100 m,
   exact template geotransform, **every in-footprint pixel finite and in [0,1]**, NaN outside — the specific
   class of error ("Predicted values must be in range [0, 1]") that killed a past upload is engineered away
   (root cause + defenses: IR-29-PREV-SUBMIT-ERROR-CLASS).

## Quickstart (repo)

```bash
pip install -r requirements.txt
python3 scripts/restore_data.py            # hash-pinned mirror restore + verification
python3 -m pytest -q tests/                # 15+ tests incl. metric brute-force & physics anchors
python3 scripts/run_worming.py             # upward-continuation ladder + audits (~1 min, CPU)
python3 scripts/run_holdout_screen.py      # frozen gate screen (~1 h CPU, 4 folds × draws)
python3 scripts/build_candidate.py         # packages format-verified TIF(s) into docs/downloads
python3 scripts/verify_downloads.py        # independent site-download audit
python3 scripts/build_site.py              # regenerates index.html + docs/*.html from JSON evidence
```

No GPU here: the reference-solution U-Net arm (torch) remains a next-session task on GPU hardware
(`requirements-train.txt` style env per GEMSDOE4/5 notes). Never automate drivendata.org (ToS) — the owner
submits manually through the portal using the note text above.

## Layout

```
src/gems29/   worming (UC ladder, tracking, audits), metric (DTI), thinning (Poisson-disk + ranked),
              holdout (quadrant hide-and-recover), features, head, emission arms, submission writer, thermal
scripts/      restore_data · run_worming · run_holdout_screen · build_candidate · verify_downloads · build_site
knowledge/    01 preregistration (frozen gates) · 02 results write-up
registry/     live_scores · sources · irregularities · hypotheses_h29 · artifact_ledger
evidence/     worming_receipt.json · h29_holdout.json · h29_gate.json · screen logs
docs/         executive-summary.html · research.html · sources.html · downloads/ (shipped TIFs + checks)
index.html    Pages root (repo root per GEMSDOE25 IR-25-PAGES-ROOT lesson)
```

## Limitations (carried + new; full list in `registry/irregularities.json`)

1. Mirrors not organizer-authenticated; live scores owner-reported; public leaderboard column ≠ private round score.
2. The catalogue-internal proxy cannot see far-field habitat (100 % of its truth at catalogue distance 0); proxy
   passes are eligibility, never evidence of live gain; the site says so on the same card as the download button.
3. gdr.openei.org unreachable from the sandbox: paleo-geothermal + Q-volcanics layers stay BLOCKED (pins recorded).
4. 2 CPU / 4 GB: boosted-tree heads only; no deep-model training; 100 m rasters only (no raw 1 m DEM reprocessing).
5. Worming persistence uses a relative p95 edge threshold and a heuristic drift tolerance (documented in
   knowledge/01 §3) — it is a reliability *weight*, not a validated depth inversion (Horowitz 2018's own caveat).

## Next steps (queued for the following sessions, in priority order)

1. Read `evidence/h29_gate.json` outcome into knowledge/02 + README line; if A2 pass → owner may spend one of
   the 3 weekly slots on the WORMRANK file with the site's Note text; if fail → record, do not spend.
2. H29-3 spectral line-notch experiment (registered, own frozen gate) — the refuted naive filter's stronger sibling.
3. H29-5 strain-×-persistence corridors (microseismicity + dilatation along persistent basement edges).
4. On a networked runner: fetch paleo-geothermal + Q-volcanics against the pins; then H29-4.
5. GPU session: reference-solution U-Net trained with the DTI-aligned loss on the now-local data (mirror the
   drivendataorg reference repo, pinned), sliding-window + TTA, blended with h19-5 as prior surface — the only
   lever class with room above 0.30 in the concentration arithmetic.
6. Consider `soft persistence prior` (continuous S-decay field instead of quantized P) as H29-1b if A2 repeats
   positive on fresh draws — pre-register before running.

## Project Charter (verbatim owner prompt — re-read every session)

Review the repo.

There should be an easy to download submission tif file as described by the prompt. Read the entire prompt.

Multiscale "worming" to separate deep structure from shallow noise. A single-scale gradient map can't distinguish a genuinely deep-rooted fault from a shallow artifact — cultural noise, a thin near-surface conductor, acquisition-line aliasing — because both can produce a sharp edge at one scale. Hornby, Boschetti, and Horowitz's multiscale wavelet edge-detection method (1999), known informally in exploration geophysics as "worming," computes edges across a sequence of upward-continued versions of the same grid and tracks which ones persist as the field is progressively smoothed toward deeper equivalent sources; an edge surviving several continuation steps is associated with a genuinely deep source, one that vanishes immediately is almost certainly shallow. Compute this across the magnetic and gravity layers and use persistence-with-height as an explicit feature or filter, rather than treating a fixed-scale gradient as if it carries no information about its own reliability — a candidate that only exists at zero continuation is exactly what the acquisition-artifact audit should already distrust, and this gives that distrust a number instead of a hunch.

Here are the results from submissions into the competition, separated by ....:

[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html] gems-submission-20260925T001403Z-7f00890a: 0.1563

[https://buffedlizard55-lab.github.io/6GEMSDOE/] gems6_hgb88-topk03_33cec71ff0: 0.0286

[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html] pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193 · pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830 · pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152

[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html] gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560

[https://buffedlizard55-lab.github.io/GEMSDOE4/] gems-submission-20260926T163915Z-237f0063: 0.0343

[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html] gems-submission-20260926T175114Z-7f00890a: 0.1563

[https://buffedlizard55-lab.github.io/7GEMSDOE/] lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461

[https://buffedlizard55-lab.github.io/8GEMSDOE/] Hedge-v2_submission: 0.1563

[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html] 2314b599: 0.0107

[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html] gems-structural-area06-v1: 0.0202

[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html] r7-nms3-dem10-scarp_0c9199f14e62: 0.1294 · r7-nms3-dem10-scarp_0c9199f14e62_allfinite: 0.1294

[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html] gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782

[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html] GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020

[https://buffedlizard55-lab.github.io/17GEMSDOE/] 17GEMSDOE_F-ensemble-2pct_20260930T050626Z: 0.0187

[https://buffedlizard55-lab.github.io/18GEMSDOE/] H19-C_20260930T212401Z_c11e495e: 0.0297

[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html] h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894 · h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

[https://buffedlizard55-lab.github.io/GEMSDOE10/] h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461 · h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921 · H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280 · h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839

[https://buffedlizard55-lab.github.io/13GEMSDOE/] 20261001_r13-lattice-s5_v2_nan-outside: 0.0904

[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html] h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855 · h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976 · h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360

[https://buffedlizard55-lab.github.io/GEMSDOE21/] h19-4-reference-20260930-691e4dfa: 0.1894

[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html] h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890 · h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859

[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html] h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002 · h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748

[https://buffedlizard55-lab.github.io/GEMSDOE23/] h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352

[https://buffedlizard55-lab.github.io/GEMSDOE24/] h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

[https://buffedlizard55-lab.github.io/GEMSDOE25/] dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

[https://buffedlizard55-lab.github.io/GEMSDOE26/] dilcond-oof-v1-20261003-47629f496133-nan: 0.1223

[https://buffedlizard55-lab.github.io/GEMSDOE27/] topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

28GEMSDOE SCORE: ···· 29GEMSDOE SCORE: ···· 30GEMSDOE SCORE: ···· 31GEMSDOE SCORE: ···· 32GEMSDOE SCORE: ···· 33GEMSDOE SCORE: ····

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING: https://buffedlizard55-lab.github.io/GEMSDOE25/ — dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600. Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.26? Answer the question using PhD level experience, knowledge, and judgement.

Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ — 0.3195 is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website. It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.

Put this prompt into the repo readme and read it every time we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line. We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above. We need to come up with distinct and unique strategies to score higher in this competition leaderboard. We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents. We should store all of our information and knowledge that we can gather from official verified sources. This will serve as a starting point for other projects as well. We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for. So it's important to be contrarian but be smart about it. We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents. We need to do deep research and critical thinking and come up with new hypothesis to test.

The following sites should serve as a starting point for understanding how to generate TIF submissions. These websites are researched, and tested and have generated TIF submissions. But we need to generate high scoring submissions. [site list as above]

Work on the next steps from the previous sessions first. The goal of this project is to place top of the leaderboard in this competition. The competition: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ — understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification. Guidelines: https://www.drivendata.org/competitions/306/competition-doe-gems/ · about/resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/ · data: https://www.drivendata.org/competitions/306/competition-doe-gems/data/ · reference solution: https://github.com/drivendataorg/gems-prize-reference-solution · submission guide PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf (owner mirror: https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf). Competition data mirrors on Dropbox per owner: example_submission.tif, existing_faults.tif, gems-geodawn-numerical-features.tif, Digital-elevation-model-links-JSON.pdf (links retained in data/manifest.json provenance chain). OpenEI: https://gdr.openei.org/submissions/1391.

Tell me what are you limitations and what you need access to during this project. We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data. (Answered in "Limitations" above and on the site; ❌ No DrivenData auth → data via hash-pinned owner mirrors — resolved this session; submission uploads remain owner-only by policy.)

Site creation: Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean. It should include all relevant information in an easy to read format with official verified links as sources for review. Work line by line verify everything no hallucinations.

"The single remaining blocker to training is data placement: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run." — you need to complete the above task by yourself. (Done via `scripts/restore_data.py`, verified; `prepare_data` role fulfilled by the same pinned manifest.)

I tried to submit the document that i downloaded from the site but it returned this error on the submission form: "Predicted values must be in range [0, 1]". Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25. Create a executive summary subpage that explains exactly how to make a submission into the contest. (→ docs/executive-summary.html + IR-29-PREV-SUBMIT-ERROR-CLASS.)

Run this task through multiple passes. Pass 1: Implement the task completely and verify the result. Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find. Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues. Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request. Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project. It should be worked on in this next session or the next session.

## License / citation

Data usage per competition rules (external data allowed with licenses permitting use and sharing with sponsor): USGS/DOI public-domain products (GeoDAWN 10.5066/P93LGLVQ, USGS faults, 3DEP), GDR OpenEI 1391 (CC BY 4.0), INGENIOUS (DOI 10.15121/1881483). Method citation: Hornby, Boschetti & Horowitz (1999), GJI 137(1):175–196, doi:10.1046/j.1365-246X.1999.00793.x.

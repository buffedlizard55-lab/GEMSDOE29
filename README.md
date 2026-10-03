# GEMSDOE29 — DOE GEMS Prize (#306): multiscale worming lab & submission site

> **Read this entire README, including the verbatim Project Charter below, at the start of every session.**
> The site renders every number from this repo's own JSON evidence; nothing on the pages is hand-typed.
> **Live site:** https://buffedlizard55-lab.github.io/GEMSDOE29/ — first screen: one-click, locally format-verified research TIFF + note to paste. The current artifact failed its frozen proxy gate and is **not recommended for submission**.

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

## Status — 2026-10-03 (review continuation)

* **Repository charter preserved:** the original full project prompt remains verbatim below. The working status here is maintained separately so the charter is not silently rewritten.
* **Inputs restored and SHA-256 verified:** the 418,912,844-byte 19-band feature stack was reassembled from five correctly named, individually pinned split blobs; labels, template, parent rasters, LiDAR/GeoDAWN derivatives, the INGENIOUS probe archive, and the owner-mirrored D2.8 TIFF also pass their manifest pins. `python3 scripts/restore_data.py --verify` reports `ALL VERIFIED`. These are pinned **owner mirrors, not organizer-authenticated**; no competition endpoint was contacted.
* **Material implementation corrections:** two independent worming bugs invalidated intermediate screens: the six-level persistence denominator could write `P=1.25`, and `prep_field` replaced its nearest-valid FFT padding with a global median despite the preregistration. The code now preserves nearest-valid fill and uses `last_level_index/(n_levels-1)`, bounded `[0,1]`, with regressions for both. The former holdout-gate aggregator could not see confirmation draws 2/3; the gate and safe staged-run command are tested. All superseded receipts, results and WORMRANK artifacts are hash-archived under `evidence/history/` and `knowledge/history/`, not silently overwritten. The acquisition-line routine remains a strike summary, not a spectral-energy/notch test.
* **Current preregistered worming receipt:** `evidence/worming_receipt.json` reports magnetic/gravity mean persistence 0.485/0.302, level-0-only fractions 17.1%/58.7%, and full-ladder fractions 17.3%/19.1%. Mean magnetic E–W strike persistence (0.540) exceeds N–S (0.447), but strike summaries do not establish whether any edge is a flight-line artifact. The upward-continuation operator has Spearman 0.880 agreement with an owner-mirrored, u8-quantized contractor-labelled `TMI_up150` grid; this is a soft implementation check, not provenance authentication.
* **Current preregistered spatial screen and H29-5:** both screen draws were evaluated over all four quadrants using the corrected nearest-valid padding. H29-5's candidate head scored −0.0789 and −0.0870 mean paired ΔDTI against the best same-fold/draw existing control, with 0/4 positive folds on each draw. H29-5 failed its frozen screen; confirmation draws were therefore not run, exactly as the preregistered compute-saving rule allows. A1/A2/B1/B2 also failed the +0.005 screen bar. All values are catalogue-internal proxy measurements, not live/private leaderboard evidence. **No weekly slot is recommended or spent.** Details: `evidence/h29_holdout.json`, `evidence/h29_gate.json`, and `knowledge/02_h29_results_2026-10-03.md`.
* **Investigation of the reported 0.2600:** the restored GEMSDOE25 D2.8 raster has 44,090 positive pixels. The local deterministic `dot_thin(H19-5, 2.8)` mask matches its pixel mask exactly; GeoTIFF bytes differ. The associated 0.2600 score remains owner-reported: no organizer receipt ties that particular file to the value, although a 0.2600 public-column entry was observed at rank 15. Do not present the mask match as score verification.
* **Download and format checks:** `docs/downloads/` contains the WORMRANK research artifact plus a D2.8 reference reproduction, each with an explicit unique name, short note, NaN/zero variants, single-TIFF ZIP and local read-back receipts. The verifier checks one float32 band, exact pinned-template CRS/dimensions/geotransform, finite `[0,1]` in-footprint values, declared outside convention, ZIP contents and hashes. These local checks reduce the reported range-error risk; they do **not** guarantee portal acceptance, and WORMRANK is **not submission-eligible** under the failed gate.
* **Citation correction:** the prior DOI ending `.00793.x` identifies a different Schlottmann article. The Hornby et al. (1999) publisher record supports DOI [`10.1046/j.1365-246X.1999.00788.x`](https://academic.oup.com/gji/article/137/1/175/700677). The preserved charter below is not altered; the separate License/citation section after the charter is corrected and the erratum is recorded in `knowledge/05_pre_run_implementation_audit_2026-10-03.md`.

## How to use the site / submission steps

1. Open the project home page and download the prominent WORMRANK GeoTIFF (or its ZIP/zero-outside alternative). The displayed note, unique name, hash and check receipt belong to that exact artifact.
2. **Current recommendation: do not spend a weekly slot on WORMRANK.** Its frozen A2 spatial-proxy gate failed. The D2.8 reference is a duplicate reproduction of an already-reported mask, not a new experiment.
3. If a later candidate passes its frozen screen and confirmation gate, the owner may review its evidence and manually upload at DrivenData. No portal submission is automated here.
4. A local-format pass is not a live-validator or score guarantee. Read `docs/executive-summary.html` for the exact portal steps and the source/acceptance caveats.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python scripts/restore_data.py              # restore and hash-check pinned owner mirrors
.venv/bin/python -m pytest -q                           # unit, gate-regression and sibling-mask checks
.venv/bin/python scripts/run_worming.py                 # corrected upward-continuation ladder and receipt
.venv/bin/python scripts/run_holdout_screen.py --screen-only  # 4 folds × 2 preregistered screens
.venv/bin/python scripts/build_candidate.py             # packages locally verified research/reference TIFFs
.venv/bin/python scripts/verify_downloads.py             # independent grid, range, ZIP and hash checks
.venv/bin/python scripts/build_site.py                   # rebuild JSON-driven pages
.venv/bin/python scripts/check_site.py                   # link/fragment/claim-page checks
```

The default and `--screen-only` evaluate screen draws 0/1 across four folds. Run `--confirmation-only` only after saved complete screen evidence contains at least one passing arm; it appends draws 2/3, and exits without fitting if no arm passes. Never access DrivenData programmatically. The official DOE/NLR rules PDF ([link](https://docs.nlr.gov/docs/fy26osti/96647.pdf)) states three automated-scoring submissions per week, private-set scoring, one final submission selected across the prize phases, finalist code/documentation requirements, and generative-AI narrative disclosure.

## Layout

```
src/gems29/   worming, DTI metric, thinning, holdout, feature assembly, gating, submission writer, thermal probes
scripts/      pinned data restore · worming · spatial screen · candidate packaging · download/site validators
knowledge/    frozen preregistration · corrected results · source-verified knowledge · next slate · audit corrections · three-pass recheck
registry/     live-score claims · sources · irregularities · hypothesis slates · artifact ledger
evidence/     corrected receipts/results · preserved pre-correction history
docs/         executive summary · research · sources · locally checked downloads and receipts
index.html    GitHub Pages home page and obvious TIFF download
```

## Limitations and open work

1. Competition inputs are owner mirrors pinned by commit and SHA-256, not authenticated against organizer downloads. Score-to-file associations in the project lineage remain owner-reported unless separately receipted.
2. The spatial holdout uses only catalogue-derived truth and is structurally blind to faults missing from that catalogue; a proxy pass is eligibility evidence only, never a live-score prediction.
3. The free GDR 1391 paleothermal deposit archive is listed under CC BY 4.0, but its direct binary download failed in this sandbox. H29-4 stays blocked until an accessible, licensed and hash-pinned copy is obtained.
4. CPU-only local screen uses histogram gradient boosting and 100 m rasters; the reference U-Net / DTI-aligned deep model remains unimplemented and untested here.
5. Potential-field persistence is an interpretation cue, not a unique depth inversion or fault label; amplitude, source geometry, interference, processing and the relative p95 threshold affect it.
6. H29-5 failed the pre-registered screen; this is not proof the physical mechanism is false. H29-3 spectral notch and H29-6 curvature/junctions remain untested and need their own preregistered gates. No implementation should precede that registration.

## Next research priorities

1. H29-3: measure the predicted cross-line spectral peaks first; only notch if a peak is demonstrated, then rerun persistence under its own frozen gate.
2. H29-6: potential-field Hessian curvature/junction detector at fixed metric scales; compare against the current spatial holdout best.
3. H29-4: retrieve the official GDR 1391 paleothermal archive through an accessible permitted route, pin its hash, then preregister before scoring.
4. Higher-capacity detector (e.g. reference U-Net with DTI-aware loss) only after a reproducible GPU environment and leakage-safe validation plan exist.

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

Data usage per competition rules (external data allowed with licenses permitting use and sharing with sponsor): USGS/DOI public-domain products (GeoDAWN 10.5066/P93LGLVQ, USGS faults, 3DEP), GDR OpenEI 1391 (CC BY 4.0), INGENIOUS (DOI 10.15121/1881483). Method citation: Hornby, Boschetti & Horowitz (1999), GJI 137(1):175–196, DOI 10.1046/j.1365-246X.1999.00788.x (Oxford Academic publisher record).

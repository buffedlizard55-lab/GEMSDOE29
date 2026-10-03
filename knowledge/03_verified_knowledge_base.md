# Verified knowledge base — the science of finding hidden geothermal faults (GEMS #306)

Purpose (owner instruction): "store all of our information and knowledge that we can gather from
official verified sources. This will serve as a starting point for other projects as well."
Every line is either (V) verified by direct read of the linked official source during 2026-10-03
session work in this repo family, (S) sibling-repo-verified (hash-pinned mirrors + prior sessions'
receipts; marked as such), or (C) claim carried from owner-reported text (never silently upgraded).

## 1. The task, from the official pages

- (V) Task: predict "the presence of structures that are indicative of geothermal resources —
  namely, geological faults", as a per-pixel probability grid over the GeoDAWN region.
  Source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (read 2026-10-03).
- (V) Ground truth for scoring = expert-mapped faults NOT in the public USGS database (initial round);
  after the initial round, experts review everyone's submissions and RESCORE against an expanded label
  set (final round). Consequence: predicting genuinely new, verifiable lineaments has final-round option
  value that the public leaderboard does not price. Source: problem page §Competition structure.
- (V) Training labels are "known that this set of faults is not complete and may even contain some
  inaccurate data" — verbatim; catalogue noise is expected, so catalogue-fit metrics saturate.
- (V) Metric (verbatim from problem page): k(d)=(1−d/300 m)+; TPw=Σ_g max_x p(x)k(d); FPw=Σ_{p>0} p(x)(1−max_g k(d));
  FNw=Σ_g (1−max_x p(x)k); DTI=TPw/(TPw+0.2FPw+0.8FNw+eps). α=0.2 β=0.8 → false positives cost 4× less
  than misses: recall-weighted, budget-tolerant metric, which is exactly why max-within-R + sum-FP
  geometry ("dotting") moves scores more than detector polish did for this group.
- (V) Submission format: single-band float32 GeoTIFF, EPSG:32611, 100 m, same bounds, values in [0,1],
  data OUTSIDE bounds "null or nan"; .zip with exactly one GeoTIFF also accepted. Source: problem page
  §Submission format + the live form text quoted in the owner brief.
- (V) End date: Dec. 3, 2026, 11:59 p.m. UTC; prize pool $300k ($50k initial top-5; $250k final
  100/70/40/25/15k). External data encouraged with licenses permitting sponsor use.
  Source: https://www.drivendata.org/competitions/306/competition-doe-gems/ (read 2026-10-03T09:14Z).
- (V) The DOE/NLR official rules PDF (https://docs.nlr.gov/docs/fy26osti/96647.pdf), reviewed in six chunks on 2026-10-03, states three automated-scoring submissions per week, private-set scoring, one final submission selected across prize phases, code/assets/documentation for finalists, and generative-AI disclosure in the narrative.

## 2. The geography and data, from official sources

- (V) The study area is the GeoDAWN NV West-Central 2020 survey: "Geoscience Data Acquisition for
  Western Nevada" — high-resolution airborne magnetic + radiometric (+ gravity context) over the
  Walker Lane transect (UTM 11N grid origin 243350 E, 4508550 N, 3292×3730 px at 100 m → covers
  ≈ 329×373 km, roughly Yerington–Walker Lake–Death Valley junction). Source: problem page +
  ScienceBase item 657e1d85d34e23d3533209f7 (DOI 10.5066/P93LGLVQ).
- (S) Acquisition geometry: 4 blocks, E–W flight lines at 200/400 m spacing, variable terrain clearance —
  GeoDAWN ReadMe; the named cultural/acquisition nuisance for gradient detectors.
- (V) The official 19-band stack (verified by reading the file's own band metadata 2026-10-03):
  mag_anom, rtp, tmi_hg, geod_2ndinv, iso_grav_anom_slope, tc(→radiometric total counts, mislabelled),
  geod_shearrate, geod_dilatationrate, tmi_vg, deq_n100a15, iso_grav_anom_vg, det_elev, iso_grav_anom,
  tmi, depth_to_base_surf, ieq_n100a15, cond_surf, iso_grav_anom_hg, det_elev_slope.
  Bands 4/7/8 are the geodetic strain-rate tensor scalars (GPS/InSAR-derived) — actively deforming
  crust measured by geodesy, independent of visual scarp mapping.
- (S) Labels = USGS Quaternary Fault & Fold Database + INGENIOUS (Great Basin Center for Geothermal
  Energy, DOI 10.15121/1881483); catalogue here has 60,988 positive px on the grid (verified locally).
- (S) GDR submission 1391 (https://gdr.openei.org/submissions/1391, CC BY 4.0) carries the independent
  evidence layers this family uses: springs/wells chemistry (27,092 clipped rows incl. measured
  temp + geothermometer estimates), INGENIOUS 2 m temperature probes (3,800 records; README field
  F2mDAB = "2m temperature normalized to average background" — the official residual), QFaults v2
  traces (1,179 clipped polylines; slip-rate/recency attributes), Great Basin Quaternary volcanics,
  paleo-geothermal sinter/travertine deposits. Two of these (paleo, volcanics polygons) remain
  unfetchable from the sandbox (network block; pins recorded for a networked runner).

## 3. Worming (multiscale upward-continuation edge tracking)

- (V/S) Correct citation: Hornby, P., Boschetti, F., Horowitz, F.G., 1999. “Analysis of potential field data in the wavelet domain.” *Geophysical Journal International* 137(1):175–196, DOI `10.1046/j.1365-246X.1999.00788.x`. Oxford Academic's publisher record supports this identifier. The earlier project DOI `.00793.x` resolves to a different Schlottmann paper; see `knowledge/05_pre_run_implementation_audit_2026-10-03.md`.
- (V) Horowitz 2018, Stanford-hosted review: https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf — operationally describes continuation heights and horizontal-gradient modulus maxima; potential-field interpretation remains non-unique and depth estimates degrade with depth. Persistence is not a unique depth estimate or proof of faulting.
- (Measured here, current preregistered implementation) On pinned owner-mirror grids using nearest-valid FFT exterior padding: 85,427 magnetic / 25,888 gravity level-0 p95 edges; 17.1% / 58.7% are level-0-only; 17.3% / 19.1% survive to 1600 m. Mean normalized persistence is 0.485 magnetic / 0.302 gravity (P = last matched 0-based level / (number of levels − 1), bounded [0,1]). E–W / other / N–S mean magnetic P is 0.540 / 0.491 / 0.447. The strike result does not identify an acquisition artifact; a spectral-frequency test remains separate. An intermediate implementation overwrote nearest fill with a global median; its screen and artifacts are archived as nonconforming in `evidence/history/pre_nearest_fill_2026-10-03/`.
- (Measured here, soft operator check) Our 150 m TMI continuation HGM ranks have Spearman 0.878 against the owner-mirrored, u8-quantized contractor-labelled `TMI_up150` grid. It is a numerical consistency check, not data provenance authentication.
- (Correction / historical status) The first implementation normalized six ladder levels by `n_levels-2`, permitting P=1.25 and altering both thresholding and ranks. Its worming receipt and H29 scores are invalid for the registered method; original snapshots remain under `evidence/history/` and `knowledge/history/`. The gate also previously omitted confirmation draws from its summary; synthetic regression tests now cover confirmation draw 2/3 handling.
- (Corrected proxy screen) On two complete screen draws × four quadrants, A1 means −0.000094/−0.000231; A2 −0.000996/+0.000257; B1 +0.000377/+0.000350; B2 +0.000497/+0.001232. Each missed the +0.005 screen threshold. H29-5's new persistence × strain/seismicity head was −0.078014/−0.087947 versus the best same-fold/draw pre-existing control, with 0/4 folds positive on both draws. It failed the frozen screen; confirmation draws were not run under the preregistered compute-saving rule. No slot was spent or recommended. These are catalogue-internal proxies, not live/private scores; see `evidence/h29_holdout.json` and `knowledge/02_h29_results_2026-10-03.md`.

## 4. The metric arithmetic that decides strategy (live-score inversion, siblings + this repo's check)

- (V) Masking semantics: catalogue pixels are removed from both credit and FP (sibling live-coincidence
  evidence; 8GEMSDOE == GEMSDOE 0.1563 after adding all catalogue pixels).
- (V, reproduced here) dot_thin(H19-5_solid, 1.5) == the owner-mirrored d1.5 mask pixel-for-pixel;
  dot_thin(·, 2.8) matches the pinned owner-mirrored D2.8 mask pixel-for-pixel (44,090 positives). GeoTIFF bytes differ. This verifies mask reproduction only; the 0.2600 score-to-file association remains owner-reported.
- (C + metric-based interpretation) The owner-reported H19-5 parent/D1.5/D2.8 sequence is 121,131 px / 0.1922, 60,069 / 0.2477, and 44,090 / 0.2600. D2.8 sets a minimum spacing of 2.8 cells (~280 m at the 100 m grid), close to the official 300 m linear distance-support radius. Along a straight trace, the midpoint of a 280 m gap is ~140 m from the nearest dot (kernel weight ≈0.53). Sparse geometry can plausibly retain near-line credit while pruning redundant/remote emission under the distance-weighted metric (false-positive coefficient 0.2; false-negative coefficient 0.8). This is a plausible explanation for the reported trend, not causal attribution: the score-to-file link is unauthenticated and the public scoring labels are unavailable locally.
- (S) Retention identity: DTI = TPw/(0.2·TPw·(1−ρ) + 0.2·N + 0.8·|G|); credit of a subset ≈ credit_solid ×
  c(subset)/c_solid; validated to −0.1 % (h19-5→d1.5) and +4.0 % (h25-ctx→h28) against live anchors;
  |G| ≈ 12.2–12.8 k truth px; emission geometry exhausted at ≈0.255–0.260 on this surface.
- (V, 2026-10-03 leaderboard read) Public #1 = DARD 0.3195 (12 subs); #2 = nchuzhoy 0.3128 with only
  2 submissions → materially better detector, not schedule luck; our 0.2600 sits at public #15.
- (S) Concentration ceiling: every group emission ever measured ≤ 5.7× blind; beating 0.3195 at
  ≤ 60k px needs > 0.570·|G| credit — "only new information that ranks fault-proximal truth better".

## 5. What has been tried across GEMSDOE…27 (dedupe table — do not re-derive)

| lever | live outcome | lesson |
|---|---|---|
| U-Net-style ensemble + hedge (GEMSDOE, 8) | 0.1563 | raw ML on supplied bands plateaus |
| pindrop thermal/geochem nodes (3) | 0.083–0.119 | point-evidence emission alone is weak |
| LiDAR scarp top-2 % (7) | 0.1461 | 1 m DEM scarps are good habitat, bad budget |
| dotted ridge surfaces (10) | 0.0921→0.1839 by dotting alone | +44 % from geometry |
| multi-line corroboration h19-4/5 (19) | 0.1894/0.1922 | 4-line gate beats single-layer matches |
| d1.5 → d2.8 dotting (24→25) | 0.2477 → 0.2600 | spacing optimum ≈ 2.8 px, confirmed live |
| +1,259 far-field topology dots (27) | 0.2449 (vs 0.2477) | far-field dot ADDITION lost live — needs ≥1.62× blind |
| SGMC bedrock-gap habitat (16 h18-4) | 0.0360 | bedrock-map gap ≠ hidden-fault habitat |
| XEDGE scale-persistence features (26) | blocked +0.0014/+0.005 | Gaussian scale-persistence as feature: no |
| DILCOND dilatation×conductivity (26) | blocked +0.0032/+0.005 | coincidence feature without edges: no |
| blind lattice (13) | 0.0904 | pure-geometry |G| calibration anchor |

## 6. Free official data NOT yet used by anyone in this family (leads for next sessions)

1. Siler & Faulds slip/dilation-tendency shapefile (doi 10.5066/P9YL58W6, USGS) — stress-conditioned
   slip tendency per Quaternary fault; registered H26-4 stalled on fetch; pairs with H29-5 corridors.
2. GDR 1391 paleo-geothermal polygons + Great Basin Q volcanics (pins in data/manifest.json) — blocked
   by sandbox network only; one CI-runner job away (GEMSDOE27 wrote `fetch_external_layers.py` for exactly this).
3. USGS 3DEP 1 m DEM tiles beyond the 706 already processed (the `1m_DEM_links.csv` list) for
   sub-100 m scarp refinement under persistent worm corridors only (cheap, targeted — not blanket LiDAR work).
4. Nevada BLM mineral-interest / geothermal lease parcels (GEMSDOE24 audit_sources holds closed-claim
   distance already) — human-activity audit layer, useful as NEGATIVE control (suppress, not promote).
5. DOGGS/INGENIOUS produced-well temperature atlases (GBC open data) for a heat-flow residual surface —
   H27-4's "blocked" idea; check licence on the specific DOI page before use.
6. Earthquake phase data (ComCat) for re-located microseismicity swarms — the bands give pre-computed
   densities (deq/ieq_n100a15); raw picks at fixed radius/azimuth windows would re-shape that term.
   Only worth it if used along persistence-selected corridors (H29-5).

## 7. Submission-site engineering lessons (this family's own incident log, now enforced in code)

- NaN inside footprint = "[0, 1]" rejection (GEMSDOE25 IR); both NaN/zeros outside are accepted (12GEMSDOE pair);
  Pages must build from the ROOT index (IR-25-PAGES-ROOT); every download ships with read-back verification +
  sha256 + a ≤200-char Note; never claim a live score without a receipt; pre-register gates before running;
  owner mirrors are hash-pinned and marked not-organizer-authenticated everywhere they appear.

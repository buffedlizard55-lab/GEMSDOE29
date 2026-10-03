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
- (V) The September 2026 Official Rules PDF at https://docs.nlr.gov/docs/fy26osti/96647.pdf was fetched and sections 3.2–3.5 reviewed in the current source register. It permits up to three weekly feedback submissions, requires selection of one final submission for both prize rounds, and requires generative-AI use disclosure in the narrative when applicable. Check the linked current rules and timeline before acting.

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

## 3. Worming ("multiscale edge" line tracking) — the method used here

- (V/S) Hornby, P., Boschetti, F., Horowitz, F.G., 1999. Analysis of potential field data in the wavelet
  domain. Geophysical Journal International 137(1):175–196 — doi:10.1046/j.1365-246X.1999.00788.x.
  Upward continuation of a potential field is a wavelet scale change; the modulus maxima of the
  horizontal gradient at each continued height are the multiscale edges; their decay with height
  classifies the source singularity (Lipschitz exponent); "worm" tracks connect the maxima across scales.
- (V) Operational recipe + caveats: Horowitz 2018, Stanford GMR workshop
  https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf — gravity: UC to a suite of heights,
  local HGM maxima at each; magnetics: work on RTP/pseudogravity; "the change with depth of the position
  of an edge marks the dip"; depth estimates degrade with depth. Commercial implementation (Intrepid
  "WormE", https://docs.intrepid-geophysics.com/intrepid/topics/edge-detection-worme.html) confirms the
  industry usage: "creates many upward continuation grids", groups edge points into worms, reports
  strike/depth/structural index.
- (V, measured here on pinned owner-mirror grids; not organizer-authenticated) With nearest-valid FFT exterior padding, the current implementation finds 85,427 magnetic / 25,888 gravity level-0 p95 edges; 17.1 % / 58.7 % are level-0-only; 17.3 % / 19.1 % survive to 1600 m. Mean bounded persistence is 0.485 / 0.302. The UC operator's HGM ranks correlate with the owner-mirrored contractor-labelled TMI_up150 grid at Spearman 0.880 (298,649 sampled pixels); this is an operator check, not source authentication. E–W / other / N–S mean magnetic persistence is 0.540 / 0.491 / 0.447. It is a descriptive strike summary, not proof of line contamination or basement fabric; do not kill E–W edges without a separate spectral test.
- (V, current preregistered negative result) The corrected nearest-fill, bounded-P screen tested A1/A2/B1/B2 and H29-5 over two screen draws × four spatial folds. All five failed. H29-5 was −0.07894/−0.08703 mean paired proxy DTI vs the best same-fold/draw control, with 0/4 positive folds on each draw. A1/A2/B1/B2 were below the +0.005 bar; no confirmation draws were fit. See `evidence/h29_gate.json` and `knowledge/02_h29_results_2026-10-03.md`. These catalogue-gap proxy results neither predict the leaderboard nor disprove a geological mechanism.
- (V, audit correction) An earlier bounded-P implementation still replaced nearest-filled FFT padding with a global median, contrary to the frozen method; its screen and artifact are archived under `evidence/history/pre_nearest_fill_2026-10-03/` and must not be treated as current. The original P>1.0 variant is separately archived under `evidence/history/pre_correction_downloads/`.

## 4. Metric arithmetic and local proxy calibration (no leaderboard snapshot)

- (V) Masking semantics: catalogue pixels are removed from both credit and FP (sibling live-coincidence
  evidence; 8GEMSDOE == GEMSDOE 0.1563 after adding all catalogue pixels).
- (V, reproduced here) dot_thin(H19-5_solid, 1.5) == the 0.2477 file's mask bit-for-bit;
  dot_thin(·, 2.8) → exactly 44,090 px (the 0.2600 file's count). Geometry is reproducible, not folklore.
- (S/C) Retention identity: DTI = TPw/(0.2·TPw·(1−ρ) + 0.2·N + 0.8·|G|); prior calculations estimated a 12.2–12.8k-pixel truth scale and an approximately 0.255–0.260 geometry range for one historical surface. These are owner/sibling-derived estimates, not verified competition results; no live leaderboard arithmetic is retained here.
- (C) A prior main-branch commit contained a manually copied public leaderboard snapshot. This PR removes the snapshot and rank/team details under the current Terms policy. The historical user-provided prompt is preserved as source text, but those claims are not independently verified, used as targets, or shown in the status site.
- (S/C) Concentration arithmetic in earlier sibling notes was conditional on those owner-reported anchors and is not a competition-score forecast. Do not use it to decide whether to spend a weekly slot.

## 5. Older experiment inventory (historical owner/sibling reports; not independently verified)

The figures below are preserved as qualitative project-history context from prior repositories and the owner's materials. No organizer receipts, account identity, or score-to-file mapping were independently verified for them. They are not used as training targets, promotion gates, or a live-score feed.

| lever | historical reported outcome (unverified) | lesson / limit |
|---|---|---|
| U-Net-style ensemble + hedge (GEMSDOE / GEMSDOE8) | 0.1563 reported | raw ML on supplied bands was reported to plateau |
| thermal/geochemical point evidence | 0.083–0.119 reported | point-evidence emission alone was reported weak |
| LiDAR scarp top-2% emission | 0.1461 reported | terrain scarps may be useful habitat but can be inefficient at a strict budget |
| dotted ridge surfaces | 0.0921→0.1839 reported | spacing changes can alter emission geometry; historical score mapping is unverified |
| multi-line corroboration H19-4/5 | 0.1894/0.1922 reported | a multi-line gate was explored; values are owner reports |
| d1.5 → d2.8 thinning variants | 0.2477→0.2600 reported | local mask/count reproduction does not authenticate the score relationship |
| far-field topology additions | 0.2449 vs. a 0.2477 reported anchor | one owner-reported comparison was negative; not a leaderboard-derived claim here |
| SGMC bedrock-gap emission | 0.0360 reported | a geologic-map gap is not itself evidence of hidden-fault habitat |
| XEDGE scale-persistence features (GEMSDOE26) | proxy gate reportedly failed | Gaussian scale-persistence was tried; H31 must not be described as the first persistence test |
| DILCOND dilation×conductivity (GEMSDOE26) | proxy gate reportedly failed | this earlier conjunction is not evidence for any new interaction without a fresh test |
| blind lattice | 0.0904 reported | retained only as prior project context |


## 6. Free official data NOT yet used by anyone in this family (leads for next sessions)

1. Siler & Faulds slip/dilation-tendency shapefile (doi 10.5066/P9YL58W6, USGS) — stress-conditioned
   slip tendency per Quaternary fault; registered H26-4 stalled on fetch. H29-5's tested strain/seismicity interaction failed its registered catalogue-gap screen; any reuse needs a new hypothesis and independent evidence.
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
   Do not repeat the failed H29-5 feature combination without a newly preregistered physical target and stronger off-catalogue validation.

## 7. Submission-site engineering lessons (this family's own incident log, now enforced in code)

- NaN inside footprint = "[0, 1]" rejection (GEMSDOE25 IR); both NaN/zeros outside are accepted (12GEMSDOE pair);
  Pages must build from the ROOT index (IR-25-PAGES-ROOT); every download ships with read-back verification +
  sha256 + a ≤200-char Note; never claim a live score without a receipt; pre-register gates before running;
  owner mirrors are hash-pinned and marked not-organizer-authenticated everywhere they appear.

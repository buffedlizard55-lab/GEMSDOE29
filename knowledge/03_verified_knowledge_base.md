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
- (C) 3 submissions per rolling 7 days — from the official rules PDF (www.nlr.gov/docs/fy26osti/96647.pdf),
  NOT re-readable in this sandbox (IR-29-RULES-URL); multiple sibling sessions behaved consistently with it.

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
  domain. Geophysical Journal International 137(1):175–196 — doi:10.1046/j.1365-246X.1999.00793.x.
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
- (V, measured here) On the official grids: 87k magnetic / 30k gravity level-0 p95 edges; 17.8 % / 51.0 %
  exist at zero continuation only; 17.4 % / 18.0 % survive to 1600 m; our UC operator matches the
  contractor TMI_up150 grid (Spearman 0.878 on HGM ranks). E–W-striking edges are the MOST persistent
  (0.656 vs 0.562 N–S) — E–W lineation artifacts, if present, are not the dominant shallow population;
  regional E–W basement fabric is the parsimonious reading. Any 'kill E–W' heuristic is refuted (V).
- (V, this session's negative result) On the catalogue-internal hide-and-recover proxy, worming
  persistence as gate (A1), rank (A2) or head features (B1), and thermal-probe features (B2) all move
  sparse proxy DTI by |Δ| < 0.001 vs the +0.005 frozen gate (see evidence/h29_gate.json). Interpretation:
  (i) the proxy cannot see the far-field habitat where worming operates (structural blind spot, disclosed);
  (ii) at p95 edge density the parent emission is 97 % off-edge, so gating is nearly a no-op and ranking
  is a weak lever; (iii) no evidence that worming is FALSE science — evidence that this proxy + this
  emission surface cannot adjudicate it in a weekend. H29-3/H29-5 register the sharper versions.

## 4. The metric arithmetic that decides strategy (live-score inversion, siblings + this repo's check)

- (V) Masking semantics: catalogue pixels are removed from both credit and FP (sibling live-coincidence
  evidence; 8GEMSDOE == GEMSDOE 0.1563 after adding all catalogue pixels).
- (V, reproduced here) dot_thin(H19-5_solid, 1.5) == the 0.2477 file's mask bit-for-bit;
  dot_thin(·, 2.8) → exactly 44,090 px (the 0.2600 file's count). Geometry is reproducible, not folklore.
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

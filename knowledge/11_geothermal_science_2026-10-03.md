# Verified geothermal-fault knowledge base (for this project and its successors)

**Date:** 2026-10-03 (UTC). Everything below is either quoted from an official/primary source with a link,
or marked as an inference of this project. Nothing here was fetched from `drivendata.org` (see
`knowledge/03_drivendata_terms_access_policy.md`); competition-specific statements are attributed to the
public problem description and to what peers report staff said, each labelled.

## 1. The physical model this competition encodes

In the amagmatic Great Basin, high-temperature systems need **heat** (regional crustal heat flow, locally
magmatic) *and* **permeability**; faults supply the permeability (Faulds et al., 2006, 2011; Faulds &
Hinz, 2015). Fluid rises along critically stressed, dilatant fault intersections and flows laterally in
valley fill. Consequently:

* Major range-front normal faults host only ~1 % of catalogued systems (their thick clay gouge and
  earthquake cycling reduce permeability) — Faulds & Hinz (2015), Giddens & Faulds (2025) Figure 2.
* Step-overs/relay ramps host ~32 % of catalogued systems in the 2012–2015 inventory (Faulds, Hinz &
  Kreemer, GDR 383, <https://gdr.openei.org/submissions/383>) and ~47 % of producing systems / ~39 % of
  known Nevada systems in the 2025 re-analysis (Giddens & Faulds, Stanford SGW 2025,
  <https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf>).
* Fault **terminations**/horse-tails host ~22–25 %, normal×transverse **intersections** ~22 %
  (same sources; Faulds & Hinz, WGC 2015, <https://www.semanticscholar.org/paper/bcf2deeaf6877d0f8631d4dcae78976a7e404236>).
* **As much as ~75 % of the Great Basin's geothermal resources may be blind/hidden** (Giddens & Faulds
  2025, quoting the earlier UNR assessments) — which is exactly the class this competition asks for.

## 2. Competition-specific facts (public problem description, transcribed)

* Test truth = “faults that are not contained within the current public USGS database”, manually
  identified by consulted experts; the final round re-scores the same submission against an **expanded**
  label set after experts review all teams' predictions
  (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>, transcribed 2026-10-02/03).
* Metric: distance-weighted Tversky index, α = 0.2 (FP), β = 0.8 (FN), triangular kernel R = 300 m.
  Consequence proved in `knowledge/07_metric_emission_analysis_2026-10-03.md`: **recall-dominant covering**.
* **Reported (second-hand, flagged):** DrivenData staff statements relayed by peer projects
  (2026-09-16, 2026-09-22) say catalogue pixels are masked out of evaluation, and that “new fault”
  includes newly mapped **geometry of an existing fault system**. Verify in the official forum before
  relying on it for a submission decision.

## 3. Free, official data sources that matter for this problem

| Source | What it adds | Link / DOI | Reachable from this sandbox? |
|---|---|---|---|
| USGS Quaternary Fault and Fold Database | the catalogue the prize calls “incomplete” | <https://usgs.github.io/faults/> | no (usgs.gov blocked) |
| INGENIOUS / GDR 1391 (2 m probes, well & spring chemistry, paleo-geothermal, Q volcanics) | thermal + geochemical ground truth | <https://gdr.openei.org/submissions/1391>, DOI 10.15121/1881483 | no from sandbox; the two CSVs + probe archive are already hash-pinned here |
| Siler (2022) slip & dilation tendency for Great Basin Quaternary faults | per-segment stress favourability | DOI [10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6) | no from sandbox (sciencebase.gov blocked); metadata verified via index |
| Peacock & Bedrosian (2022) electrical-conductance maps of the Great Basin | MT conductance/fault-zone alteration | DOI [10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU) | no from sandbox; a conductance surface is already a competition band |
| GeoDAWN airborne magnetics/radiometrics (USGS ScienceBase item 657e1d85d34e23d3533209f7) | the competition's potential-field stack | <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> | no from sandbox; already inside `training_features.tif` |
| USGS 3DEP | 1 m DEM for scarp work; no use restrictions | <https://www.usgs.gov/3d-elevation-program/about-3dep-products-services> | no from sandbox; 706 tiles already distilled into the mirrored LiDAR descriptor stack |
| NBMG report r058 (Faulds et al., 2021) | inventory of structural settings, Nevada | <https://pubs.nbmg.unr.edu/Inventory-structural-settings-p/r058.htm> | not tested |

**Sandbox network reality (verified 2026-10-03, `curl` exit 35 / HTTP 000):** only `github.com`,
`codeload.github.com`, `api.github.com` and `pypi.org` resolve. `gdr.openei.org`, `drivendata.org`,
`usgs.gov`, `sciencebase.gov`, `earthquake.usgs.gov`, `pubs.usgs.gov`, `osti.gov` and
`raw.githubusercontent.com` all fail with `SSL_ERROR_SYSCALL`. Any new external layer therefore needs the
owner's unrestricted runner (or a public GitHub mirror); none is required by the Rank 1–5 hypotheses in
`knowledge/10_candidates_v2_2026-10-03.md`, which all run on layers already pinned in this repository.

## 4. Transform background for the candidate hypotheses

* **Multiscale worming** — Hornby, Boschetti & Horowitz (1999), *Geophysical Journal International* 137,
  175–196, [doi:10.1046/j.1365-246x.1999.00788.x](https://doi.org/10.1046/j.1365-246x.1999.00788.x);
  Horowitz (2018) review, <https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf>.
  Edge maxima of the horizontal-gradient modulus tracked through upward-continued heights; the review
  warns that inversion is non-unique, deeper edges are less accurately located, and strong sources shadow
  weaker ones.
* **Euler deconvolution** — Reid et al. (1990), *Geophysics* 55, 80–91,
  [doi:10.1190/1.1442774](https://doi.org/10.1190/1.1442774); structural-index pitfalls documented in
  Reid et al. (2013) and Reid & Thurston (2014), both public at <https://www.reid-geophys.co.uk/>.
* **Slip/dilation tendency** — Morris et al. (1996) for slip tendency, Ferrill et al. (1999) for dilation
  tendency, as implemented by Siler (2022) for Great Basin fault segments (above).
* **Silica geothermometry** — the GDR 1391 table already carries quartz, chalcedony and Na-K-Ca
  temperature estimates per spring; standard calibrations are Fournier (1977) and Giggenbach (1988),
  and the file's own columns are what the mirror holds, so no external calibration is needed to use them.

## 5. What this implies for strategy (inference, not source)

1. Because the scored truth excludes the catalogue, *accuracy on the catalogue is not the objective* —
   measured local gains on catalogue-gap folds can be orthogonal to the leaderboard (this repository has
   now measured both signs of that effect; see `knowledge/09_h34_results_2026-10-03.md`).
2. The prize's final round explicitly rewards predictions that help experts find **previously unmapped**
   faults, so habitat for *unmapped* structures (interaction zones, MT conductance edges, off-catalogue
   heat-flow anomalies, deep potential-field edges) is worth more than another catalogue-fitting feature.
3. The metric multiplies that: uncovered truth costs 0.8 while unnecessary prediction mass costs 0.2
   (see the marginal rule), so a detection channel that is even modestly informative *off catalogue*
   should be emitted generously, while mass piled onto the catalogue is worthless.

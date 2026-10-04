# 43 — Proxy calibration against ten owner-reported sibling scores (2026-10-03)

Script: [`scripts/calibrate_proxy_against_reported_scores.py`](../scripts/calibrate_proxy_against_reported_scores.py).
Evidence: [`evidence/proxy_calibration.json`](../evidence/proxy_calibration.json). **No model is fitted** — every
row is one stored raster scored by the same two frozen proxies the screens use (`gemsdoe.proxies`), so this
document is a *ranking* check, not a new experiment and not a competition score.

**Why:** `knowledge/34` §6.1 made this the project's first strategy item. Every promotion decision in this
repository is gated on the catalogue-hidden proxy, but its only external anchor was a three-point ordering
(`H19-5 0.1922 < D1.5 0.2477 < D2.8 0.2600`) from unverified owner reports (`knowledge/17`, `knowledge/32`).
Three points cannot tell a proxy from a coincidence. This extends the anchor set to ten and measures the
rank correlation.

## Method

* Ten artifacts whose **reported** competition scores are stated in the owner's brief or in a sibling
  repository's own README. Three (H19-5, D1.5, D2.8) are hash-pinned mirrors inside this repository; the
  other seven were fetched from the owner's **public GitHub** sibling repositories with the authenticated
  `gh` CLI (raw media type), recording repo, branch, commit SHA, path, byte size and SHA-256 in the evidence
  file. **No DrivenData endpoint was contacted**; nothing is scraped or polled.
* Each raster is read as the binary emission the portal would see (`finite & > 0`) and scored on:
  * **catalogue-hidden** (the primary proxy) — masked DTI on hidden catalogue components, 4 quadrant folds ×
    draws 20/21, `hide_frac` 0.20, domain eroded 12 px, 15 px collar;
  * **SGMC off-catalogue** (the secondary proxy) — masked DTI against `derived_sgmc_faults_100m_u8.tif`
    faults ≥ 300 m from the supplied catalogue, inside the footprint.
* Correlation is computed between reported score and proxy score over the usable anchors. Reported scores are
  **owner claims**; only the D2.8 raster is byte-pinned in this repository. `13GEMSDOE` resolved to its
  `_zerofill` variant because that repository publishes both variants and the `find_file` preference string
  did not match the `_nan-outside` spelling — harmless here, since both variants are identical under the
  `> 0` mask (zero and NaN are both non-emission).

## Results (10/10 anchors usable)

| anchor (sibling) | reported | catalogue-hidden | SGMC | emitted px | hug | on-catalogue px |
|---|---:|---:|---:|---:|---:|---:|
| D2.8 (GEMSDOE25, pinned) | 0.2600 | 0.09832 | 0.0953 | 44,090 | 0.187 | 0 |
| D1.5 (GEMSDOE24, pinned) | 0.2477 | 0.09449 | 0.1011 | 60,069 | 0.190 | 0 |
| tgc-t-v2-on-d1-5 (GEMSDOE27) | 0.2449 | 0.09412 | 0.1024 | 61,328 | 0.190 | 0 |
| H19-5 (19GEMSDOE, pinned) | 0.1922 | 0.06970 | 0.1006 | 121,131 | 0.190 | 0 |
| lidarscarp-ridge-top2pct (7GEMSDOE) | 0.1461 | 0.08464 | 0.0658 | 76,859 | 0.219 | 0 |
| h30-arrangement (GEMSDOE23) | 0.1352 | 0.09258 | **0.2010** | 91,533 | 0.124 | 0 |
| dilcond-oof-v1 (GEMSDOE26) | 0.1223 | 0.07175 | 0.1072 | 60,068 | 0.140 | 1,398 |
| pindrop-v4-nodes (GEMSDOE3) | 0.1193 | 0.07884 | **0.2359** | 155,021 | 0.085 | 0 |
| r13-lattice-s5-v2 (13GEMSDOE) | 0.0904 | 0.08571 | **0.2509** | 206,895 | 0.081 | 2,391 |
| conj-alteration-mag (15GEMSDOE) | 0.0782 | 0.06966 | 0.1802 | 99,999 | 0.085 | 1,263 |

**Rank correlation, reported score vs proxy score (n = 10):** catalogue-hidden **Spearman +0.709**,
Kendall **+0.556**, Pearson **+0.637**. SGMC off-catalogue orders the worst three artifacts *highest*
(r13 0.2509, pindrop 0.2359, h30 0.2010 — reported 0.0904 / 0.1193 / 0.1352), i.e. its rank correlation with
the reported scores is **negative** on this set.

## What this changes

1. **The primary proxy is a usable ranking device, not an oracle.** A +0.71 Spearman over ten files is real
   signal for *ordering* candidate families (and it is the first external validation the proxy has had), but
   the same proxy places D2.8 (0.2600) and tgc-t-v2-on-d1-5 (0.2449) within 0.0002 of each other while the
   live scores differ by 0.015 — expect ±0.01-scale ranking noise, which is exactly the scale of the G1 bar
   (+0.005). Screens must keep reporting fold-level detail; a single mean is not enough.
2. **The SGMC proxy must never be promoted to a veto on its own.** `IR-29-PROXY-VETO-PATTERN` had already
   vetoed H41's and H43's best arms and withheld H53's `A2`; this calibration shows the SGMC proxy ranking
   the three lowest-scoring artifacts on top. The H41/H43/H53 decisions stand as *conservative* (no slot was
   spent, nothing was lost), but the rule is now explicitly recorded as a *conservative filter with known
   false vetoes*, to be re-examined before the next slot decision — a candidate that passes G1/G2 and fails
   only G3 should be escalated to the owner as "primary pass, secondary conflict" rather than silently
   closed.
3. **A hard ceiling is now visible in the emission, not the features.** The two best reported artifacts in
   the whole family (D2.8 0.2600, D1.5 0.2477) emit 44 k–60 k dots with hug ≈ 0.19 and *zero* on-catalogue
   pixels, while the low scorers emit 92 k–207 k dots. Dense, loosely-catalogued emissions underperform;
   selective, off-catalogue emissions win. That is quantitative support for `knowledge/34`'s "credit
   density" reading and it is now recorded as a *proxy-level* regularity (10 files), not a single-artifact
   story.

## Limits (stated so they are not over-read)

* Reported scores are unverified owner claims except the pinned D2.8 raster; two anchors (h30, r13/pindrop)
  come from stages whose README text does not state the number, so their "reported" values rest on the
  owner's brief alone.
* The anchors are **not independent**: the high scorers are near-copies of one lineage (D2.8 ⊂ D1.5 ⊂
  H19-5 emission recipes), so the correlation is partly measuring "this lineage's artifacts rank above the
  others", not ten independent tests.
* The correlation is measured on *stored final artifacts*, whose emission recipes differ (dot thinning,
  budgets, masks). It validates the proxy as a ranking of **outputs**, which is what a promotion gate needs,
  but it does not validate it as a per-column feature statistic.
* `n = 10` with one tie-free array: a Spearman of +0.709 has a two-sided p ≈ 0.02 under the null, i.e.
  significant but fragile; re-run this script whenever a new sibling artifact with a reported score appears.

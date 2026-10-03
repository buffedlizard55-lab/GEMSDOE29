# H31b screen results — dense continuous worming persistence (2026-10-03)

Frozen protocol: [`knowledge/19_preregistered_h31b_dense_worming_2026-10-03.md`](19_preregistered_h31b_dense_worming_2026-10-03.md)
(frozen revision `14b8c68ea21c0c182606b27bc7e1d4c18384d6a6`, preregistration SHA-256
`ff66c20c84c93de3…`). Raw artifacts: [`evidence/h31b_dense_screen/{design.json, cells.jsonl, summary.json}`](../evidence/h31b_dense_screen/).
Execution: branch `arena/01a102cf-gemsdoe29`, clean committed worktree at the frozen revision,
draws 22/23 × four spatial quadrants × five arms, 40/40 cells finite, 1281 s wall clock.
No DrivenData endpoint was touched; all inputs are the hash-pinned owner mirrors.

## 1. Feature density — the H31 defect is removed

The failed H31 cache was nonzero on 0.001–0.084 % of the footprint
([`knowledge/16`](16_h31_screen_results_2026-10-03.md)). The dense H31b family W (12 columns,
built by `src/gemsdoe/wormdense.py`, cache `data/work/wormdense_features.npy`,
SHA-256 `08831a00debf4183…`) is:

| Column family | Nonzero fraction (footprint) |
|---|---:|
| `W_*_FRAC`, `W_*_LAST` (persistence columns) | 7.96–8.03 % |
| `W_*_E0`, `W_*_DEEP` (edge-amplitude columns) | 78.25 % (observed-data mask) |

Every arm's output now differs from the control (H31 emitted pixel-identical dots in 8/8 cells;
H31b differs in all 40 cells). The worming family is finally able to move the ridge + top-K +
dotting output, so this is the first non-null test of the family in this repository.

## 2. Primary result — catalogue-hidden proxy, per fold × draw (DTI, α=0.2, β=0.8, R=300 m)

| Cell | `C_base` | `C_wrtp` | `C_wpsg` | `C_wgrav` | `C_wall` (primary) | Δ wall−base |
|---|---:|---:|---:|---:|---:|---:|
| NW · d22 | 0.1352 | 0.1255 | 0.1253 | 0.1326 | 0.1371 | +0.0019 |
| NW · d23 | 0.1376 | 0.1362 | 0.1396 | 0.1387 | 0.1335 | −0.0040 |
| NE · d22 | 0.1599 | 0.1700 | 0.1730 | 0.1662 | 0.1696 | +0.0097 |
| NE · d23 | 0.1564 | 0.1501 | 0.1454 | 0.1416 | 0.1527 | −0.0037 |
| SW · d22 | 0.1378 | 0.1475 | 0.1484 | 0.1418 | 0.1454 | +0.0076 |
| SW · d23 | 0.1436 | 0.1524 | 0.1457 | 0.1434 | 0.1550 | +0.0115 |
| SE · d22 | 0.1522 | 0.1443 | 0.1653 | 0.1428 | 0.1531 | +0.0009 |
| SE · d23 | 0.1938 | 0.2080 | 0.1957 | 0.2081 | 0.1973 | +0.0035 |
| **8-cell mean** | **0.15205** | **0.15424** | **0.15480** | **0.15189** | **0.15547** | **+0.00342** |

Secondary (descriptive only, registered proxy-conflict IR-29-PROXY-CONFLICT): SGMC
off-catalogue class (62,703 px) — `C_base` 0.08396, `C_wrtp` 0.08331, `C_wpsg` 0.08330,
`C_wgrav` 0.08135, `C_wall` 0.08341: no off-catalogue lift for any W arm.
Catalogue-hug share is unchanged (0.100–0.105 across arms), so the gain is not "hug the
catalogue harder".

## 3. Frozen gate verdict — **FAIL**

| Gate | Draw 22 | Draw 23 | Verdict |
|---|---|---|---|
| G1 mean paired gain ≥ +0.005 | +0.005037 (4/4 folds positive) | +0.001801 (2/4 positive) | **FAIL (draw 23)** |
| G2 ≥ 3/4 folds positive | 4/4 ✓ | 2/4 ✗ | **FAIL (draw 23)** |
| G3 no fold < −0.010 | min +0.0009 ✓ | min −0.0040 ✓ | PASS |
| G4 8-cell mean > 0.14479 (then-current comparable holdout best) | 0.15547 > 0.14479 | | PASS |
| G5 40/40 cells finite + manifest hashes | ✓ | | PASS |

Per the frozen decision rules (knowledge/19 §5): any screen gate failure → **stop**. No
confirmation (draws 24/25) is run, no candidate TIFF is built, and no weekly slot is
considered. This is a proxy outcome, not a competition score.

## 4. What the result actually says

1. **The dense family is positive on average but draw-unstable.** Draw 22 passes G1 exactly
   (+0.0050, 4/4 folds); draw 23 does not (+0.0018, 2/4 folds). The sign pattern is not
   random cell noise: two of the four negative cells are the *draw-23 NW/NE* cells, where the
   base model's own score is only slightly different between draws — the W family's effect is
   **conditional on which fault components the hide step removed**, i.e. it interacts with the
   specific spatial mixture of hidden segments.
2. **Hidden-set composition is broadly similar between draws** (per fold: hidden truth pixels
   2025/1986, 2501/2514, 3898/4065, 3448/3719; mean distance to visible catalogue 12.6/11.2,
   17.6/15.6, 10.7/10.5, 12.6/11.9 px) — so the instability is a *which-segments* effect, not
   a bulk-geometry effect. The most anomalous cell is `SE·d23` (base 0.1938, an outlier high
   base score): the segments hidden there happen to sit where the base model is already
   confident, which compresses any additive feature's room to help.
3. **Branch ranking: magnetic routes lead.** `C_wpsg` (pseudogravity-proxy route, +0.00275)
   and `C_wrtp` (+0.00219) are the two positive branches; the isostatic-gravity branch
   `C_wgrav` is inert (−0.00016). This is consistent with the physical expectation that the
   magnetic layer (GeoDAWN's strong, flight-calibrated potential field) carries the usable
   edge population while the isostatic anomaly's HGM persistence does not, at these scales.
4. **Absolute level.** `C_wall`'s 0.15547 is the highest same-protocol (Cell/emission/K/metric)
   8-cell screen mean recorded in this repository to date (H31 `T_BASE` 0.14708, H34 C1
   0.14479, H34 C0 0.14086). It is **not** a new "holdout best" in the repository's sense: the
   promotion anchor is a *gate-passing* method, and C_wall failed its frozen stability gates,
   so the comparable anchor remains H34 C1 at 0.14479. The number is reported here for the
   scientific record only and is used nowhere as a promotion input.

## 5. Decision and next steps (frozen by this record)

* **Stop.** No confirmation, no candidate file, no slot. The H31b screen is closed as a
  negative stability result with a positive mean — the worming family is not closed (unlike
  H31's null), it is *unproven at the frozen stability bar*.
* If the owner wants the worming family tested again, it requires a **new preregistration**
  (this one is consumed by its decision rules), with at minimum: (a) four fresh draws
  (seeds 26–29 are unused) to average out the which-segments interaction, (b) a
  magnetic-route-only family (drop the inert GRAV branch; keep RTP+PSG) so the tested family
  matches the two positive branches, and (c) the same G1–G5 structure. This is a planning
  option, not scheduled work.
* **Rank 2 of the v3 slate is now the lead local candidate: H36 (MT conductance structural
  edges and step asymmetry)** — local bands, 0.5–1 day, preregister before any fit.
* **H35** (interaction zones) remains blocked on the owner-side fetch of Siler (2022)
  DOI 10.5066/P9YL58W6 (sciencebase.gov is unreachable from this sandbox, IR-29-SANDBOX-NET);
  a stress-direction-approximated first test is possible without it.
* No file on the site is slot-approved; the repository's recommendation is unchanged: the
  owner decides, and the slot is spent at most once (one selected submission scores in both
  prize rounds).

All numbers above are spatially blocked **proxy** results on hash-pinned owner-mirror inputs
with artificially hidden catalogue components. They do not measure the organizer's hidden
expert-labelled test faults or any leaderboard score.

## 6. Postscript (2026-10-03, merge-time): independent confirmation by a parallel workstream

A parallel session-3 workstream (merged to main as PR #7/#8) preregistered and ran an
**independent screen of the same dense-persistence idea** — their H40 "dense continuous
upward-continuation persistence ladder" — on draws 24/25 (the draws this workstream had
reserved for H31b confirmation), plus new H35 tip-corridor interaction fields. All four of
their arms **also failed** their frozen gate
([`knowledge/21_h35_h40_results_2026-10-03.md`](21_h35_h40_results_2026-10-03.md); A3_h40_persist
mean gain +0.00048). The dense-persistence family has now failed on **two independent
implementations, on adjacent draw pairs (22/23 and 24/25), with identical gate structure** —
the family verdict (no generalizable increment over the frozen structural baseline on this
grid) is materially stronger than this document's original "unproven-at-the-bar" wording,
which is retained as written above because it was frozen with the verdict. The two
workstreams' v3 slates overlap (this file's H31b ≈ their H40; this file's H35 ≈ their H35
direction); both registers are kept for audit (`registry/hypotheses_v3_2026-10-03.json`
here, `registry/hypotheses.json` there).

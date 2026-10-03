# Why 0.2600 was the group's best, and what the arithmetic says is needed to beat 0.3195

**Date:** 2026-10-03 (UTC). **Status:** analysis of published metric definitions, locally computed
geometry facts, and a conditional model whose anchors are *owner-reported and unverified*. Every number
below is labelled **computed here**, **reported** (a claim, not a receipt), or **conditional** (derived
from reported anchors). This document contains no leaderboard access: no DrivenData page was fetched,
polled, or copied by this session.

## 1. The metric, as published

Source: DrivenData GEMS Prize problem description,
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> (transcribed in this
repository since 2026-10-02; the same transcription is implemented in `src/gemsdoe/metric.py` and was
corroborated this session against the public problem-page text returned by an independent web search and
against the organizer's own reference notebook, which trains with `TverskyLoss(alpha=0.2, beta=0.8)` —
`github.com/drivendataorg/gems-prize-reference-solution`).

```
k(d)  = max(1 - d/300 m, 0)                       triangular kernel, 300 m support (3 px at 100 m)
TP_w  = Σ_{g ∈ G} max_{x : d(x,g) ≤ R} p(x) k(d(x,g))        weighted true positives
FP_w  = Σ_{x : p(x) > 0} p(x) [1 - max_{g ∈ G} k(d(x,g))]    weighted false positives
FN_w  = Σ_{g ∈ G} [1 - max_{x : d ≤ R} p(x) k(d(x,g))]       weighted false negatives
DTI   = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)
```

Two published competition facts matter as much as the formula:

1. The test truth is **"faults that are not contained within the current public USGS database"**,
   manually identified by consulted fault experts. The initial prize round scores against that private
   set; the final round re-scores every team's *same* submission against an **expanded** label set that
   adds "previously-unknown faults that experts verify after reviewing every team's submission"
   (same page, competition-structure section).
2. Cell-level masking of the existing catalogue: two DrivenData staff statements reported by peer
   projects (2026-09-16 and 2026-09-22, quoted in the sibling `11GEMSDOE` record) say pixels
   corresponding to known USGS/INGENIOUS faults are **excluded from evaluation** (they "do not count
   towards penalty terms") and that "new fault" includes "newly mapped geometry of an existing fault
   system". *Flagged as second-hand*: these quotes are not from an official page this project has
   fetched, and a locally reproduced observation is consistent with them — the sibling project
   `8GEMSDOE` reported 0.1563 for a file with off-catalogue pixels **plus every catalogue pixel**, the
   same score as the file without them, i.e. adding catalogue pixels changed nothing.

## 2. What the formula implies (exact, no data needed)

Write `|G|` for the number of truth pixels and `p ∈ {0,1}` for a binary emission of `N` pixels. Then
`FN_w = |G| − TP_w`, so

```
DTI = TP_w / ( 0.2·TP_w + 0.2·FP_w + 0.8·|G| )            (0.2·TP_w + 0.2·FP_w + 0.8·(|G| − TP_w))
```

and the marginal value of adding one predicted pixel with credit `c` (new TP captured) and false-positive
mass `f` is positive exactly when

```
c/f  >  0.2 · TP_w / (0.2 · FP_w + 0.8 · |G|)              =: τ
```

**Computed here, by differentiating the published expression.** Three consequences:

1. **TP is a maximum over predictions.** A dot beside a dot that already covers the same truth adds no
   credit and still pays FP mass. Emission is a *covering* problem; thickness is waste. This is the
   formal reason the group's dot-thinning ladder helped.
2. **Recall dominates.** α = 0.2 versus β = 0.8, and ε-scale denominators for a sparse |G|, make τ small:
   with `|G| = 12,691`, `TP_w = 3,910`, `FP_w = 36,154` (the conditional model of §4) τ = 0.045 — i.e.
   a dot is worth emitting while its expected credit exceeds ~4.5 % of its FP mass.
3. **Catalogue-restricted evaluation changes the optimum.** If catalogue pixels are excluded, the useful
   habitat is *off-catalogue faults*: predictions on or beside the catalogue earn nothing there, so the
   whole training signal from a catalogue-trained model (which is strongest exactly on and beside the
   catalogue) is partly worthless for the score.

## 3. Why the dotted files scored what they scored — computed geometry

All three artefacts are in this checkout or in the hash-pinned mirror. `H19-5` is the parent surface
(owner-reported 0.1922); `d1.5` is its `dot_thin(·, 1.5)` transform (owner-reported 0.2477, and verified
pixel-identical to the 0.2477-labelled mirror by the sibling project); `d2.8` is the file whose content id
is `e56ea318af89`, sha256 `91eae1ca…39b8` (owner-reported 0.2600, the group's best; the only in-repo copy
is `docs/downloads/gemsdoe29-historical-d28-20261002-e56ea318af89-nan.tif`).

| file | emitted px **computed here** | % of H19-5 | kernel-captured H19-5 mass **computed here** | credit per emitted px | own 8-neighbours | reported DTI (**claim**) |
|---|---:|---:|---:|---:|---:|---:|
| H19-5 solid | 121,131 | 100 % | 100 % | — | 2.19 mean | 0.1922 |
| `d1.5` | 60,069 | 49.6 % | 82.15 % | 1.657 | 0 (all isolated) | 0.2477 |
| `d2.8` | 44,090 | 36.4 % | 73.12 % | 2.009 | 0 (all isolated) | 0.2600 |

**Computed here:** H19-5 is binary, contains **zero** catalogue pixels, and sits a median 14.6 px
(1.46 km) from the catalogue (p10 1.4 px, p90 64.9 px, max 219.3 px). Dots every ~2 px along those
lineaments buy ~1.5–2.0 lineament-pixels of kernel credit each, and the reported score rose monotonically
with *credit per emitted pixel*, not with emitted area. That is the whole story of 0.1922 → 0.2477 →
0.2600 under this metric: **fewer, better-placed dots beat more, adjacent dots**, exactly as §2 predicts.

## 4. The gap to 0.3195 — conditional arithmetic

The sibling project `GEMSDOE25` fitted a latent-truth model to 25 owner-reported score↔file pairs
(anchors **unverified**). Its selected model implies |G| ≈ 12,691 truth pixels and the D2.8 file at
credit density ≈ 0.089 per dot with ≈ 0.82 FP mass per dot. Those numbers reproduce the reported 0.2600
through the published formula:

```
TP_w = 3,910, FP_w = 0.82·44,090 = 36,154, |G| = 12,691
DTI  = 3,910 / (0.2·3,910 + 0.2·36,154 + 0.8·(12,691 − 3,910)) = 0.260      ✓ (conditional)
```

Solving the same expression for the reported leader (0.3195) at the **same** budget gives the required
credit:

```
TP_w = 4,660  →  +19 % credit at the same 44,090-dot budget
```

or, at the **same average credit density** (0.0887/dot), a larger budget:

```
N = 60,900 dots → the same conditional 0.3195        (≈ +38 % emission)
```

With perfect recall at these densities the conditional ceiling is ≈ 0.49 at ≈ 143,000 dots (beyond which
TP saturates |G|). Three levers, in the order this repository can actually implement them:

| lever | what it changes | evidence it is real | cost |
|---|---|---|---|
| **Habitat precision** (dot where truth is) | credit per dot ↑ → DTI ↑ directly | §3: score tracked credit/dot on the group's own ladder | high (new discovery physics) |
| **Coverage-optimal emission** (this session: H34) | same field, better placement + budget chosen by the τ rule | §2 marginal algebra; measured in `knowledge/09_h34_results_2026-10-03.md` | low (implemented) |
| **Budget extension under τ** | more dots while marginal `c/f > τ` | conditional model says current average `c/f = 0.089/0.82 = 0.108 ≈ 2.4 τ` | low, but unverifiable locally |

**Honest limit:** all of §4 is *conditional on unverified anchors*. The direction is nevertheless
robust because it follows from the published formula: to raise DTI you either earn more credit per
emitted pixel or emit more credit-earning pixels.

## 5. What would falsify this picture

- If the private truth is much denser than ~12.7 k pixels, budgets matter less and habitat precision
  matters relatively more (the ratio of the two levers shifts, the +19 %/+38 % equivalence does not).
- If catalogue pixels are **not** excluded (contrary to the reported staff statements), then the
  catalogue-hugging halo becomes valuable again and the sibling's "Hug the known-fault halo is not a
  supported strategy" result would need re-reading.
- If the reported 0.2600↔file mapping is wrong, §3's ladder still stands (it is local geometry), but §4's
  calibration does not.

## 6. Irregularities raised by this analysis

1. **IR-29-D28-NAMING:** the shipped file is named `d2-8` but the sibling's model text describes the
   same 44,090-pixel geometry as the `d = 2.4 px` point of its sweep. Either the file name or the sweep
   parameter is mislabelled; the bytes are unambiguous (44,090 px), the label is not.
2. **IR-29-MASKING-SECONDHAND:** the "catalogue pixels are masked" rule is reported by peers quoting
   staff, not from a page this project fetched. It should be confirmed in the official forum by the
   account owner before any submission decision that depends on it.
3. **IR-29-ANCHOR-CHAIN:** every score in §4 descends from owner-reported claims. No receipt, page
   copy, or account association exists in this repository.

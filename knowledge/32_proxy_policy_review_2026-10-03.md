# 32 — Proxy-policy review: the SGMC veto has blocked every primary-gate pass (2026-10-03)

Evidence: [`evidence/proxy_agreement_review.json`](../evidence/proxy_agreement_review.json), recomputed from the
archived raw cells by [`scripts/review_proxy_agreement.py`](../scripts/review_proxy_agreement.py). Register
entry: `IR-29-PROXY-VETO-PATTERN`. **This document changes no label, gate or candidate status.** It is a
finding placed in front of the owner for a decision, because it is about whether the repository can ever
recommend a weekly slot at all.

## 1. What was measured

The repository's promotion discipline has two local proxies:

* the **primary** catalogue-hidden DTI — the proxy with the only external anchor that exists here
  (`knowledge/17`: it reproduced the ordering of three unverified owner/user-reported historical scores,
  Spearman **+1.0** on three points; the SGMC proxy ordered the same three **−0.5**);
* the **SGMC off-catalogue class**, whose disagreement `knowledge/19` §5 declares grounds to withhold
  promotion.

Every archived raw-cell file that carries both proxies was re-read (six stages, **23 arm-stages**, draws
20/21 through 32/33). For each arm-stage the script recomputes the mean paired fold gain of the arm over its
stage's base arm, on both proxies.

## 2. What the archive says

| | count |
|---|---|
| arm-stages with both proxies positive | 6 of 23 |
| primary positive, SGMC negative | 13 of 23 |
| primary negative, SGMC positive | 3 of 23 |
| both negative | 1 of 23 |
| **arm-stages that cleared a stage's primary promotion gate** | **5** |
| **…of those, SGMC-positive** | **0** |

The five gate-passers and what the second proxy said:

| stage | arm | primary mean gain | SGMC mean gain | source |
|---|---|---:|---:|---|
| H41 screen (draws 28/29) | `A1_h41_off` | +0.00662 | **−0.00106** | `knowledge/26` |
| H41 screen (draws 28/29) | `A4_h41_union` | +0.00734 | **−0.00226** | `knowledge/26` |
| H41 confirmation (draws 30/31) | `A4_h41_union` | +0.00773 | **−0.00211** | `knowledge/26` |
| H43 screen (draws 32/33) | `A3_knick` | +0.01419 | **−0.00012** | `knowledge/30` |
| H43 screen (draws 32/33) | `A4_union` | +0.01287 | **−0.00190** | `knowledge/30` |

Three arm-stages excluded from that list on the frozen gates' own terms (they are *not* gate passes, and the
script records the reason for each): H34's `C1_geodesic_dots` is a control, not a proposal; H35/H40's
`A4_union` met the mean criterion but failed the ≥3/4-positive-folds rule (2/4 on draw 24); H43's `A1_off`
(+0.00401) missed the +0.005 mean bar.

The two largest SGMC gains anywhere in the archive come from coverage-style emissions that destroy the
primary metric (H34 `C2_coverage_rule` +0.05840 with 0/4 positive folds; `C3_coverage_binary` +0.08006 with
0/4). The SGMC class is a state-geologic-map fault population that the competition metric does not measure;
disagreement between the two proxies is therefore expected, and it is not, by itself, evidence against a
candidate.

## 3. Why this matters for the win condition

Under a rule that requires both proxies to be positive, and the further requirement that the SGMC sign hold
on ≥3/4 folds, **no candidate can be recommended for a weekly slot unless the two proxies agree — and no arm
that has ever passed the primary gate has had a positive SGMC sign.** That is not a theoretical concern: it
is the exact mechanism that withheld promotion for H41 (all four arms, both stages) and, as `knowledge/30`
§5 records, is the pattern the in-flight H43 confirmation must also confront.

## 4. Options for the owner (decision requested, none taken here)

1. **Keep the veto.** Then the honest statement is that this repository's promotion path is, so far,
   unpassable, and the H43/H41 arms remain research artifacts. Any future candidate must be designed to
   please both proxies — which the archive suggests selects against the emissions the primary rewards.
2. **Demote the SGMC proxy to a published risk flag**, keeping (a) the calibrated primary gate, (b) fresh-draw
   confirmation, and (c) the exact-file audit as the promotion requirements. Rationale: only the primary
   proxy has an external anchor, and that anchor is positive; the SGMC proxy's anchor is negative. Under this
   option the H43 `A3_knick`/`A4_union` screen (pending the frozen confirmation on draws 34/35) would be
   evaluated on the primary gate alone, with the SGMC conflict printed on the candidate card rather than
   acting as a veto.
3. **Before changing anything, preregister a proxy-calibration study** that expands the anchor set beyond
   three unverified reported scores (e.g. the owner's own submission history: the 0.2600 file and its
   siblings are in `docs/downloads/`, so their primary-proxy values can be computed and their ordering
   compared with the reported scores). This is the most conservative path and costs no submission slot.

Recommendation, stated as this repository's own judgement: **option 3 first, then option 2 if the calibration
holds** — a rule change that decides whether the project can ever submit should itself be preregistered and
anchored, not adopted mid-session because a candidate happens to be sitting at the gate. Until the owner
decides, every label in `registry/submissions.json` stays as it is and the site keeps saying so.

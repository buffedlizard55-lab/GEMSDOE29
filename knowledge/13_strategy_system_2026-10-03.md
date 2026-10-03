# The system this project now recommends to attack >0.3195

**Date:** 2026-10-03 (UTC). Companion documents: `knowledge/07_metric_emission_analysis_2026-10-03.md`
(the arithmetic of the metric and of the 0.2600 file), `knowledge/09_h34_results_2026-10-03.md`
(the coverage-emission screen), `knowledge/10_candidates_v2_2026-10-03.md` (the five geological routes),
`knowledge/12_preregistered_factorial_families_2026-10-03.md` (which features to keep).

## 1. The problem with every 0.26-class entry in one sentence

Every reported 0.24–0.26 file is the *same* habitat — the H19-5 lineament set — emitted at slightly
different dot densities, so the whole ladder
(`d1.5` 0.2477 → `d2.8` 0.2600; `h19-4` 0.1894; `h20-1` 0.1890; `h16-1` 0.1855; ridge 0.1839 — all
owner-reported) is **one discovery channel re-sampled**, and the sampling is now converged: the emission
sweep, the dot rule, and the spacing have each been optimised against the same field. The measured
evidence for convergence: the local scoreboard shows the historical file, its rebuild, and its d1.5
parent all sit within 0.01–0.02 of each other on the catalogue-hidden proxy, and the H34 coverage
re-optimisation at equal budget captured **13.9 % less** of that field than the historical dot set —
i.e. the existing emission is already near a local optimum for its habitat.

Decomposing the published metric (knowledge/07 §4): a 0.2600 file is ≈ `TP_w 3,910` with ≈
`FP_w 36,154` and `|G| ≈ 12,691`; 0.3195 needs **+19 % credit at the same budget**, or ~38 % more dots at
the same average credit density. There is no way to buy +19 % from the same field — that was tested
directly and it is negative (H34 primary gate FAIL).

## 2. The system: *calibrated off-catalogue emission with two-proxy admission*

Three components, all implementable with what is already in the repository:

**(a) Habitat = interaction-zone field (H35), not lineament magnitude.**
Score relay-ramp pairs of trace tips, terminations and transverse intersections, weighted by dilation
tendency, on the visible catalogue plus scarp/potential-field corroboration. Rationale is the one
published statistic this project keeps returning to: step-overs/relay ramps host ~32–47 % of Great Basin
systems while range-front faults host ~1 % (Faulds & Hinz 2015, GDR 383; Giddens & Faulds 2025) — the
catalogue traces the through-going strand, the missing faults live in the interaction zones around it.

**(b) Emission = *calibrated* coverage rule.** H34's coverage rule lost its primary gate for one
dominant reason: the module's `dti_hat` budget selector is blind to which parent mass is real (it read
0.51–0.68 while the realised masked DTI was 0.12) and therefore always selects the maximum permitted
budget, tripling FP mass. The correction is to *calibrate the prior scale to the expected truth mass*
before emission — the sibling latent-truth estimate (N̂ ≈ 12.7 k pixels, unverified anchors) is one such
calibration — so the marginal-τ rule stops firing after the budget where credit/dot falls to τ. Emit the
first N dots under τ, not "as many as allowed".

**(c) Admission = two proxies, opposite failures, one decision rule.** Measured here
(`evidence/candidate_scoreboard.json`): the catalogue-hidden proxy prefers the historical emission
(0.0983 vs 0.0446) while the SGMC off-catalogue proxy prefers the off-catalogue emission by 6×
(0.5615 vs 0.0953). The two proxies rank candidates almost oppositely, so a candidate must be *reported*
on both and admitted to a slot only if it beats the historical control on the **off-catalogue** proxy
(the class the competition actually scores: faults absent from the catalogue) **without** losing more
than a registered tolerance on the catalogue-hidden proxy. This is a decision rule, not a score claim.

## 3. Why this is a different system, not a re-tune

| prior work | this system |
|---|---|
| emits the same lineament field at a different spacing | changes the *habitat object* (interaction zones, not lineaments) |
| scores itself on hidden catalogue components | admits on an independent state-map off-catalogue class, reports both |
| budget chosen by an uncalibrated `dti_hat` | budget chosen by the metric's marginal rule after calibrating expected truth mass |
| one factor at a time | 2^(5−1) factorial over five feature families, with fold-block replication for error |

## 4. What would falsify the system (pre-registered intent, not run here)

1. H35's interaction-zone field adds no credit on the off-catalogue class (folds 0–3, fresh draws).
2. The calibrated budget rule still chooses the maximum budget on a dominated prior, i.e. the
   calibration does not move the τ crossing.
3. A candidate that beats the off-catalogue proxy still loses > 0.010 on the catalogue-hidden proxy —
   in which case the two proxies are measuring different expertise and *neither* should gate a slot.

## 5. Honest status

The system is **designed, partially implemented and partially tested**: H34 is implemented and has
failed its primary gate; H35 is specified (knowledge/10 Rank 1) but not implemented; the emission
calibration is specified but not fitted; the factorial over feature families (which determines which
columns the habitat model may use) is running at the time of writing. No file here is slot-approved and
no competition score is claimed anywhere in this document.

# Prior-work audit — GEMSDOE29 main history and predecessor (2026-10-03)

**Purpose.** Keep the novelty claims aligned with the repository as merged, not just with the stale branch base. This is a repository/code/evidence review; no DrivenData leaderboard content was fetched for this audit.

## Repository synchronization finding

The Arena branch was created from `ad130c8d`, when the repository contained only a one-line README. Before this branch was ready to open its PR, `main` had advanced through PRs #1 and #2. The new branch was rebased onto that latest main and the prior H29 code, evidence, and downloads were retained. The first H31 novelty review therefore needs this correction: H29 was already real-repository prior work even though it was not present in the Arena branch's original base.

## Same-repository H29 work already on main

The earlier main history implemented a Fourier upward-continuation ladder on raw RTP and isostatic gravity; horizontal-gradient maxima; cross-height nearest-edge tracking and persistence; a line-orientation audit; and four catalogue-gap proxy arms: worm gating, worm-ranked emission, persistence as model features, and residualized 2-m thermal-probe features. The frozen H29 screen found no passing arm: all four failed the `+0.005` paired-proxy bar. The raw record includes draws 2–3 for every arm, but because no screen passed they are treated as exploratory extras, not eligible confirmations; a gate-serialization bug omitted them from the original gate snapshot. The screen result and no-slot decision are unchanged; details are in `knowledge/06_h29_gate_reconciliation_2026-10-03.md`. No weekly submission slot was recommended or used. The raw-cell results and gate are retained in `knowledge/02_h29_results_2026-10-03.md`, `evidence/h29_holdout.json`, and `evidence/h29_gate.json`.

These are **spatial catalogue-gap proxy results**, not competition scores. The protocol hides components of the existing catalogue; it does not reproduce the organizer's expert-labelled hidden faults. The H29 failure does not establish that every worming or potential-field method is useless for the hidden-label target. It does establish that the tested H29 variants did not meet their frozen proxy gate, so the result lowers the prior for similar persistence features and blocks any claim that H31 begins an untested worming programme.

## What the H31 prototype does and does not add

H31's code was implemented on the stale branch before the sync. The narrow claimed increment is a regularized vertical-integration pseudogravity proxy applied to RTP, explicit lateral edge-drift features, and the associated co-location term. The H29 implementation used raw RTP directly and recorded persistence/h-last/amplitude features; it did not test this exact transform-plus-drift feature definition. H31 is therefore a **related, lower-priority extension**, not a new worming category. It remains unfitted and unscored; the H29 result is part of its prior, and H31 needs a fresh same-run spatial comparison before it can be considered further.

## Reviewed GEMSDOE25 predecessor

The public owner repository `buffedlizard55-lab/GEMSDOE25`, commit `efc4be7bb3cfdf2def12a7fb83284d3311ac9220`, was reviewed for feature registries, preregistrations, experiment scripts/raw-cell analyses, artifact registers, and documentation. It contains fixed-scale potential-field gradients, analytic signal, tilt/Hessian/ridge features; 3DEP-derived terrain/scarp descriptors; catalogue geometry; thermal/geochemical/well and volcanic-vent features; prediction thinning; single-tip continuation; H30-1 paired relay-bridge × scarp support; and H30-3 cross-profile scale persistence. A raw 1-m scarp cross-profile template is explicitly deferred. A source search found separate downface/upface inputs but no normalized opposing-face asymmetry ratio; that narrow H32 transform remains a candidate, not a verified result. The predecessor's A-family result was reported inert/negative on its catalogue-gap proxy; H30-1 failed fresh-draw confirmation. These were not recomputed here and are not competition scores.

The predecessor's historical D2.8 raster is retained only as an owner-mirrored format/reproduction example. Its score association is a user/owner-reported claim, not a verified score-to-file receipt; it is not a current recommendation.

## Other limits and consequential decisions

- H32's exact terrain-profile asymmetry ratio is distinct from earlier scarp-magnitude descriptors, but requires another line-by-line code search before implementation.
- H33's per-location acquisition-geometry control is adjacent to H29's line audit and registered spectral-notch work. Its official flight-path binaries, schema, CRS, coverage, and rights are not validated; it remains blocked.
- Do not use any prior score claim, artifact, or proxy as an official competition result. A holdout pass is only a necessary research gate, never a sufficient reason to spend a weekly slot.
- DrivenData's Terms review prohibits automatic monitoring and manual monitoring/copying without prior written consent. No such consent is recorded. A previously committed public leaderboard snapshot was removed in this PR; no polling, manual score copying, or leaderboard feed is implemented.

## Reproducibility status

The main-branch H29 raw evidence remains committed for historical reproducibility. H31's earlier feature-only smoke cache was built from a dirty worktree and has not persisted; it must not be reused. Any future H31 screen must restore and hash-check the pinned owner mirrors, rebuild caches from a clean committed source, run the frozen screen, and validate every raw cell with the independent analyzer. Report it as a catalogue-gap holdout proxy, never as a competition score.

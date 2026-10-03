# H29 corrected-screen handoff — 2026-10-03

## Current decision

The current H29 implementation uses preregistration-compliant nearest-valid FFT exterior padding and bounded persistence, `P = last_matched_level_index / (n_levels - 1)`. Its five-arm screen failed on both complete screen draws across all four spatial folds. No confirmation models were fit; a separate `--confirmation-only` invocation exited before model fitting. Do not pursue confirmation for these arms, and do not present any local proxy result as a live competition score.

The primary report is [`knowledge/02_h29_results_2026-10-03.md`](02_h29_results_2026-10-03.md), with raw rows and gates at [`evidence/h29_holdout.json`](../evidence/h29_holdout.json) and [`evidence/h29_gate.json`](../evidence/h29_gate.json). The earlier 16-row run is preserved only as historical evidence under `evidence/history/`; see [`knowledge/06_h29_gate_reconciliation_2026-10-03.md`](06_h29_gate_reconciliation_2026-10-03.md). Neither historical nor current evidence is a competition score.

## Implementation and artifact status

- Persistence is constrained to `[0,1]`; nearest-valid FFT padding is no longer overwritten by the global median. Regression tests cover both corrections, the archived gate compatibility helper, complete-fold rules, and the no-confirmation guard.
- The current WORMRANK TIFF has a local A2 gate failure. It is available for research inspection with an explicit do-not-submit note; it is not slot-approved.
- REFD28 exactly reproduces the owner-mirrored D2.8 pixel mask. The claimed `0.2600` score association remains unverified and is not authenticated by the file. The possible geometric explanation—reduced redundant dots retaining metric support—is discussed conditionally in [`knowledge/07_metric_emission_analysis_2026-10-03.md`](07_metric_emission_analysis_2026-10-03.md); it is not proof of causal score improvement.
- The main-branch HGB C0 download's method result is below the H34 C1 spatial holdout best, so that file is also explicitly not slot-cleared. No submission slot has been spent. See `registry/status_feed.json` and `registry/submissions.json`.
- The site downloads are single-band, float32 GeoTIFFs checked against the hash-pinned owner-mirror template. The site labels each file's current eligibility and provides its short Note; local format validation does not imply organizer acceptance.

## Reproduction boundaries

H29/core rasters are hash-pinned in `data/manifest.json`. `python scripts/restore_data.py --verify` checks the local restore; the legacy H29 restore writes under checkout `data/` and does not honor `GEMS_DATA_DIR`. The separate H31 restore has its own manifest and environment paths. Do not commit restored data. No DrivenData endpoint, upload, or automated leaderboard access was used.

## Final verification recorded in this integration

- Full local test suite: 112 passed.
- Ruff: passed.
- All 11 core data-manifest entries: SHA-256 verified.
- Both H29 TIFF/ZIP packages: 28 independent checks each, zero failures.
- All five registered downloadable TIFFs: local submission-format checks passed against the restored owner-mirror template.
- Generated Pages build and offline link/status check: passed.

These checks establish code, evidence-integrity, local-format, and site consistency only. They do not validate any competition score or authorize a slot.

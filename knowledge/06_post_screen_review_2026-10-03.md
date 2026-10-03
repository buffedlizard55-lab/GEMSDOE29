# Post-screen review and three-pass record — 2026-10-03

## Decision and scope

The current preregistered screen uses the corrected nearest-valid FFT exterior fill and bounded six-level persistence. All five arms fail. H29-5 was −0.078939 and −0.087032 mean paired catalogue-proxy ΔDTI against the best same-fold/same-draw control, with 0/4 positive folds on each screen draw. A1/A2/B1/B2 also fail the +0.005 screen gate. Confirmation draws 2/3 were not fit; a direct `--confirmation-only` recheck exited safely because no arm passed. No weekly slot was spent, no DrivenData endpoint was accessed, and no upload was made.

`WORMRANK` is a locally format-verified research artifact, not submission-eligible under its A2 proxy gate. Current stem: `gems29-wormrank-d28-20261003-59dcaf6dd11d`; 41,338 positive pixels. `REFD28` reproduces the owner-mirrored D2.8 **pixel mask** (44,090 positives); its GeoTIFF bytes differ, and its association with the owner-reported 0.2600 public-column value is unauthenticated. It is a duplicate and must not be resubmitted.

## Pass 1 — implementation and verification

- Corrected persistence normalization is `last_matched_level_index/(n_levels-1)`, bounded [0,1]; amplitude retention remains separate in [0,2].
- Preserved the preregistered nearest-valid padding through FFT preparation. The six-level p95 edge screen completed over two draws and four spatial folds (566.0 seconds). Current H29-5 results are in `evidence/h29_holdout.json`; per-arm gates are in `evidence/h29_gate.json`.
- Worming receipt reports magnetic/gravity mean P 0.485/0.302, level-0-only fractions 17.1%/58.7%, full-ladder fractions 17.3%/19.1%; E–W/N–S/other magnetic strike means are 0.540/0.447/0.491. This is a descriptive strike audit, not a spectral test.
- Candidate packaging produced a uniquely named one-band float32 GeoTIFF, ZIP, zero-outside alternative and build receipt. The current note is `GEMSDOE29 WORMRANK | d2.8 spacing, corrected persistence+ridge rank | A2 gate=FAIL proxy only | 59dcaf6dd11d | live-unverified`.
- The current WORMRANK and REFD28 artifacts are checked independently against build-time hashes and the pinned competition grid. Local checks are format evidence only, not portal acceptance.
- The website is generated from evidence/registry JSON; its home page links the exact current TIFF and note, displays the holdout result and no-slot recommendation, and states source/acceptance limits.

## Pass 2 — bug and edge-case review

The second review caught one more scientific implementation defect after an earlier bounded-P screen: `prep_field` computed nearest-valid exterior padding, then a subsequent `np.where` silently replaced those cells with the global valid-cell median. This contradicted the frozen preregistration and changes Fourier continuation near the footprint boundary. The code now preserves nearest fill, with a regression test that distinguishes nearest from median padding. The intermediate bounded-P results, ledger and WORMRANK files were copied byte-for-byte with SHA-256 to `evidence/history/pre_nearest_fill_2026-10-03/` and removed from public downloads. They are explicitly marked invalid for the preregistered boundary treatment. Worming and all eight screen rows were recomputed after the fix; all arms still fail.

Other reviewed risks and fixes:

1. The original persistence denominator divided by `n_levels-2`, allowing P=1.25. It now divides by `n_levels-1`; runtime bounds and tests prevent recurrence. Earlier P>1 evidence/downloads are separately archived under `evidence/history/pre_correction_downloads/`.
2. The former gate searched its screen-only mapping for confirmation draws 2/3, making confirmation invisible. Its first repair also incorrectly required both confirmations; the registered rule requires at least one complete passing draw. The gate now validates exact unique fold IDs and finite deltas, requires both passing screens and accepts any one complete passing confirmation; missing incomplete data cannot create a pass.
3. The prior script default could fit confirmation models before evaluating the screen. Default is screen-only; `--confirmation-only` verifies saved matching protocol evidence and a passing arm first. The current failed screen was exercised and skipped without fitting.
4. The prior download verifier could overwrite build-time hashes after a mismatch. It now preserves immutable build hashes, logs observed hashes separately, and regression-tests repeated mismatch failures.
5. A stale pre-correction TIFF/ZIP could remain linked publicly. Both superseded WORMRANK sets are archived with hashes; only the current nearest-fill, bounded-P artifact remains in public downloads.
6. Website artifact facts now come from JSON receipts/registries; current checks validate linked artifact checksum and show note/status rather than implying portal acceptance.

## Pass 3 — full recheck against the request

Final checks after the nearest-fill rerun: `.venv/bin/python -m pytest -q` **34 passed**; `compileall` and `git diff --check` passed; strict JSON parsing passed for 11 current registry/evidence/download-receipt files; `scripts/restore_data.py --verify` reported all 11 rasters/archives verified; `scripts/verify_downloads.py` passed 28 checks each for WORMRANK and REFD28 with zero failures; `scripts/build_site.py` and `scripts/check_site.py` returned **OK**. `--confirmation-only` was exercised against the current failed screen and printed that model fits were skipped. No competition automation/upload is part of this workflow.

## D2.8 interpretation and next work

The pinned owner-reported parent/D1.5/D2.8 sequence is 121,131 / 60,069 / 44,090 positive pixels and public-column scores 0.1922 / 0.2477 / 0.2600. The mask reproduction verifies local geometry only. The official metric's 300 m continuous distance support and recall-heavy α=0.2, β=0.8 make a budget-spacing explanation plausible: 2.8 pixels is 280 m, and the midpoint between dots on a straight trace is about 140 m away, retaining roughly 0.53 of the linearly weighted credit. This is consistent with the reported trend, not proof of causation or score-to-file association; secret labels and a receipt are unavailable.

Next experiments require separate preregistration: measure H29-3's predicted flight-line spectral peak before any notch, or develop H29-6's fixed-scale curvature/junction test. A stronger source of holdout truth for faults missing from the catalogue remains necessary. H29-4 stays blocked until the official GDR 1391 archive is accessible and hash-verified. Do not spend a slot without a passing frozen gate.

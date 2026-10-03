# Pre-run implementation audit — corrections required before the next holdout run

**Audit frozen 2026-10-03 before the corrected worming/H29-5 rerun.** Findings below were determined by reading this repository's implementation and checking the cited primary-source records. The historical results are retained; they are not silently edited or presented as corrected results.

## Blocking scientific / evaluation defects

1. **Persistence normalization is off by one.** `src/gems29/worming.py::worm_persistence` divided the last 0-based level index by `len(edge_levels)-2` for the six-level ladder. The pre-registered definition is `last_level_index / (number_of_levels - 1)`. With six levels, the old code could write `P=1.25`, not a value in `[0,1]`. It also changes A1's 0.5 cutoff and clips/saturates the highest A2 ranks. Therefore the old worming persistence rasters and H29 A1/A2/B1 comparisons are **invalid for the registered method** and must be regenerated; the old evidence files will be preserved as pre-correction history.
2. **Confirmation draws were not included in the gate summary.** The previous holdout JSON contains raw rows for draws 0–3, but the aggregation loop wrote only draws 0–1 into `per_draw` and then searched that two-draw mapping for draws 2–3. Thus `confirm_draw` was structurally impossible to populate and `PASS` was structurally impossible. Recompute the gate from all four draws and add unit tests before any new result is used.
3. **The registered amplitude-retention statistic was not written to disk.** It was calculated in memory but omitted from the rasters list and feature loader. Persist it (separately from persistence P) or stop claiming it was stored.
4. **The acquisition-line audit documentation overclaimed its calculation.** It returned mean persistence grouped by strike, but its docstring promised frequency-band energy ratios that were never calculated. Correct the docstring and keep spectral-notch measurement as a separately registered experiment.

## Source / documentation defects

5. **Hornby et al. DOI mismatch.** The project cited `10.1046/j.1365-246X.1999.00793.x`; Crossref resolves that identifier to a different article. Oxford Academic's publisher record and the Stanford review support the correct Hornby–Boschetti–Horowitz article DOI `10.1046/j.1365-246X.1999.00788.x`. Replace every bad DOI; retain this audit trail.
6. **Source-table claims were hidden.** `scripts/build_site.py` asked the JSON record for the literal key `"'claims'"`, so the live page printed `-` rather than the recorded claim summaries. Read the actual `claims` field and test that it renders.
7. **The local format checker was not as strict as its prose.** Strengthen it to reject infinities, verify all in-footprint values are finite and in `[0,1]`, check the required NaN/zero outside convention, compare the full grid profile against the pinned template, and ensure the ZIP contains exactly one matching GeoTIFF. A local pass still cannot authenticate the owner mirror or guarantee the organizer portal accepts it.
8. **`scripts/restore_data.py` could not restore the stated split stack.** The manifest names were `part-000` while the pinned public sibling blobs are named `gems-geodawn-numerical-features.tif.part-000`, and the script had no exact per-part remote path. Data were absent at the start of this run. Pin exact source paths, use atomic downloads, verify every part and final stack, and re-run the restore.
9. **The source page generator needs a link audit that includes single-quoted `href`s.** The old `check_site.py` only checked double-quoted links and therefore skipped some generated source-page links.
10. **Submission copy overclaimed acceptance.** A file can be shown locally to satisfy the pinned template checks, but the competition data mirror is not organizer-authenticated and portal validation is not public. Wording must say “locally format-verified / designed to avoid the reported range failure,” not “cannot raise” or “guaranteed accepted.”

## Action / historical handling

- Preserve `evidence/h29_holdout.json`, `evidence/h29_gate.json` and `evidence/worming_receipt.json` under explicit pre-correction names before replacing the primary pointers.
- Correct code, add unit tests for bounded persistence and draw-2/3 gate aggregation, restore the pinned owner-mirror data, and regenerate all primary evidence from the corrected implementation.
- No weekly slot has been spent. No historical owner-reported live score is upgraded to an organizer receipt by this audit.

## Addendum — second review found a boundary-fill mismatch

During the full second-pass bug review on 2026-10-03, `prep_field` was found to nearest-fill invalid cells and then replace them with the global median via `np.where`. This contradicted the preregistered FFT boundary treatment. The median overwrite is removed and a regression distinguishes nearest from median padding. The bounded-P screen/artifact generated before this fix is archived with hashes in `evidence/history/pre_nearest_fill_2026-10-03/`; it is not current evidence. Worming and all eight screen rows were recomputed with nearest-valid fill; current measurements and failed gates are in `evidence/worming_receipt.json`, `evidence/h29_holdout.json`, `evidence/h29_gate.json`, and `knowledge/02_h29_results_2026-10-03.md`. The staged confirmation command was re-run and skipped model fitting because no arm passed.

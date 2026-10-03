# 31 — Session-5 note: the data blocker, the emission-density result and the H43 execution record (2026-10-03)

This is the note the session-5 site cards link. It records three things that happened after the session-4 H41
close-out, with the exact commands and hashes needed to re-check each one:

1. the standing "competition data" blocker was closed locally with a script-written placement receipt;
2. the frozen emission-density sweep finished and returned a *negative* result (keep the pinned artifact);
3. the H43 screen had to be quarantined and re-run after an out-of-memory kill and a cached-input drift.

Everything below is a local, hash-checked statement. **No score in this document is a competition score.** The
owner-mirrored inputs are byte-pinned to owner repositories, not organizer-authenticated
(`IR-DATA-01`); every proxy number is a spatial proxy computed inside this repository.

## 1. The data blocker, closed with a receipt

The original brief's open item was that the DrivenData data page requires a login. The repository's answer is
the owner-mirror restore path — it never contacts DrivenData (policy review: `knowledge/03`, `AGENTS.md` rule 3):

```bash
bash scripts/download_competition_data.sh          # restores + hash-verifies the H31-group mirror set
python scripts/prepare_data.py                     # aligned footprint/label/band caches
python scripts/build_features.py                   # 64-column static block  -> data/work/static_ABCD.npy
python scripts/build_addons.py                     # S/G/E/H27 add-ons      -> data/work/addons.npy
python scripts/record_data_placement.py            # writes the receipt (add --check to only re-verify)
```

Verified in this checkout on 2026-10-03 (UTC):

| what | value | where it is recorded |
|---|---|---|
| owner-mirror files present and byte-correct | **11 / 11** (`training_features.tif` `4371c82e…`, `labels.tif` = `existing_faults.tif` `7ba308cc…`, `sample_submission.tif` `2176d08e…`, LiDAR `d580bb8b…`, GeoDAWN `c22420f7…`/`a35a9c6d…`, SGMC `643cbe99…`, GDR `122718e6…`/`9702f2e5…`/`f91bafba…`) | `registry/data_manifest.json`, restore stdout |
| prepared bars | footprint **5,167,373 px**, catalogue **60,988 px**, **19** aligned band arrays | `evidence/data_placement_receipt.json` |
| derived caches | `static_ABCD.npy` `fe584a12…` (1,322,847,616 B), `addons.npy` `ad31ff14…` (103,347,588 B) | same receipt |
| coverage of the pinned manifest | **22/22** entries (h31 group 11/11, core group 11/11) | same receipt |
| preparation time | 51.5 s for `prepare_data.py` (19 bands, 3730 × 3292 float32) | session console, reproducible |
| organizer authentication | **false** — the mirrors are not the organizer's bytes | receipt field `organizer_authenticated` |

The receipt is re-checkable without rewriting anything:

```bash
python scripts/record_data_placement.py --check     # exit 0 == every pinned file still byte-correct
```

With those arrays in place the train → inference → validate path is runnable end to end on a machine with
enough memory and (optionally) a GPU; the screens in this repository fit a 2-core / 3.9 GB container only in
staged pieces, which is exactly what item 3 below is about. `scripts/check_submission.py` validates any
produced GeoTIFF against the pinned template (one `float32` band, EPSG:32611, 100 m, values in [0,1], NaN
outside the footprint) — this is the check that answers the earlier rejection
"Predicted values must be in range [0, 1]".

**What this does *not* claim.** These are owner mirrors restored from public sibling repositories, verified
byte-for-byte against recorded SHA-256 pins. They are not organizer-authenticated downloads, and no result
computed from them is an official score. That limitation is registered as `IR-DATA-01` and is repeated on the
site.

## 2. Emission-density sweep — the result is "do not re-space the pinned artifact"

Frozen protocol: [`knowledge/27`](27_preregistered_emission_density_sweep_2026-10-03.md).
Full result: [`knowledge/28`](28_emission_density_sweep_results_2026-10-03.md).
Evidence: `evidence/emission_sweep/{design.json,rows.jsonl,summary.json}`.

Fifteen deterministic rows, no model fitted, no holdout draw spent, all scored with the two registered
file-level proxies. Headline numbers on the primary `catalogue_hidden` proxy (4 folds × draws 20/21):

* calibration ladder reproduced in the same order as the reported live ladder —
  solid **0.06970** < d1.5 **0.09449** < d2.8 **0.09832** (calibration check **PASS**);
* the pinned d2.8 artifact is the **maximum** of the family; every denser and every sparser row is worse
  (denser: −0.00383 … −0.02862; sparser: −0.00280 … −0.02672);
* the score-aware placement variant is also worse at its own best spacing (−0.00433), so
  score-ordered dotting is not a free improvement here;
* the frozen rule returns `admissible: []` and `recommendation: "cal_d2_8 (keep the pinned artifact)"`,
  with `recommendation_is_boundary: false` — i.e. the optimum is interior, which licenses stopping.

Two side findings, both registered: the spacing parameter is quantised by an integer disc
(`thin_2.0` ≡ d1.5 and `thin_2.4` ≡ d2.8 are pixel-identical, `IR-29-SPACING-QUANTISATION`), and the
historical "d2.8" file name is a naming artefact of that quantisation (`IR-29-D28-NAMING`, medium severity,
content id `e56ea318af89` is the unambiguous identifier).

Consequence for the weekly slot: **none**. The sweep cannot clear the slot rule because that rule requires
beating the same-run H34-cell holdout control (0.14479), and this sweep fits no model. Its value is that it
closes the "just thin it more" hypothesis with a measured curve instead of an assumption.

## 3. H43 execution record — an OOM kill, a cache drift, and the honest response

The frozen H43 screen (`knowledge/29`) was launched from commit `a244032`; it was killed by the kernel OOM
killer after 23 of 40 rows (cells `NW:32`, `NW:33`, `NE:32`, `NE:33` complete; `SW:32` missing two arms).
The container has 3.9 GB; the process peaked at `total-vm:5463148kB, anon-rss:3661016kB`.

Resuming was attempted and correctly *refused*: the resume guard re-hashes every input recorded in
`design_screen.json`, and the cached `work/bands/12_det_elev.npy` no longer matched its recorded hash
(`caa50bf75e99d58a…` recorded, `739d6373125abf16…` present). The present file is exactly what
`src/gemsdoe/prepare.py` produces from the pinned `data/training_features.tif` band 12 (re-read and compared
element-wise: zero differing values, identical NaN mask, 7,113,308 NaN cells), so the *recorded* array is the
non-reproducible one. Mixing the two arrays inside one frozen design would be silently dishonest, so:

* the 23 rows, the original design file and the stale log were **quarantined** — not deleted — under
  `evidence/history/h43_screen_oom_partial_2026-10-03/` with a README that carries the hash table above;
  they are historical and must never be summarised or gated as the H43 result;
* the runner gained a verified `--resume`/`--cell`/`--max-cells` path that re-checks the frozen
  preregistration, module and input hashes before appending any row (commit `0d1138d` and follow-ups);
* the screen was **re-run from scratch** on the same frozen preregistration with the current reproducible
  caches, staged into several processes of two cells each so a single process cannot exceed the container
  limit.

The staged execution is a compute-environment workaround, not a protocol change: draws (32/33), folds,
arms, seeds, gates and the preregistration hash are unchanged. It is disclosed as
`IR-29-H43-STAGED-EXECUTION`. Results — including the gate arithmetic recomputed from the raw rows by
`scripts/analyze_h43_screen.py` — are in [`knowledge/30`](30_h43_drainage_results_2026-10-03.md).

## 4. Verification performed in this session (so the next session need not redo it)

| check | command | outcome |
|---|---|---|
| mirrors still byte-correct | `bash scripts/download_competition_data.sh` | 11/11 present, hashes printed and matching the manifest |
| arrays reproducible | `python scripts/prepare_data.py` | footprint 5,167,373 / labels 60,988 / bands 19, 51.5 s |
| placement receipt | `python scripts/record_data_placement.py --check` | problems `[]` |
| unit tests | `python -m pytest -q` | 162 passed |
| lint | `ruff check src scripts tests` | clean |
| site build | `python scripts/build_site.py && python scripts/check_site.py` | pages written, `check_site: OK` |
| sweep regression | `scripts/run_emission_sweep.py` reference row | reproduces `evidence/candidate_scoreboard.json` to the last digit |
| D2.8 input hash | `data/inputs/dotted_h19_5_d2_8_nan.tif` | `91eae1ca42ec845e…` (matches `knowledge/27` §2 and `evidence/d28_geometry.json`) |

## 5. Limits carried forward (not resolved here)

* Everything is an owner mirror; nothing is organizer-authenticated (`IR-DATA-01`).
* All proxies are spatial proxies; the private expert-labelled test set has never been seen, and no number in
  this repository other than an owner-reported leaderboard value is a competition score.
* The 0.2600 / 0.2477 / 0.1922 ladder is a set of unverified owner/user claims; the emission sweep can only
  say that *if* those associations are right, the proxy ranks them correctly and the ladder is converged.
* No weekly slot has been used. The slot rule is unchanged: beat `0.14479018210246675` on the same-run
  H34-cell holdout protocol, pass the frozen gates, then pass the exact-file audit and human review.

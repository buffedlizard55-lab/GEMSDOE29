# H43 screen — quarantined partial stage (2026-10-03)

This directory preserves the first H43 screen attempt, byte-for-byte, and records why it is **not** part of the
H43 result. Nothing here was deleted and nothing here was edited.

## What the files are

- `design_screen.json` — the design record written by `scripts/run_h43_screen.py` from commit `a244032`
  (git revision recorded in the file), with the SHA-256 of the frozen preregistration (`knowledge/29`), of the
  five modules and of every input array.
- `cells_screen.jsonl` — 23 of the 40 raw cell rows. Cells `NW:32`, `NW:33`, `NE:32`, `NE:33` are complete
  (5 arms each); `SW:32` holds `C0_base`, `A1_off`, `A2_network` only.

## Why it stopped

The screen ran as a background process under a 3.9 GB container and was killed by the kernel OOM killer during
the fifth cell (`SW:32`, arm `A3_knick`):

```
[2008.230748] Out of memory: Killed process 9762 (python3) total-vm:5463148kB, anon-rss:3661016kB, ...
```

No summary file was ever written, so no gate was evaluated on these rows.

## Why it was quarantined instead of resumed

`scripts/run_h43_screen.py --resume` re-verifies every hash recorded in `design_screen.json` before appending a
row. Re-checking the pinned inputs on 2026-10-03 after the kill gave:

| input | recorded sha256 (screen start) | hash at re-check | verdict |
| --- | --- | --- | --- |
| `data/sample_submission.tif` | `2176d08e485a…` | `2176d08e485a…` | same |
| `data/labels.tif` | `7ba308ccdc44…` | `7ba308ccdc44…` | same |
| `data/external/derived_sgmc_faults_100m_u8.tif` | `643cbe992ef4…` | `643cbe992ef4…` | same |
| `work/bands/_footprint.npy` | `c44609477177…` | `c44609477177…` | same |
| `work/bands/_labels.npy` | `d77fa88ad58d…` | `d77fa88ad58d…` | same |
| `work/bands/12_det_elev.npy` | `caa50bf75e99…` | `739d6373125a…` | **differs** |
| `work/static_ABCD.npy` | `fe584a12ed3e…` | `fe584a12ed3e…` | same |
| `work/addons.npy` | `ad31ff14a804…` | `ad31ff14a804…` | same |

The present `12_det_elev.npy` is exactly what `src/gemsdoe/prepare.py:prepare_inputs` produces from the
hash-pinned `data/training_features.tif` (band 12 re-read and compared element-wise: 0 different values,
identical NaN mask, 7,113,308 NaN cells). The recorded array therefore cannot be regenerated from the pinned
inputs, and appending new rows to those 23 would mix two different elevation arrays in one frozen design.
The honest options were to discard or to preserve; this repository preserves. **These 23 rows must never be
summarised, gated or quoted as the H43 result.**

## What replaced it

The screen was re-run from scratch on the same frozen preregistration (`knowledge/29`, unchanged hash) with the
current, reproducible caches, staged into several OS processes of two cells each so that a single process cannot
exceed the container limit. The live evidence lives in `evidence/h43_screen/`; the staged execution mode is
disclosed as `IR-29-H43-STAGED-EXECUTION` in `registry/irregularities.json` and in `knowledge/30`.

# Superseded median-padding screen and artifact snapshot

This complete intermediate result set used the corrected persistence normalization but did **not** implement the pre-registered nearest-valid FFT padding faithfully: `prep_field` subsequently replaced nearest-filled cells with the global median. Although the screen failed, it is invalid for the registered boundary treatment and is archived rather than silently retained as current evidence. Do not use its metrics or WORMRANK output for a slot decision. The corrected method has now been fixed to preserve nearest-valid filling; a new worming receipt, spatial screen, artifact build, and site are being generated.

Archived original files and SHA-256:
- `evidence/history/pre_nearest_fill_2026-10-03/worming_receipt.json` — 3,502 bytes; SHA-256 `a25ac9c02ab17c9b30ceaa6026b4126732a017ce93b38f8ab1c6afd4b3984112`.
- `evidence/history/pre_nearest_fill_2026-10-03/h29_holdout.json` — 29,923 bytes; SHA-256 `8e9d6caa9aa9a76a06033dc97967844cd97490370ed9e98c20cfe5fa1d490b1f`.
- `evidence/history/pre_nearest_fill_2026-10-03/h29_gate.json` — 10,262 bytes; SHA-256 `88c3e4953d1c4bf098dc0ce13bb8867c4de82233bf3387014d5da2c8517f594c`.
- `evidence/history/pre_nearest_fill_2026-10-03/artifact_ledger.json` — 17,205 bytes; SHA-256 `4d7a9497eed1b84252e73d33a81b6305b3069ff96419b7b5726fa85d02d14c49`.
- `evidence/history/pre_nearest_fill_2026-10-03/knowledge_02_h29_results.md` — 7,938 bytes; SHA-256 `f9a96a04892831af1cc6d35ec7f33a3db9c5027985091f35097f818395e68187`.
- `evidence/history/pre_nearest_fill_2026-10-03/downloads/checks-wormrank-b4643d3622d5.json` — 6,211 bytes; SHA-256 `4d7126fb07e9f414d35d48baa42f0cbaaaaed74e79a6a83596020f22388dd2f0`.
- `evidence/history/pre_nearest_fill_2026-10-03/downloads/gems29-wormrank-b4643d3622d5-nan.tif` — 1,567,806 bytes; SHA-256 `fed135479141ac7d1e3768139fddce6dc564374b82585831f7325c8ec9e37dc0`.
- `evidence/history/pre_nearest_fill_2026-10-03/downloads/gems29-wormrank-b4643d3622d5-nan.zip` — 311,934 bytes; SHA-256 `3e393e81c5a88f68b199b23d1c163b43a1fa2336875176c61ecc0f068fbb80c0`.
- `evidence/history/pre_nearest_fill_2026-10-03/downloads/gems29-wormrank-b4643d3622d5-zeros.tif` — 801,692 bytes; SHA-256 `88e71d57c5792dcc8d02b7cdd913874f96bb21d2f57fc506623143ab8e591f5d`.

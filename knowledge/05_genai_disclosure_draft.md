# Draft generative-AI disclosure for a future submission narrative

The GEMS Prize rules (official rules §3.2) require the competitor to disclose the extent of generative-AI
use in the narrative when applicable. This project used Arena.ai Agent Mode (a multi-model coding agent;
the underlying model family varies per session) to help inspect repository history, review official and
scientific sources, compare and document hypotheses, write/refactor research code and tests, run the
locally verified spatial-holdout screens, and prepare project documentation and the public Pages site.
Specifically, generative-AI assistance covered:

* source verification work (reading the competition rules/problem page transcriptions, DOI metadata checks
  for Hornby/Boschetti/Horowitz 1999, Bellier & Zoback 1995, GDR 1391/1391-INGENIOUS, Siler 2022,
  Peacock & Bedrosian 2022) and transcription of constraints into `registry/sources.json`;
* deterministic signal-processing code (worming/persistence in `src/gemsdoe/worms.py` and
  `src/gemsdoe/dense_persist.py`, interaction-zone corridor construction in `src/gemsdoe/h35.py`,
  thinning and emission in `src/gemsdoe/thinning.py`/`ridges.py`) plus tests and screen runners;
* the frozen preregistrations (`knowledge/19_*`, `knowledge/01_*`) including gate constants, and the
  negative-result writeups (`knowledge/02`, `knowledge/06`, `knowledge/15`-series);
* site generation (`scripts/build_site.py`), local format checks (`scripts/check_submission.py`), and the
  geometry receipt script (`scripts/audit_d28_geometry.py`).

All fitted predictions are produced by the declared scikit-learn models (`HistGradientBoostingClassifier`
with the recorded frozen parameters) on explicit training data recorded in the evidence JSONs — not by an
LLM at inference time. All model inputs are the hash-pinned competition and mirrored public rasters/CSVs
recorded in `registry/data_manifest.json`. No leaderboard content was scraped or used.

The owner remains responsible for: choosing whether any artifact is submitted; the manual upload on
DrivenData; verifying all scientific interpretations against the cited literature (the agent is not an
independent scientific authority); and confirming current rules/deadlines. Do not state that results,
rights, or scientific interpretations were independently verified unless that review has actually
occurred. Before any final submission this disclosure must be updated to identify the exact code
version/commit, the final artifact name and hash, and the actual verification steps performed by the
human competitor at that time.

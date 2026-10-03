# Agent notes (GEMSDOE29)

1. FIRST ACTION every session: read `README.md` in full (Project Charter + Core Values). Then the newest dated
   file in `knowledge/` and `evidence/h29_gate.json`.
2. Data is restored + hash-verified by `python3 scripts/restore_data.py`; large rasters are gitignored — never
   commit `data/`.
3. Never contact drivendata.org programmatically (ToS). Submission uploads are the owner's action, with the
   site's Note text.
4. Every number that reaches the site must come from a JSON under `evidence/` or `registry/` written by a script;
   regenerate pages with `python3 scripts/build_site.py` after experiments.
5. New predictive ideas must be pre-registered (gate written BEFORE results, like `knowledge/01`) and pass the
   frozen holdout gate before any file is labelled slot-recommended. Proxy pass ≠ live evidence (documented).
6. Irregularities go to `registry/irregularities.json` with severity + action, and are surfaced on the site.
7. Three-pass review before finishing any task (implement → bug-review → full recheck).

# Limitations and next-session plan (session 3 close-out, pass 3)

## What is finished and verified as of this merge

* Full repo review pass; 123 tests pass; ruff clean; site builds and `scripts/check_site.py` is green.
* Session-3 pipeline complete: pre-registration (`knowledge/19`, frozen before any fit) → implementation with
  tests → H40 cache → 40-cell screen (draws 24/25, clean tree) → independent raw-cell gate recomputation →
  results doc (`knowledge/21`) → registry/status/site/README updates → PR #7 merged to main.
* The why-0.2600 emission geometry (knowledge/07 §3) was re-derived byte-exactly from the mirrored rasters
  (`scripts/audit_d28_geometry.py` → `evidence/d28_geometry.json`).
* Every Pages number originates from script-written evidence/registry JSONs. No score values appear on
  public pages (checker-enforced). No DrivenData access of any kind was made.

## Scientific status (honest)

1. **The feature-adding program is in a strong negative streak.** H29 (five arms), H31 (seed-tracked
   persistence), H34 (coverage emission) and now H35/H40 (four arms) all fail the same +0.005 paired-mean
   gate on identical folds. The best-ever arm (A4 union, +0.00562) is rejected only by the fold-robustness
   rule. This is evidence that the frozen baseline already saturates the *potential-field + terrain +
   catalogue-geometry* information in this grid — not that geophysics is useless.
2. **Proxy ≠ score.** All screening truth is catalogue-gap/SGMC proxies; the organizer labels are expert
   additions (incl. new geometry on existing systems) we cannot see. The A4 near-miss could mean the gate is
   conservative relative to the real metric, or that the gain is fold noise. We deliberately cannot
   distinguish these locally, and moving the gate after seeing results is prohibited by the amendment rule.
3. Owner-mirrored data is not organizer-authenticated; if mirror bytes differ from the real competition
   bundle, every proxy result shifts (all hashes are pinned so drift is detectable).

## Remaining work, in priority order, for the next session

1. **H41 screen (v3 rank 1)** — slip-rate-weighted INGENIOUS off-catalogue centroid corridors
   (`data/external/gdr_qfaults_traces.csv`, local + hash-pinned; centroid-only ceiling documented). Needs:
   preregistration (new file, draws 26/27 + 28/29 proposed), feature builder `h41.py`, emission-corridor
   variant using the *existing* `h35.py` strike-smearing machinery, then the identical gate chain. This is
   the only candidate whose information source is label-side (newly mapped geometry), so it has the highest
   prior of beating the baseline per unit work (~0.5 day).
2. **Weekly-slot decision rule stays armed:** nothing in `registry/submissions.json` is slot-approved; the
   lead artifact remains `…a4d439b07426-nan.tif` (format-valid only). If the owner chooses to use a slot
   anyway for *feedback* purposes, the manual guide on the site is current; the repository continues to
   recommend against spending a slot below the H34-C1 holdout best (0.14479 proxy).
3. **H36/H37/H42 implementations** as each is preregistered (v3 doc has the full spec, cost and falsifier
   budget). H33 remains blocked on the unfetchable GeoDAWN flight-path binary; the H42 measured-period
   variant needs no external data and can absorb it.
4. **Robustness upgrade worth considering before new features:** re-estimate A4 (union) on *different*
   folds/draws as a pure replication receipt (no gate changes) — if it repeats its mean-gain ≥ +0.005 on
   8/8 folds it becomes the strongest candidate ever for a fresh confirmation-stage preregistration; if it
   does not, the fold-concentration reading is confirmed and the interaction-zone family closes cleanly.
5. Housekeeping: `work/h40_dense_persistence.npy` is regenerable (25.6 s) — no need to archive; consider a
   tiny CI step that runs `scripts/check_site.py` after Pages builds (it is currently only run manually).

## Standing limitations (do not "fix" by assertion)

* Sandbox cannot reach gdr.openei.org/doi.org binaries (TLS restrictions) — GDR 1391 full trace geometry and
  the flight-path binary must be owner-fetched; metadata verified in prior sessions stands.
* Memory ceiling (~3.9 GB) bounds screen design: 5 concurrent fits at 1.29M×91 float32 is the tested limit;
  a 6th arm or a 5th draw per fold risks OOM and should run as two staged invocations.
* HistGradientBoosting `random_state` is the only seed handle; emission is deterministic given scores, but
  dot-set ordering ties are resolved by `score_ordered_dots` raster order — documented, not worth changing.
* Gates use strict float comparisons at the threshold (no epsilon) — inherited, conservative, documented in
  `knowledge/21` §3.
* The site feed's `draw_inventory` is prose, not a database; a future session that adds draws should add a
  structured registry file and a test rather than more strings.

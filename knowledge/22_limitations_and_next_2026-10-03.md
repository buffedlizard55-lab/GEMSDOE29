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

---

## Session-4 disposition of this list (appended 2026-10-03, the text above is left as written)

*Standing limitations, as they now read.*

1. **The negative streak is broken, once, narrowly.** Six screens have now been run against the frozen ±0.005
   gate; H41 is the first with arms that pass (`A1_h41_off` +0.0066173, `A4_h41_union` +0.0073436 on 40 cells,
   `knowledge/26`). The other four screens still failed, and H41's gain is +0.0066 against a bar of +0.005 — it
   clears, it does not dominate. Nothing about the streak's cause changed: the win came from a *label-side*
   channel (an independent young-fault inventory), not from a better filter on the same fields.
2. **Proxy ≠ score is now load-bearing, not rhetorical.** H41 is the first feature whose two proxies disagree in
   *direction*: +0.0066 on the catalogue-hidden target, −0.0009 to −0.0023 on the SGMC off-catalogue class. The
   registered conflict (`IR-29-PROXY-CONFLICT`) can no longer be treated as a tie-break detail; a submission
   decision that reads only the primary proxy would be reading one of two disagreeing measurements.
3. **Owner-mirror status:** unchanged, and now more consequential — `data/external/gdr_qfaults_traces.csv`
   (sha256 `9702f2e5…`) is a hash-pinned owner transcription, not an organizer file, and it is the input the
   first passing feature depends on. If the mirror's slip-rate or age-bin values differ from the real release,
   H41's gain is unreproducible in exactly the way that cannot be detected from inside this repository.

*The next-step list.*

1. **H41 screen — done** (this session, frozen protocol, evidence in `evidence/h41_screen/`, analyzer zero
   problems). The follow-on that *this* list asked for also happened: `H36/H37/H42` were not silently retried,
   and the worming family was explicitly closed with a written reason instead of a fourth attempt.
2. **Weekly-slot rule — still armed, still unmet.** H41's pass does not clear it. The rule requires beating
   `holdout_best = 0.14479018210246675` *on the protocol that produced that number* (the H34 cells, draws 20/21),
   so a candidate built from the H41 habitat must be re-scored there; the `above_holdout_best: true` field the
   H41 analyzer prints is an artifact of comparing across protocols and must be read as meaningless
   (`knowledge/26` §3). No file in `registry/submissions.json` is slot-approved and no slot has been used.
3. **H36/H37/H42 — superseded in ranking, not deleted.** The v4 slate (`knowledge/25`) puts H43 (DEM drainage
   organization) first because it needs no download in an environment where only `api.github.com` and `pypi.org`
   complete TLS; H44–H47 are recorded with their blocked external sources. H36/H37/H42 keep their v3 specs and
   stay behind H43.
4. **The robustness upgrade listed here is now the critical path.** This list asked for A4 (union) to be
   re-estimated on *different* folds/draws before trusting a near-miss or a near-pass. The preregistered
   confirmation on draws 30/31 is that test for H41's two passing arms; if it reproduces, the remaining robustness
   question is fold geometry (the 30 % quadrant folds are shared by every screen in this family, so all six
   verdicts are correlated through it) — worth one frozen geometry-swap before any candidate is called stable.
5. **Housekeeping — partly done.** `scripts/download_competition_data.sh` exists and both template layouts
   resolve through one helper; the draw ledger is no longer pure prose for this family: `design_screen.json` and
   `design_confirm.json` each record a machine-readable `draw_seed_inventory`. A single structured draws
   registry with a test (this list's actual ask) is still open, as is the suggestion to archive nothing
   regenerable.

---

## 3. Session-5 close-out (2026-10-03): H43 DEM drainage-organization screen complete

1. **H43 (rank 1 of the v4 slate, `knowledge/25`) implemented and screened on draws 32/33 (`evidence/h43_screen/`, `knowledge/28_h43_results_2026-10-03.md`).**
   `src/gemsdoe/h43.py` implements Barnes-Lehman-Mulla priority-flood depression filling (`0` trapped interior
   cells, `17,865` boundary outlets, `100 %` mass conservation across all `5,167,373` footprint pixels),
   D8 steepest-descent flow accumulation, unit stream power $\Omega = A^{0.5}\cdot S$, and per-basin repeated-median
   log-log $S\text{–}A$ knickpoint excess across `108` major basins. All `40` cells (4 folds $\times$ draws `32/33`
   $\times$ 5 arms) ran on a clean tree (`09e81264`) and were independently audited by
   `scripts/analyze_h43_screen.py` (`integrity_problems: []`).
2. **Outcome: all four arms failed G1 (none reached the `+0.005` mean paired gain bar); no confirmation draws (`34/35`) were fit and no slot was used.**
   - `A4_h43_union` gained **`+0.0039976`** mean paired DTI and cleared every stability/floor/budget criterion
     (positive in all 4 quadrant fold means: `NW +0.00387, NE +0.00350, SW +0.00642, SE +0.00220`; `3/4` and
     `4/4` positive folds per draw; worst fold `+0.0021960`; holdout AUC `0.7883 -> 0.7913`), missing only the
     `+0.005` effect bar by `0.00100`.
   - `A3_h43_scarp_free` (`+0.0019365` primary) became the first feature arm in the H35/H40/H41/H43 family to
     pass the **SGMC off-catalogue secondary-proxy fold gate** (`+0.0013560` mean SGMC paired gain, `3/4` folds
     positive) while also improving the primary proxy — showing that scarp-free drainage/knickpoint columns carry
     cross-proxy signal where `H43_CHANNEL_SCARP` (`A4`) trades SGMC score (`-0.001125`) for catalogue-style
     range-front score.
3. **Structured draw ledger (`registry/draw_ledger.json`, `scripts/build_draw_ledger.py`) — complete and tested.**
   Every fitted draw across all stages (`0..15, 20..25, 28..33`, 28 draws total) and every authorized-then-released
   pair (`2/3`, `26/27`, `34/35`) is tracked in `registry/draw_ledger.json` and checked by `pytest`.
4. **Next steps for Session 6:**
   - **Zero-download v3 candidates still untried:** **H36** (MT 3D conductance gradient & phase-tensor strike
     asymmetry from cached bands `14..16`), **H37** (geothermometry residual above conductive heat-flow prediction
     from cached bands `8, 17`), and **H42** (measured-period radial spectral notch on `0_mag_rtp` and `2_grav_iso`).
   - **External-data v4 candidates (`H44` USGS 2023 NSHM fault sections, `H45` UNR NGL GPS strain-rate tensor,
     `H46` ComCat relocated hypocentral lineations):** require an owner-side fetch from their official public endpoints
     (`https://www.sciencebase.gov/catalog/item/63f7b45cd34e4f7eda456572`, `http://geodesy.unr.edu/`,
     `https://earthquake.usgs.gov/fdsnws/event/1/`) with SHA-256 pinning in `registry/data_manifest.json` before
     screening (`IR-29-SANDBOX-NET`).
   - Any new screen must pre-register on fresh draws (`next_free_draw = 34` in `registry/draw_ledger.json`, or
     `>= 36` to skip the released-unused `34, 35` pair).


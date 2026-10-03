# 28 — Emission-density sweep results (2026-10-03): the thinning ladder was already converged

Frozen protocol: [`knowledge/27`](27_preregistered_emission_density_sweep_2026-10-03.md) (sha256 recorded in
`evidence/emission_sweep/design.json`). Run: `scripts/run_emission_sweep.py` on a clean tree at commit
`14ad381`, 15 scored rows, no model fitted, no holdout draw spent, no DrivenData contact. Evidence:
`evidence/emission_sweep/{design.json,rows.jsonl,summary.json}`.

## 1. What was measured

Every row is a deterministic re-spacing (or score-aware re-placement) of the **same frozen habitat**, the
owner-mirrored H19-5 emission — the parent of the group's reported live ladder (solid 0.1922 → d1.5 0.2477 →
d2.8 0.2600, all owner-reported claims). Each row was scored on the repository's two registered file-level
proxies: `catalogue_hidden` (masked DTI on hidden catalogue components, 4 quadrant folds × draws 20/21) and
`sgmc_off_catalogue` (state-map faults ≥ 300 m from the supplied catalogue). Code path:
`src/gemsdoe/proxies.py`, the same functions `scripts/score_candidates.py` now uses; the reference file's
numbers reproduce the committed `evidence/candidate_scoreboard.json` values exactly after that refactor
(0.09832378835029429 / 0.09528236525789707), which is the refactor's regression receipt.

| row | emitted px | catalogue-hidden | Δ vs 2.8 (paired, 8 cells) | SGMC |
|---|---:|---:|---:|---:|
| `cal_solid` (parent) | 121,131 | 0.06970 | −0.02862 | 0.10060 |
| `thin_2.0` | 60,069 | 0.09449 | −0.00383 | 0.10112 |
| `thin_2.4` | 44,090 | 0.09832 | **0.00000** | 0.09528 |
| **`thin_2.8` = the pinned artifact** | 44,090 | **0.09832** | 0.00000 | 0.09528 |
| `thin_3.2` | 34,817 | 0.09552 | −0.00280 | 0.08590 |
| `thin_3.6` | 34,817 | 0.09552 | −0.00280 | 0.08590 |
| `thin_4.0` | 31,930 | 0.09399 | −0.00434 | 0.08155 |
| `thin_4.8` | 26,192 | 0.08733 | −0.01099 | 0.07127 |
| `thin_5.6` | 22,243 | 0.07784 | −0.02048 | 0.06195 |
| `thin_6.4` | 19,340 | 0.07161 | −0.02672 | 0.05465 |
| `aware_2.8` (blur-score placement) | 39,751 | 0.09399 | −0.00433 | 0.08904 |
| `aware_3.6` | 30,437 | 0.08659 | −0.01173 | 0.07769 |
| `aware_4.8` | 22,397 | 0.07304 | −0.02528 | 0.06197 |
| `cal_d1_5` (pinned) | 60,069 | 0.09449 | −0.00383 | 0.10112 |
| `cal_d2_8` (pinned reference) | 44,090 | 0.09832 | 0.00000 | 0.09528 |

## 2. Verdict, by the frozen rule

* **Proxy calibration check: PASS.** `0.06970 (solid) < 0.09449 (d1.5) < 0.09832 (d2.8)` — the proxy
  reproduces the *same ordering* as the reported live ladder on all three rungs. The density axis of the
  catalogue-hidden proxy is therefore usable for a spacing decision in a way it cannot be for, say, a
  model-derived habitat.
* **Admissible rows: none.** No new row beats the pinned 2.8 px artifact on the primary proxy, so rule §5.4
  returns "**keep the pinned artifact**". The score-aware placement is *worse* at its own best spacing
  (−0.00433), so H26-0-style score-ordered dotting is not a free improvement here.
* **Boundary result: no.** The optimum is interior (2.8 px with declines in both directions), which is the
  outcome that licenses *stopping* this line rather than extending it.

**Scientific reading.** The 0.1922 → 0.2477 → 0.2600 ladder was not an unfinished sweep — it was already
sitting on the optimum of its own family. The metric's marginal algebra (`knowledge/07` §2) says a dot is
worth emitting while its expected credit exceeds ≈ 4.5 % of its FP mass; at 2.8 px the emission has spent
that budget, and both denser (solid: −0.0286) and sparser (6.4 px: −0.0267) rows are worse. The remaining
way to raise DTI is therefore **credit per dot** — better places, i.e. a better habitat — which is exactly
where every feature screen since H31 has been pointed.

## 3. Two geometry facts discovered on the real bytes

1. **The spacing parameter is quantised by an integer disc.** `dot_thin(mask, d)` blocks offsets with
   `dy² + dx² < d²`, so distinct transforms exist only between integer radius-squared thresholds. Measured
   here: `thin_2.0` is **pixel-identical** to the pinned 1.5 file (60,069 px) and `thin_2.4` is
   **pixel-identical** to the pinned 2.8 file (44,090 px, 0.00000 paired delta on all 8 cells); `thin_3.2`
   and `thin_3.6` are identical to each other (34,817 px).
   * Consequence: **IR-29-D28-NAMING is closed as a naming question, not a data question.** `knowledge/07`
   §6.1 recorded that the sibling's model text describes the same 44,090-pixel geometry as "d = 2.4" while
   the file is named `d2-8`. Both are correct descriptions of the *same transform* under this implementation:
   2.4 and 2.8 fall in one disc class. The bytes are unambiguous and the artifact is what it says it is.
   * New irregularity registered: **IR-29-SPACING-QUANTISATION** — "d" is a threshold, not a metric distance;
   any future ladder must report the disc class (pixel count) alongside the nominal spacing.
2. **Determinism control passed.** `dot_thin(H19-5 > 0, 2.8)` reproduces the pinned artifact pixel-for-pixel
   and `dot_thin(·, 1.5)` the pinned d1.5 file, from the hash-pinned parent, in this checkout (the sweep
   aborts if it does not, knowledge/27 §3.1).

## 4. What this changes, and what it does not

* **Changes:** the "just re-space the 0.26-class file" route is closed with a measurement rather than an
  assumption, and the optimum is shown to be interior. Any future emission-geometry claim must start from
  this curve.
* **Does not change:** the slot policy. This was a file-level proxy comparison with no model fitted; the
  slot rule still requires beating `holdout_best = 0.14479018210246675` on the H34 cell protocol **and**
  passing a frozen screen plus confirmation plus the secondary-proxy gate. Nothing here is slot-approved and
  nothing here was submitted.

## 5. Side finding recorded for honesty (not a result of the sweep)

While re-running the shared proxy path for the refactor, the repository candidate file
`docs/downloads/gemsdoe29-repo-c0-habitat-emission-20261003-a4d439b07426-nan.tif` was scored at the file
level for the first time: `catalogue_hidden = 0.32701`, `sgmc = 0.03782`, `hug_share = 0.595`, 37,913 px.
**That 0.327 is a leakage artifact, not evidence.** The artifact's model was trained on every catalogue
pixel, so its dots sit on catalogue components — including the very components the proxy hides — and the
number is inflated by construction (this is why `knowledge/17` deliberately quotes the *per-fold screen*
number 0.14086 for the method and never a score of the shipped file). It is recorded here as a demonstration
that the file-level proxy must never be used to rank model-derived artifacts. No page, registry or claim uses
the 0.327 figure.

## 6. Artifacts

* `evidence/emission_sweep/design.json` — preregistration sha256, frozen parameter table, input hashes,
  module hashes, git state, environment, and the explicit `seed_spend: none` declaration.
* `evidence/emission_sweep/rows.jsonl` — every row's full proxy record (8 per-cell DTI values, TP/FP,
  emitted counts, neighbour profile, paired deltas).
* `evidence/emission_sweep/summary.json` — the decision object quoted in §2.
* `src/gemsdoe/proxies.py`, `scripts/run_emission_sweep.py`, `tests/test_emission_sweep.py`.

# H29 results — worming + thermal screen against the frozen gate (2026-10-03)

Protocol: `knowledge/01_preregistration_h29_worming_2026-10-03.md` (frozen BEFORE any run).
Raw numbers: `evidence/h29_holdout.json` (16 fold×draw runs, 865 s), `evidence/h29_gate.json`,
run log `evidence/h29_screen_run.log`. Worming rasters/receipts: `evidence/worming_receipt.json`.
Metric/geometry calibration: 17/17 repo tests incl. brute-force DTI and bit-for-bit reproduction of
the mirrored 0.2477 mask + exact 44,090-px d2.8 count.

## Verdict per arm (sparse quadrant-dotted proxy DTI; gate = mean paired ΔDTI ≥ +0.005, ≥3/4 folds, both screen draws, ≥1 confirmation draw)

| arm | idea | draw0 μ (folds+) | draw1 μ (folds+) | draw2 | draw3 | verdict |
|---|---|---|---|---|---|---|
| A1 | worm-gated emission (drop defined-shallow dots) | −0.00016 (1/4) | −0.00012 (1/4) | ≈0 | +0.0004 | **FAIL** — near-no-op as predicted (IR-29-PARENT-OFF-EDGES: only 2.7 % of dots are gated) |
| A2 | worm-ranked dot claiming order | −0.00098 (2/4) | +0.00024 (3/4) | +0.0016 | −0.0008 | **FAIL** — sign unstable across draws; no evidence the H26-0 ranking lever extends to persistence-priority at d=2.8 |
| B1 | worm persistence as head features | +0.00038 (2/4) | +0.00035 (3/4) | −0.0005 | −0.0017 | **FAIL** — small, directionally positive on screen draws, not replicated on confirmation |
| B2 | 2 m thermal-probe residual features | +0.00050 (2/4) | +0.00123 (4/4) | +0.0007 | −0.0002 | **FAIL** — strongest arm this session; one 4/4 positive draw but ~1/4 of the margin; matches sibling H27-2 never getting to run at all |

## What this establishes (and what it does not)

1. Established: on this grid, at this threshold (p95 edges), with this proxy, at this budget (2.8-px
   dots), neither persistence-as-filter, persistence-as-order, nor persistence/thermal-as-features
   clears the pre-registered bar. No slot was recommended and none was spent.
2. Established: the acquisition-line audit has a number now — E–W edges are the MOST persistent
   (0.656 vs N–S 0.562); the naive "aliasing = shallow = dies under UC" heuristic is refuted on this
   survey area, which kills the cheap version of H29-3 and motivates the spectral-notch version instead.
3. NOT established (and not claimed): that worming is useless for the hidden-label habitat. The proxy's
   truth is 100 % on-catalogue; 77.8 % of the live-scored emission's credit lives ≥300 m from the
   catalogue (measured here), where the proxy is structurally blind. The defensible statement is
   "no measurable proxy gain ⇒ not slot-eligible", which is exactly what a frozen gate is for.
4. NOT established: that the parent surface is optimal — GEMSDOE27's live inversion bounds its
   geometry at ≈0.255–0.260 and caps concentration at 5.3–5.7× blind. Beating 0.3195 needs
   information that ranks fault-proximal truth > 5.7× blind; this session proved these two specific
   channels (p95-worm persistence, probe residuals as raw features) are not that, at these dosages.

## Next-session agenda (ranked, registered in registry/hypotheses_h29.json)

1. H29-3 spectral flight-line notch → re-derive persistence on line-suppressed fields (the refuted
   naive filter's rigorous sibling; own frozen gate).
2. H29-5 microseismicity/dilatation corridors ALONG persistent worms (interaction term, not raw features).
3. Soft-prior emission: multiply the parent's ranking field by (1 + γ·(P−0.5)) with γ pre-registered;
   the quantized p95 gate is coarse — the continuous amplitude-retention field S (already computed,
   stored per-level) is the better dosage; pre-register before running.
4. GPU session: DTI-aligned U-Net (reference solution + sibling loss code) trained on the now-restored
   local stack; ensemble with h19-5 as prior; the only lever class with headroom above 0.30 by the
   concentration arithmetic.
5. Networked runner: GDR paleo-geothermal + Q-volcanics fetch against pins in data/manifest.json → H29-4.

## Artifacts shipped today (statuses attached, not implied)

- `docs/downloads/gems29-wormrank-d28-20261003-73a8c4d12139-{nan,zeros}.tif(+zip)` — the A2-style
  full-map emission (41,349 px): format-validated (30/30 checks), **research-only, gate FAIL**, on the
  site with that label on the download card itself.
- `docs/downloads/gems29-refd28-repro-20261003-1cc7dc534d51-*` — bit-exact reproduction of the
  0.2600 geometry; reference/rollback only; resubmission pointless and labelled as such.

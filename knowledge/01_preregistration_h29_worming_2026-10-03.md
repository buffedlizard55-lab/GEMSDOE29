# H29 pre-registration — multiscale worming as deep/shallow reliability, frozen 2026-10-03T08:40Z

Written and committed BEFORE any worming raster or holdout number in this repo was produced.
Maximize P(Win) means pre-committing the gate so a failure is a failure, not a re-tune.

## 1. Literature basis (verified 2026-10-03, links in registry/sources.json)

- Hornby, P., Boschetti, F., & Horowitz, F. G. (1999). *Analysis of potential field data in the
  wavelet domain.* Geophysical Journal International 137(1), 175–196. The prompt's "1999,
  exploration-geophysics worming" reference. (Irregularity flag: prompt cites this as a 1999
  *Geophysics*/wavelet edge-detection paper; the primary source is GJI 137. See IR-29-CITATION.)
- Horowitz, F. G. (2018). *Potential Field Poisson Wavelet Multiscale Edge Analysis*, Stanford
  Geothermal Workshop: https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2018/Horowitz.pdf —
  operational recipe: upward-continue to a suite of heights; local maxima of horizontal-gradient
  modulus at each height are multiscale edges ("worms"); for magnetics work in reduced-to-pole or
  pseudogravity space; upward continuation *is* a scale change of the wavelet transform; the decay
  of edge strength with height carries the depth/singularity information.
- Practical corollaries used here: an edge that vanishes immediately with small continuation is
  shallow/possibly instrumental; a persisting edge is tied to deeper, more extensive sources.
  Depth estimates grow *less* reliable with depth (Horowitz 2018, stated limitation) — so
  persistence is used as a *reliability weight*, never as a depth inversion.
- Acquisition geometry: GeoDAWN NV West-Central 2020 (DOI 10.5066/P93LGLVQ, ScienceBase item
  657e1d85d34e23d3533209f7): four blocks, E–W flight lines, 200 m and 400 m line spacing. E–W
  line aliasing is the named shallow-artifact nuisance.

## 2. What already exists in this repo family (checked line-by-line, so "novelty" is honest)

- 19GEMSDOE `L4_Geopotential_Basement` (a line inside parent H19-4/H19-5): **single-scale**
  (fixed 1.5 km) multi-azimuth strike-coherent gravity+magnetic horizontal-gradient ridge.
  No continuation ladder, no persistence statistic, no line-artifact number.
- GEMSDOE26 `H26-XEDGE`: Gaussian scale-space edges at 300/600/1200 m sigma, cross-scale signed
  agreement + doubled-angle structure tensors, used as **head features**; failed its frozen gate
  (+0.0014 sparse vs required +0.005). Not Fourier upward continuation, no worm tracking, never
  applied as an emission reliability filter.
- GEMSDOE27 `H28-1 potential_edges.py`: two-scale Gaussian magnitudes + concordance as features.
  Same limitation.
- Therefore the following are genuinely untried in this repo family and are the objects of this
  pre-registration: (a) FFT upward-continuation ladder on `rtp` and `iso_grav_anom` from the raw
  potential fields; (b) cross-level worm tracking with a height-growing match tolerance;
  (c) persistence-with-height as an **emission reliability filter/re-ranker**; (d) an explicit
  E–W-line survival audit number.

## 3. Operators and frozen constants

- Ladder heights h = 0, 100, 200, 400, 800, 1600 m on the 100 m grid.
- Continuation: `F{u_h} = F{u} · exp(-2π h |k|)` (rfft2/irfft2, float64); field median-removed,
  nearest-filled outside footprint, 192-px cosine edge taper.
- Edges per level: local maxima of the horizontal-gradient modulus along the gradient direction,
  HGM ≥ 95th percentile of in-footprint HGM at that level (`EDGE_QUANTILE = 0.95`).
- Tracking: contiguous level-to-level nearest-neighbour match, tolerance
  `tol_px = 1 + 0.5·(h/100 m)`; a chain breaks at the first unmatched level.
- Persistence P ∈ {0, 0.2, 0.4, 0.6, 0.8, 1.0} = last matched level / (levels-1) on level-0 edge
  pixels. Joint raster: `min(P_mag, P_grav)` where both fields have a level-0 edge, otherwise the
  single field's persistence; plus a **defined mask** (1 where a level-0 edge exists in either field).
  Absence of a level-0 edge means worming is SILENT, not negative.
- TAU_PERSIST = 0.5 (survived to ≥ 800 m ⇒ "deep"; below ⇒ distrusted shallow) for A1 gating.
  A1 removes ONLY pixels where the joint statistic is DEFINED and below TAU; where no level-0 edge
  exists (statistic silent) the parent dot is kept untouched. A2 gives silent pixels neutral priority.
- Cross-check anchor: our TMI continuation to 150 m HGM vs the contractor `TMI_up150` grid HGM
  (u8 ranks, monotone-only comparison), Spearman over the footprint, 4-px stride.

## 4. Arms, data, metric

- Truth proxy = hide-and-recover catalogue components: 4 spatial quadrants, 20 % of 8-connected
  components hidden per quadrant per draw; draws 0–1 = screen, draws 2–3 = confirmation.
  Metric = binary DTI with catalogue masking, per-fold then pooled (metric.py semantics).
- Emission arms (parent solid = mirrored h19-5 emission, minus known catalogue, per quadrant):
  A0 control `dot_thin(·, 2.8)`; A1 worm-gated (drop pixels with jointP < 0.5, then same thinning);
  A2 worm-ranked (`dot_thin_ranked`, priority = 0.5·jointP + 0.5·lidar ridge composite).
- Head arms (HistGradientBoosting, frozen hyperparameters in head.py, 8:1 negative sampling):
  B0 = 19 raw bands + 10 lidar bands + 2 catalogue-distance features;
  B1 = B0 + 4 worming features; B2 = B0 + 3 thermal-probe features (GDR 1391, hash-pinned,
  F2mDAB background-normalised residual — unblocks 25/27's H27-2 which could not fetch the file).
  Emission = top-K per quadrant, K = A0 quadrant count (budget parity ±0 by construction).
- Pixel counts reported for every arm; A1 is allowed to shrink the count and that is reported, not
  silently absorbed.

## 5. Frozen gate (applies to each candidate B1-B0, B2-B0, A1-A0, A2-A0)

PASS iff: mean paired quadrant ΔDTI ≥ **+0.005** and ≥ 3/4 quadrants positive in **both** draws
0 and 1, AND replicated in the same form on at least one confirmation draw (2 or 3).
Anything else = FAIL: no full-map fit, no TIF packaged as a slot candidate, arm recorded blocked.

## 6. Disclosed biases (do not pretend these away)

- The proxy is catalogue-internal: it under-sees far-field habitat where the live 0.2477/0.2600
  emissions earn most credit (GEMSDOE27 measured 100 % proxy truth at catalogue distance 0). A
  worming gain measured here is necessary, NOT sufficient, for a live gain; conversely a proxy
  loss does not refute a deep-structure detector whose target habitat the proxy cannot see. The
  far-field audit statistics (E–W survival, concordance with thermal probes) are reported
  alongside precisely so the *scientific* case is visible separately from the proxy number.
- No live effect is claimed for any file built from a pass. The DTI-vs-emission-geometry model
  fitted on owner-reported anchors (GEMSDOE25/27) is reported as conditional arithmetic only.
- Upward continuation of an airborne grid also smooths *real* shallow fault signal; TAU=0.5
  gating may remove genuinely young, shallow-expressed Quaternary faults. That is the risk this
  screen is designed to expose, and it is symmetrical: the gate must improve, not merely shift,
  which pixels are credited.
- The competition scores *newly mapped expert faults*, not necessarily geothermal ones; worming is
  justified as a deep-crustal structure detector, which is only *correlated* with the label set.

## 7. Outputs promised by this session

`evidence/worming_receipt.json` (all ladder stats + audits), `evidence/h29_holdout.json` (per-arm
per-fold numbers), `evidence/h29_gate.json` (gate verdict), site pages with these numbers
rendered from the JSON, and — only if a gate passes — a packaged, format-verified candidate TIF
with note text, labelled "slot-recommended (local gate passed; live effect unverified)". If all
gates fail, the site's one-click download remains a format-verified *research artifact* with the
failure recorded on the same page, and the recommended live action stays "no new slot spend".

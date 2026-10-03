"""GEMSDOE29 — multiscale worming (Hornby-style) reliability science for the DOE GEMS Prize.

Competition: DrivenData #306 (DOE GEMS Prize Challenge, geothermal fault discovery over the GeoDAWN
region, Nevada). Metric: distance-weighted Tversky index, alpha=0.2, beta=0.8, triangular kernel with
300 m support. Submission: single-band float32 GeoTIFF, EPSG:32611, 3730x3292 at 100 m, values in
[0,1], null/nan outside. All official definitions quoted from
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (read 2026-10-03).

Modules
-------
paths/grid      : cache paths + the frozen competition grid.
metric          : DTI re-implementation (semantics per official page + sibling-validated masking),
                  unit-tested against brute force.
worming         : the science this session adds — upward-continuation ladder on the two potential
                  fields, profile edge detection, cross-level worm tracking, persistence rasters,
                  and the acquisition-line audit.
thinning        : deterministic Poisson-disk dot thinning + ranked variant (sibling-credited).
holdout         : spatially-blocked hide-and-recover folds (sibling-credited).
features/emission/submission : alignment, candidate emission and format-validated GeoTIFF writing.
thermal         : official GDR 1391 2 m temperature probes, parsed from the hash-pinned archive.
"""

__version__ = "29.0.0"

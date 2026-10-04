"""H53 cross-scale topographic fabric coherence: scale-persistent orientation, label-free.

The candidate slate v6 (`knowledge/38`) ranks this first of the untried ideas and the 2^(5-1)
fractional factorial (`knowledge/14`) is the prior behind that ranking: the DEM-curvature/scarp
family **B** carried a supported inclusion effect of **+0.0241** with 8/8 cells positive while the
potential-field families were weak or inert. H53 adds the one axis family B has never used --
*window scale*. Every orientation column in this repository is either single-scale or label-derived
(`L_strike_c2`/`L_strike_s2` are one-scale LiDAR strikes; `L_coh100` is a resultant length computed
from the **visible catalogue mask**, so it cannot see anything the catalogue does not already
contain). H53 is a pure function of the elevation grid.

Physics. A fault-controlled lineament keeps one strike as the observation window grows; dune fields,
drainage texture, bedding, cultural grids and acquisition-scale noise rotate or are replaced. The
measurement is the classical structure tensor (Förstner & Gülch 1987; Harris & Stephens 1988 review
in Weickert 1997): at each window scale ``s``,

    J_s = G_s * (grad I_s grad I_s^T),   coherence C_s = (l1 - l2)/(l1 + l2),
    orientation theta_s = 0.5 atan2(2 Jxy, Jxx - Jyy),

with ``I_s = G_s * I`` the scale-``s`` smoothing of the elevation grid. ``C_s`` is 1 for a pure step
line and 0 for an isotropic feature; ``theta_s`` is the gradient azimuth, so the *strike* is
``theta_s + 90 deg`` (mod 180 deg). Because only differences of strike matter to the agreement
statistics, the +90 deg convention is cosmetic here and is reported in the diagnostics instead.

Cross-scale persistence (the H53 signal, frozen before any fit):

* ``H53_COH_MIN``  -- ``min_s C_s`` over the scales with a defined orientation; 0 if fewer than two
  scales are defined. A lineament that is sharp at 300 m and gone at 1500 m has a low minimum.
* ``H53_AGREE``     -- axial (mod 180 deg) resultant length ``R = |sum_s w_s exp(2i theta_s)| / sum_s w_s``
  with ``w_s = C_s`` on defined scales. ``R = 1`` means every scale sees the same strike, ``R ~ 0.5``
  is the expected value of three random strikes, ``R = 0`` means they are incompatible. Fewer than two
  defined scales gives ``R = 0`` (nothing to agree with).
* ``H53_NSCALES``   -- share of the three scales whose strike lies within ``tol_deg`` of the
  coherence-weighted mean strike: 0, 1/3, 2/3 or 1.
* ``H53_PERSIST``   -- ``H53_COH_MIN * H53_AGREE``: strong **and** scale-persistent.

Definition of "defined": ``C_s >= coherence_min`` **and** the scale-``s`` gradient modulus at the pixel
reaches ``min_contrast_fraction`` of the 99th percentile of that scale's gradient modulus over the
footprint. The absolute-floor form is deliberate: the worming line's documented failure mode
(`knowledge/34` section 4, `knowledge/40` section 3) was a *percentile of its own level* threshold, which
keeps a fixed fraction of pixels at every level and therefore can never show that something vanished.
Here a quiet window simply yields an undefined orientation and drags the agreement statistics down.

Honest limits, stated before the screen: (i) the 100 m grid coarsens the 300 m window, so the smallest
scale is close to the Nyquist-scale texture of the DEM; (ii) lithologic layering, dyke swarms and
bedding also produce scale-persistent fabric, so the arm set must isolate the *off-catalogue* increment
(that is arm A2) and the conjunction with the scarp amplitude (arm A3); (iii) a scale-persistent fabric
is a *lineament* claim -- it does not by itself prove a fault, it re-ranks where a fault would be
drawn. Nothing in this module reads the catalogue, the labels or any fitted quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter

from .features import nearest_fill

H53_NAMES = [
    "H53_COH_MIN",
    "H53_AGREE",
    "H53_NSCALES",
    "H53_PERSIST",
]


@dataclass(frozen=True)
class H53Config:
    """Frozen H53 parameters. Declared in `knowledge/41` before any fit; never tuned after one."""

    scales_px: tuple[float, float, float] = (3.0, 7.0, 15.0)  # 300 / 700 / 1500 m analysis window at 100 m cells
    gradient_sigma_px: float = 1.0  # gradient pre-smoothing: the analysis window is the *tensor* window
    tensor_sigma_factor: float = 1.0  # tensor smoothing = factor * window scale
    tol_deg: float = 15.0  # strike agreement tolerance (slate v6: "+/-15 degrees")
    coherence_min: float = 0.15  # below this the structure-tensor orientation is undefined
    min_contrast_fraction: float = 1e-3  # gradient floor as a fraction of the scale's own p99
    highpass_sigma_px: float = 0.0  # > 0 removes wavelengths longer than ~3 sigma before the tensor
    elev_band: str = "12_det_elev.npy"

    def validate(self) -> None:
        if len(self.scales_px) != 3 or any(s <= 0 for s in self.scales_px):
            raise ValueError("scales_px must be three positive window scales")
        if self.highpass_sigma_px < 0:
            raise ValueError("highpass_sigma_px must be non-negative (0 disables the high pass)")
        if self.highpass_sigma_px > 0 and self.highpass_sigma_px < self.scales_px[-1]:
            raise ValueError("highpass_sigma_px must exceed the largest window scale, or the scale ladder is empty")
        if tuple(sorted(self.scales_px)) != tuple(self.scales_px):
            raise ValueError("scales_px must be declared in increasing order")
        if self.tensor_sigma_factor <= 0:
            raise ValueError("tensor_sigma_factor must be positive")
        if self.gradient_sigma_px <= 0:
            raise ValueError("gradient_sigma_px must be positive (it is the noise pre-scale)")
        for name, value in (("tol_deg", self.tol_deg),):
            if not 0.0 < value < 90.0:
                raise ValueError(f"{name} must lie strictly inside (0, 90) degrees")
        for name, value in (("coherence_min", self.coherence_min),
                            ("min_contrast_fraction", self.min_contrast_fraction)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1]")


def _structure_tensor(elev: np.ndarray, scale: float, tensor_sigma_factor: float,
                      gradient_sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (coherence, gradient azimuth, gradient modulus) for one analysis window.

    The gradient is taken at the small fixed pre-scale ``gradient_sigma`` (one cell at 100 m); the
    analysis window enters only through the tensor smoothing ``sigma_t = factor * scale``. Smoothing the
    *field* at the window scale before differentiating -- an easy misreading of "multiscale" -- would
    wipe out every wavelength below ~2 scales and make the ladder a band-pass of the regional trend
    instead of a fabric window.
    """
    smoothed = gaussian_filter(elev, float(gradient_sigma), mode="nearest")
    gy, gx = np.gradient(smoothed)
    del smoothed
    modulus = np.sqrt(gx * gx + gy * gy).astype(np.float32)
    sigma_t = float(tensor_sigma_factor) * float(scale)
    jxx = gaussian_filter(gx * gx, sigma_t, mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma_t, mode="nearest")
    jxy = gaussian_filter(gx * gy, sigma_t, mode="nearest")
    del gx, gy
    trace = jxx + jyy
    diff = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy)
    coherence = np.where(trace > 0, diff / np.maximum(trace, np.finfo(np.float32).tiny), 0.0)
    theta = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    del jxx, jyy, jxy, diff, trace
    return (np.clip(np.nan_to_num(coherence, nan=0.0), 0.0, 1.0).astype(np.float32),
            np.nan_to_num(theta, nan=0.0).astype(np.float32), modulus)


def _axial_resultant(theta: np.ndarray, weights: np.ndarray, defined: np.ndarray) -> np.ndarray:
    """R = |sum w exp(2 i theta)| / sum w over the scale axis, ignoring undefined scales."""
    w = np.where(defined, weights, 0.0)
    c2 = np.sum(w * np.cos(2.0 * theta), axis=0)
    s2 = np.sum(w * np.sin(2.0 * theta), axis=0)
    wsum = np.sum(w, axis=0)
    return np.where(wsum > 0, np.sqrt(c2 * c2 + s2 * s2) / np.maximum(wsum, np.finfo(np.float32).tiny), 0.0)


def build_h53_fields(band_dir: Path, footprint: np.ndarray, fi: np.ndarray,
                     config: H53Config | None = None) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, Any]]:
    """Build the four H53 columns as footprint vectors plus full grids and diagnostics.

    ``footprint`` is the bool grid; ``fi`` is ``np.flatnonzero(footprint.ravel())`` from the caller (passed
    in because recomputing it on a 12 M-pixel grid is wasteful). Nothing here reads the catalogue or labels.
    """
    config = config or H53Config()
    config.validate()
    elev = np.load(band_dir / config.elev_band, mmap_mode="r")
    if elev.shape != footprint.shape:
        raise ValueError(f"elevation band {elev.shape} does not match footprint {footprint.shape}")
    filled = nearest_fill(np.asarray(elev, dtype=np.float32))
    if not np.isfinite(filled).all():
        raise ValueError("nearest_fill left non-finite elevation values; the footprint is not covered")
    if config.highpass_sigma_px > 0:
        # Remove the regional slope/warp (wavelengths >> the largest window) so that the scale ladder
        # measures lineament fabric rather than the one regional gradient, which all three windows share
        # by construction and which would otherwise saturate the agreement statistic.
        filled = (filled - gaussian_filter(filled, float(config.highpass_sigma_px), mode="nearest")).astype(np.float32)

    coherences, thetas, diagnostics = [], [], {"scales_px": [float(s) for s in config.scales_px], "per_scale": []}
    for scale in config.scales_px:
        coherence, theta, modulus = _structure_tensor(filled, float(scale), config.tensor_sigma_factor,
                                                      config.gradient_sigma_px)
        # Contrast floor: an *absolute* fraction of this scale's own 99th-percentile gradient modulus, so a
        # quiet window can genuinely fail to define an orientation (the H31/H29 percentile-threshold failure).
        contrast_floor = float(config.min_contrast_fraction) * float(np.percentile(modulus, 99.0))
        defined = (coherence >= float(config.coherence_min)) & (modulus >= contrast_floor)
        del modulus
        coherences.append(coherence)
        thetas.append(theta)
        diagnostics["per_scale"].append(dict(
            scale_px=float(scale),
            coherence_defined_fraction=float(np.mean(defined.ravel()[fi])),
            coherence_mean_defined=float(coherence.ravel()[fi][defined.ravel()[fi]].mean())
            if defined.ravel()[fi].any() else 0.0,
            contrast_floor=float(contrast_floor),
        ))
        del defined
    del filled

    coh = np.stack(coherences)
    theta = np.stack(thetas)
    del coherences, thetas
    defined = coh >= np.float32(config.coherence_min)
    n_defined = defined.sum(axis=0)

    coh_min = np.where(n_defined >= 2, np.min(np.where(defined, coh, np.inf), axis=0), 0.0).astype(np.float32)
    agree = np.where(n_defined >= 2, _axial_resultant(theta, coh, defined), 0.0).astype(np.float32)

    c2 = np.sum(np.where(defined, coh, 0.0) * np.cos(2.0 * theta), axis=0)
    s2 = np.sum(np.where(defined, coh, 0.0) * np.sin(2.0 * theta), axis=0)
    mean_theta = 0.5 * np.arctan2(s2, c2)
    delta = np.abs(np.arctan2(np.sin(2.0 * (theta - mean_theta)), np.cos(2.0 * (theta - mean_theta)))) * 0.5
    within = (delta <= np.deg2rad(float(config.tol_deg))) & defined
    nscales = (within.sum(axis=0).astype(np.float32) / np.float32(len(config.scales_px)))
    nscales = np.where(n_defined >= 2, nscales, 0.0).astype(np.float32)
    persist = (coh_min * agree).astype(np.float32)
    del theta, coh, defined, c2, s2, mean_theta, delta, within, n_defined

    vectors = np.stack([coh_min.ravel()[fi], agree.ravel()[fi], nscales.ravel()[fi], persist.ravel()[fi]])
    grids = {
        "H53_COH_MIN": coh_min,
        "H53_AGREE": agree,
        "H53_NSCALES": nscales,
        "H53_PERSIST": persist,
    }
    diagnostics.update(dict(
        n_footprint=int(fi.size),
        level_detector="structure-tensor coherence and gradient azimuth at three window scales",
        agreement_rule="axial resultant length of the per-scale strikes, coherence-weighted, mod 180 degrees",
        defined_rule=f"coherence >= {config.coherence_min} AND gradient modulus >= "
                     f"{config.min_contrast_fraction} x that scale's own p99",
        surrogate_note="R ~ 0.5 is the expected value of three unrelated strikes; R = 1 is one strike",
        nonzero_fraction={name: float(np.mean(row > 0)) for name, row in zip(H53_NAMES, vectors)},
        mean={name: float(row.mean()) for name, row in zip(H53_NAMES, vectors)},
        max_value={name: float(row.max()) for name, row in zip(H53_NAMES, vectors)},
        coherence_min_band="defined or undefined per scale; the floor is absolute, never a percentile of the field",
        label_free=True,
    ))
    return vectors.astype(np.float32), grids, diagnostics

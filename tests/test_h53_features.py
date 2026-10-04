"""Synthetic validation of the H53 cross-scale fabric statistics.

The claims under test are the ones the module docstring makes, measured on synthetic input (never on
real data, never with labels): a straight lineament that survives the whole analysis ladder scores a
high agreement and persistence, isotropic texture does not, and a fabric that lives at a wavelength the
ladder cannot hold onto is caught by the *minimum coherence* column rather than by the agreement column.
These are physics checks of the statistic, not evidence about real faults.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.h53 import H53_NAMES, H53Config, build_h53_fields  # noqa: E402

N = 160
STEP_ROW = N // 2
BAND = slice(STEP_ROW - 6, STEP_ROW + 7)  # +/- 600 m around the synthetic lineament


def _grid() -> tuple[np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    return yy, xx


def _iso(seed: int = 3) -> np.ndarray:
    return gaussian_filter(np.random.default_rng(seed).normal(size=(N, N)).astype(np.float32), 2.0)


def _straight_step() -> np.ndarray:
    yy, _xx = _grid()
    return 40.0 * np.tanh((yy - STEP_ROW) / 2.0)


def _fine_ridges() -> np.ndarray:
    """Vertical ridges with a 600 m wavelength: strong gradient, no scale persistence."""
    _yy, xx = _grid()
    return 30.0 * np.sin(2.0 * np.pi * xx / 6.0)


def _fields(tmp_path: Path, elev: np.ndarray, name: str = "elev.npy") -> dict[str, np.ndarray]:
    band_dir = tmp_path / "bands"
    band_dir.mkdir(parents=True, exist_ok=True)
    np.save(band_dir / name, elev.astype(np.float32))
    footprint = np.ones(elev.shape, bool)
    fi = np.flatnonzero(footprint.ravel())
    vectors, _grids, _diag = build_h53_fields(band_dir, footprint, fi,
                                              config=H53Config(elev_band=name))
    return {n: vectors[i] for i, n in enumerate(H53_NAMES)}


def test_names_shapes_and_ranges(tmp_path: Path) -> None:
    footprint = np.ones((80, 80), bool)
    footprint[:5] = False
    band_dir = tmp_path / "bands"
    band_dir.mkdir(parents=True, exist_ok=True)
    np.save(band_dir / "small.npy", _iso()[:80, :80].astype(np.float32))
    fi = np.flatnonzero(footprint.ravel())
    vectors, grids, diag = build_h53_fields(band_dir, footprint, fi, config=H53Config(elev_band="small.npy"))
    assert vectors.shape == (4, fi.size)
    assert len(H53_NAMES) == 4
    for name in H53_NAMES:
        assert grids[name].shape == footprint.shape
    assert float(vectors.min()) >= 0.0
    assert float(vectors.max()) <= 1.0
    assert diag["label_free"] is True
    assert diag["defined_rule"].startswith("coherence >=")


def test_straight_lineament_scores_high_agreement_and_persistence(tmp_path: Path) -> None:
    line = _fields(tmp_path / "a", _iso() + _straight_step())
    background = _fields(tmp_path / "b", _iso())
    band = np.zeros((N, N), bool)
    band[BAND, :] = True
    b = band.ravel()
    assert line["H53_AGREE"][b].mean() > 0.9, "one straight step must agree across the whole ladder"
    assert line["H53_PERSIST"][b].mean() > 0.8
    assert background["H53_PERSIST"][b].mean() < 0.5, "isotropic texture must not look persistent"
    assert line["H53_NSCALES"][b].mean() == pytest.approx(1.0)


def test_fabric_that_does_not_survive_the_window_shows_in_min_coherence(tmp_path: Path) -> None:
    line = _fields(tmp_path / "a", _iso() + _straight_step())
    mixed = _fields(tmp_path / "b", _fine_ridges() + _straight_step())
    band = np.zeros((N, N), bool)
    band[BAND, :] = True
    b = band.ravel()
    assert mixed["H53_COH_MIN"][b].mean() < line["H53_COH_MIN"][b].mean() - 0.3
    assert line["H53_COH_MIN"][b].mean() > 0.9


def test_deterministic_and_footprint_scoped(tmp_path: Path) -> None:
    footprint = np.zeros((N, N), bool)
    footprint[20:140, 20:140] = True
    band_dir = tmp_path / "bands"
    band_dir.mkdir(parents=True, exist_ok=True)
    np.save(band_dir / "elev.npy", (_fine_ridges() + _straight_step()).astype(np.float32))
    fi = np.flatnonzero(footprint.ravel())
    first, _g1, _d1 = build_h53_fields(band_dir, footprint, fi, config=H53Config(elev_band="elev.npy"))
    second, _g2, _d2 = build_h53_fields(band_dir, footprint, fi, config=H53Config(elev_band="elev.npy"))
    assert np.array_equal(first, second)
    assert first.shape[1] == int(footprint.sum())


def test_nan_outside_footprint_is_filled_not_propagated(tmp_path: Path) -> None:
    elev = _iso() + _straight_step()
    elev[0:8, :] = np.nan
    footprint = np.ones(elev.shape, bool)
    footprint[0:8, :] = False
    band_dir = tmp_path / "bands"
    band_dir.mkdir(parents=True, exist_ok=True)
    np.save(band_dir / "elev.npy", elev.astype(np.float32))
    fi = np.flatnonzero(footprint.ravel())
    vectors, _grids, _diag = build_h53_fields(band_dir, footprint, fi, config=H53Config(elev_band="elev.npy"))
    assert np.isfinite(vectors).all()

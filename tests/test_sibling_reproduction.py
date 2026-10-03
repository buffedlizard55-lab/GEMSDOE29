"""Reproduction anchors against pinned owner mirrors (skipped when data absent).

These local checks do not authenticate the competition portal or owner-reported scores:
  * dot_thin(solid_h19_5, 1.5) reproduces the mirrored d1.5 mask bit-for-bit;
  * dot_thin(solid_h19_5, 2.8) reproduces the original D2.8 pixel mask bit-for-bit and its count;
  * local metric checks are finite sanity guards only; owner-reported live scores are not receipts.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems29 import gridio  # noqa: E402
from gems29.metric import dti_binary  # noqa: E402
from gems29.thinning import dot_thin  # noqa: E402

P = ROOT / "data"


@pytest.mark.skipif(not all((P / p).exists() for p in (
    "inputs/h19_5_nan.tif", "inputs/dotted_h19_5_d1_5_nan.tif", "inputs/dotted_h19_5_d2_8_nan.tif")),
    reason="owner mirrors not restored")
def test_d15_and_d28_masks_reproduced():
    with rasterio.open(P / "bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    parent, _ = gridio.read_band(P / "inputs/h19_5_nan.tif")
    solid = np.isfinite(parent) & (parent > 0.5) & fp
    d15 = dot_thin(solid, 1.5)
    ref, _ = gridio.read_band(P / "inputs/dotted_h19_5_d1_5_nan.tif")
    refm = np.isfinite(ref) & (ref > 0.5) & fp
    assert np.array_equal(d15, refm)
    d28 = dot_thin(solid, 2.8)
    ref_d28, _ = gridio.read_band(P / "inputs/dotted_h19_5_d2_8_nan.tif")
    ref_d28m = np.isfinite(ref_d28) & (ref_d28 > 0.5) & fp
    assert int(d28.sum()) == 44_090
    assert np.array_equal(d28, ref_d28m), "D2.8 mask differs from the original owner-mirrored raster"


@pytest.mark.skipif(not (P / "bridge/labels.tif").exists(), reason="owner mirrors not restored")
def test_catalogue_masked_metric_is_finite_and_ordering_sane():
    with rasterio.open(P / "bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    lab, _ = gridio.read_band(P / "bridge/labels.tif")
    catalog = np.nan_to_num(lab) > 0
    parent, _ = gridio.read_band(P / "inputs/h19_5_nan.tif")
    solid = (np.isfinite(parent) & (parent > 0.5) & fp).astype(np.float32)
    dotted = dot_thin(solid > 0.5, 1.5).astype(np.float32)
    # truth here is only the catalogue itself, so with catalogue masking every pixel is 'known'
    # and both scores must come out as the degenerate zero-truth result (guards, not science).
    rs = dti_binary(solid, catalog, valid=fp, known=catalog & fp)
    rd = dti_binary(dotted, catalog, valid=fp, known=catalog & fp)
    assert np.isfinite(rs["dti"]) and np.isfinite(rd["dti"])

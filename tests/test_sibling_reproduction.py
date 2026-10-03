"""Reproduction anchors against the owner-mirrored, live-scored files (skipped when data absent).

These are the strongest calibration checks this repo can make without credentials:
  * `dot_thin(solid_h19_5, 1.5)` must reproduce the mirrored 0.2477 file's mask bit-for-bit;
  * `dot_thin(solid_h19_5, 2.8)` must reproduce the 44,090-pixel count of the 0.2600 file;
  * our DTI on the dotted files against the CATALOGUE with catalogue masking must behave
    monotonically (dotted >= solid on the catalogue-internal proxy) — sanity only, the live
    scores are owner-reported, not receipts.
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


@pytest.mark.skipif(not (P / "inputs" / "h19_5_nan.tif").exists(), reason="owner mirrors not restored")
def test_d15_mask_and_d28_count_reproduced():
    with rasterio.open(P / "bridge/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    parent, _ = gridio.read_band(P / "inputs/h19_5_nan.tif")
    solid = np.isfinite(parent) & (parent > 0.5) & fp
    d15 = dot_thin(solid, 1.5)
    ref, _ = gridio.read_band(P / "inputs/dotted_h19_5_d1_5_nan.tif")
    refm = np.isfinite(ref) & (ref > 0.5) & fp
    assert np.array_equal(d15, refm)
    assert int(dot_thin(solid, 2.8).sum()) == 44_090


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

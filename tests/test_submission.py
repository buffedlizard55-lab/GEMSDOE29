import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gemsdoe.submission import (
    check_file, content_id, make_filename, make_note, write_submission, zip_single,
)

TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


@pytest.fixture()
def template(tmp_path):
    H, W = 40, 50
    foot = np.zeros((H, W), bool)
    foot[5:35, 8:44] = True
    arr = np.where(foot, 0.0, np.nan).astype(np.float32)
    p = tmp_path / "template.tif"
    prof = dict(driver="GTiff", dtype="float32", count=1, height=H, width=W, crs="EPSG:32611",
                transform=TRANSFORM, nodata=np.nan, compress="lzw")
    with rasterio.open(p, "w", **prof) as d:
        d.write(arr, 1)
    return p, foot


def test_writer_roundtrip_matches_template_grid(template, tmp_path):
    t, foot = template
    pred = np.zeros(foot.shape, np.float32)
    pred[10, 10:30] = 1
    out = write_submission(pred, t, tmp_path / "a.tif")
    with rasterio.open(out) as s, rasterio.open(t) as ts:
        a = s.read(1)
        assert s.crs == ts.crs and s.transform == ts.transform and s.dtypes == ("float32",)
        assert (np.isnan(a) == ~foot).all()
        assert a[10, 10:30].min() == 1.0 and np.nanmax(a) == 1.0 and np.nanmin(a) == 0.0


def test_writer_refuses_nan_inside_footprint_the_original_bug(template, tmp_path):
    t, foot = template
    pred = np.zeros(foot.shape, np.float32)
    pred[~foot] = np.nan
    pred[20, 20] = np.nan  # NaN inside the template footprint is rejected by the local checker
    with pytest.raises(ValueError, match="NaN/Inf"):
        write_submission(pred, t, tmp_path / "bad.tif")


def test_writer_refuses_out_of_range(template, tmp_path):
    t, foot = template
    pred = np.zeros(foot.shape, np.float32)
    pred[12, 12] = 1.0001
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        write_submission(pred, t, tmp_path / "bad.tif")


def test_checker_flags_the_exact_failure_mode_of_the_first_gemsdoe_file(template, tmp_path):
    t, foot = template
    # Reproduce the bad file locally: an invented footprint leaves NaN inside the owner-mirror template footprint.
    fake = np.zeros(foot.shape, np.float32)
    fake[:, :20] = np.nan
    bad = tmp_path / "invented-footprint.tif"
    with rasterio.open(t) as ts:
        prof = ts.profile
    with rasterio.open(bad, "w", **prof) as d:
        d.write(fake, 1)
    r = check_file(bad, t)
    assert not r["ok_to_upload"]
    assert "footprint_all_finite" in r["hard_failures"]


def test_checker_passes_good_files_both_conventions(template, tmp_path):
    t, foot = template
    pred = np.zeros(foot.shape, np.float32)
    pred[15, 10:20] = 0.5
    for outside in ("nan", "zero"):
        out = write_submission(pred, t, tmp_path / f"{outside}.tif", outside=outside)
        r = check_file(out, t)
        # the synthetic template is not the expected competition grid, only that one check may fail
        assert set(r["hard_failures"]) <= {"template_matches_expected_grid_and_footprint"}, r["hard_failures"]
        assert r["positive_pixels"] == 10


def test_zip_contains_exactly_the_tif(template, tmp_path):
    t, foot = template
    out = write_submission(np.zeros(foot.shape, np.float32), t, tmp_path / "z.tif")
    z = zip_single(out)
    import zipfile
    assert zipfile.ZipFile(z).namelist() == ["z.tif"]


def test_content_id_ignores_known_pixels_and_negative_zero():
    foot = np.ones((6, 6), bool)
    known = np.zeros((6, 6), bool)
    known[0, :] = True
    a = np.zeros((6, 6), np.float32)
    b = a.copy()
    b[0, 3] = 1.0  # change only on a known pixel
    c = a.copy()
    c[3, 3] = -0.0
    assert content_id(a, foot, known) == content_id(b, foot, known) == content_id(c, foot, known)
    d = a.copy()
    d[3, 3] = 1.0
    assert content_id(a, foot, known) != content_id(d, foot, known)


def test_note_and_filename_are_short_and_unique():
    n = make_note("D2.8", "Poisson-disk dotted H19-5, 44,090 px", "abcdef123456")
    assert len(n) <= 120 and "abcdef123456" in n
    assert make_filename("Dotted H19-5 d2.8", "20261002", "abcdef123456") == "gemsdoe29-dotted-h19-5-d2-8-20261002-abcdef123456-nan.tif"

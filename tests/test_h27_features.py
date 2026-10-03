import numpy as np

from gemsdoe.features import build_tip_continuation


def test_tip_continuation_is_directed_parallel_and_zero_near_catalogue():
    h = w = 40
    foot = np.ones((h, w), bool)
    visible = np.zeros((h, w), bool)
    visible[20, 8:22] = True  # horizontal 8-connected trace
    # Test all cells so the returned vector can be indexed by the raster's flat coordinates.
    out = build_tip_continuation(visible, foot, np.arange(h * w)).reshape(h, w)
    assert out[20, 26] > 0.0  # beyond the right endpoint, along strike and outward
    assert out[20, 3] > 0.0   # beyond the left endpoint, along strike and outward
    assert out[20, 15] == 0.0  # on the visible catalogue
    assert out[15, 21] == 0.0  # perpendicular to strike
    assert out[16, 25] == 0.0  # not sufficiently strike-parallel
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_tip_continuation_excludes_faults_clipped_at_footprint_edges_and_empty_catalogues():
    h = w = 20
    foot = np.ones((h, w), bool)
    visible = np.zeros((h, w), bool)
    visible[0, 3:15] = True  # both endpoints are clipped by the raster boundary
    original = visible.copy()
    got = build_tip_continuation(visible, foot, np.arange(h * w))
    assert np.count_nonzero(got) == 0
    assert np.array_equal(visible, original)  # feature building must not mutate the caller's catalogue
    empty = build_tip_continuation(np.zeros_like(visible), foot, np.arange(h * w))
    assert np.count_nonzero(empty) == 0


def test_tip_continuation_returns_only_requested_footprint_indices():
    foot = np.ones((20, 20), bool)
    visible = np.zeros_like(foot)
    visible[10, 4:15] = True
    fi = np.array([10 * 20 + 17, 0, 10 * 20 + 10], dtype=np.int64)
    got = build_tip_continuation(visible, foot, fi)
    assert got.shape == fi.shape
    assert got[0] > 0 and got[1] == 0 and got[2] == 0


def test_tip_continuation_rejects_invalid_chunk_and_nonfootprint_indices():
    foot = np.ones((12, 12), bool)
    visible = np.zeros_like(foot)
    visible[6, 2:10] = True
    with np.testing.assert_raises(ValueError):
        build_tip_continuation(visible, foot, np.array([144]))
    foot[0, 0] = False
    with np.testing.assert_raises(ValueError):
        build_tip_continuation(visible, foot, np.array([0]))
    with np.testing.assert_raises(ValueError):
        build_tip_continuation(visible, foot, np.arange(12 * 12), chunk_size=0)
    with np.testing.assert_raises(ValueError):
        build_tip_continuation(visible, foot, np.arange(12 * 12), chunk_size=1.5)
    with np.testing.assert_raises(ValueError):
        build_tip_continuation(visible, foot, np.array([1.5]))

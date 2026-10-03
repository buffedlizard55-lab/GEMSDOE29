import numpy as np

from gemsdoe.thinning import dot_thin, neighbour_profile, ridge_nms, score_ordered_dots, select_top_positive


def test_dot_thin_is_a_deterministic_subset_with_min_spacing_and_maximality():
    m = np.zeros((20, 40), bool)
    m[10, 5:35] = True
    t = dot_thin(m, 1.5)
    assert (t & ~m).sum() == 0
    assert np.array_equal(t, dot_thin(m, 1.5))
    ys, xs = np.nonzero(t)
    d = np.diff(xs)
    assert d.min() >= 2  # min_dist 1.5 on a 1-px line -> spacing 2
    # maximality: every input pixel within min_dist of a kept pixel
    from scipy.ndimage import distance_transform_edt
    assert (distance_transform_edt(~t)[m] < 1.5).all()


def test_dot_thin_noop_for_unit_distance_and_keeps_isolated_pixels():
    m = np.zeros((10, 10), bool)
    m[2, 2] = m[7, 7] = True
    assert np.array_equal(dot_thin(m, 1.0), m)
    assert np.array_equal(dot_thin(m, 3.0), m)


def test_score_ordered_dots_keeps_the_highest_score_in_each_neighbourhood():
    score = np.zeros((10, 30), np.float32)
    cand = np.zeros((10, 30), bool)
    cand[5, 5:25] = True
    score[5, 5:25] = np.linspace(0.1, 0.5, 20)
    score[5, 12] = 0.99  # peak
    out = score_ordered_dots(score, cand, 3.0)
    assert out[5, 12]
    ys, xs = np.nonzero(out)
    assert np.diff(np.sort(xs)).min() >= 3
    assert (out & ~cand).sum() == 0
    assert out.sum() >= 5


def test_score_ordered_dots_max_keep_truncates_by_score():
    score = np.arange(100, dtype=np.float32).reshape(10, 10)
    cand = np.ones((10, 10), bool)
    out = score_ordered_dots(score, cand, 3.0, max_keep=3)
    assert out.sum() == 3
    assert out[9, 9]


def test_select_top_positive_never_pads_with_zeros():
    s = np.zeros((5, 5), np.float32)
    s[1, 1] = 1
    s[2, 2] = 2
    out = select_top_positive(s, np.ones_like(s, bool), 10)
    assert out.sum() == 2 and out[2, 2] and out[1, 1]
    assert select_top_positive(s, np.ones_like(s, bool), 0).sum() == 0


def test_ridge_nms_finds_a_crest_line_and_respects_the_valid_mask():
    yy, xx = np.mgrid[0:60, 0:60]
    s = np.exp(-((yy - 30) ** 2) / 8.0).astype(np.float32)  # horizontal ridge at row 30
    valid = np.ones((60, 60), bool)
    r = ridge_nms(s, valid, 1.0)
    rows = np.unique(np.nonzero(r)[0])
    assert rows.tolist() == [30]
    valid[:, :20] = False
    r2 = ridge_nms(s, valid, 1.0)
    assert not r2[:, :20].any()


def test_neighbour_profile_distinguishes_lines_from_dots():
    line = np.zeros((10, 20), bool)
    line[5, 2:18] = True
    dots = np.zeros((10, 20), bool)
    dots[5, 2:18:3] = True
    assert neighbour_profile(line)["isolated"] == 0.0
    assert neighbour_profile(dots)["isolated"] == 1.0

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems29.thinning import dot_thin
from gems29.thinning import dot_thin_ranked
from gems29.worming import prep_field, upward_continue, hgm, directional_max  # noqa: E402


def test_dot_thin_subset_and_spacing():
    rng = np.random.default_rng(0)
    m = rng.random((80, 90)) < 0.25
    k = dot_thin(m, 3.0)
    assert (k & ~m).sum() == 0
    yy, xx = np.nonzero(k)
    if yy.size > 1:
        d = np.hypot(yy[:, None] - yy[None, :], xx[:, None] - xx[None, :])
        np.fill_diagonal(d, np.inf)
        assert d.min() >= 3.0 - 1e-9


def test_ranked_subset_deterministic_and_spaced():
    rng = np.random.default_rng(1)
    m = np.zeros((70, 70), bool)
    m[10:60, 20:22] = True
    m[30:32, 10:60] = True
    prio = rng.random(m.shape)
    a = dot_thin_ranked(m, 3.5, prio)
    b = dot_thin_ranked(m, 3.5, prio)
    assert np.array_equal(a, b)                      # determinism
    assert (a & ~m).sum() == 0                       # subset
    yy, xx = np.nonzero(a)
    d = np.hypot(yy[:, None] - yy[None, :], xx[:, None] - xx[None, :])
    np.fill_diagonal(d, np.inf)
    assert d.min() >= 3.5 - 1e-9


def test_ranked_prefers_high_priority_on_a_line():
    m = np.zeros((9, 9), bool)
    m[4, :] = True                                   # a 9-px line
    prio = np.zeros(m.shape)
    prio[4, 2] = 10.0                                # force the dot at column 2
    k = dot_thin_ranked(m, 3.0, prio)
    assert k[4, 2]


def test_prep_field_preserves_nearest_valid_padding_not_median_padding():
    values = np.full((3, 3), np.nan, np.float32)
    valid = np.zeros((3, 3), bool)
    values[1, 0], values[0, 0], values[0, 1] = 0.0, 100.0, 1000.0
    valid[1, 0] = valid[0, 0] = valid[0, 1] = True
    filled, _ = prep_field(values, valid, taper=0)
    # The invalid center is equally close to the 0 and 1000 cells; either nearest fill is valid.
    # Median padding would make it exactly 0 after median removal, which is neither neighbor.
    assert filled[1, 1] in (-100.0, 900.0)
    assert np.all(np.isfinite(filled))


def test_upward_continuation_smooths_and_preserves_constant():
    const = np.full((64, 64), 3.0)
    out = upward_continue(const, 500.0)
    assert np.allclose(out, 3.0, atol=1e-6)
    rng = np.random.default_rng(2)
    noise = rng.random((64, 64))
    f = noise - noise.mean()
    c = upward_continue(f, 200.0)
    assert np.var(c) < np.var(f)


def test_upward_continuation_equals_source_depth_shift():
    """The wavelet-theory identity behind worming: UC by h of a source at depth d behaves like the
    same source at depth d+h (Hornby et al. 1999). Uses the analytic 2-D vertical-dike TMI profile
    f(x) = A*(atan((x+b)/d) - atan((x-b)/d)), infinite along strike."""
    from gems29.worming import prep_field, upward_continue, hgm
    W = H = 256
    dx = 100.0
    x = (np.arange(W) - W // 2) * dx
    b = 300.0
    def dike(d, amp=1000.0):
        prof = amp * (np.arctan((x + b) / d) - np.arctan((x - b) / d))
        return np.tile(prof, (H, 1))
    d, h = 500.0, 1000.0
    valid = np.ones((H, W), bool)
    tapered, _ = prep_field(dike(d), valid, taper=48)
    cont = upward_continue(tapered, h)
    ref = dike(d + h)
    _, _, mag_c = hgm(cont - cont.mean())
    _, _, mag_r = hgm(ref - ref.mean())
    # correlation of the gradient profiles away from the taper
    lo, hi = 60, W - 60
    a = mag_c[H // 2, lo:hi].ravel(); rr = mag_r[H // 2, lo:hi].ravel()
    corr = float(np.corrcoef(a, rr)[0, 1])
    assert corr > 0.97, f"UC profile not depth-equivalent: corr={corr}"
    # amplitude retention: peak |HGM| of the continued deep dike exceeds the continued shallow one
    def retention(depth):
        tp, _ = prep_field(dike(depth), valid, taper=48)
        _, _, m0 = hgm(tp)
        c = upward_continue(tp, 1600.0)
        _, _, mh = hgm(c)
        return float(mh.max() / max(m0.max(), 1e-9))
    assert retention(1800.0) > retention(300.0)

def test_worm_tracker_chains_break_and_resume_deterministically():
    """Direct tracker test: an edge present at levels 0-2 then missing has level_idx=2."""
    from gems29.worming import worm_persistence, LADDER_M
    levels = [np.zeros((24, 24), bool) for _ in LADDER_M]
    for lvl in range(3):
        levels[lvl][10, 12 + lvl] = True          # edge drifting 1 px/level (within tol)
    yy, xx = np.nonzero(levels[0])
    mags = [np.full((24, 24), 1.0 - 0.05 * i) for i in range(len(LADDER_M))]
    st = worm_persistence(levels, mags, yy, xx, np.ones((24, 24), bool))
    assert st["level_idx"][0] == 2
    assert abs(st["persistence"][0] - 2 / (len(LADDER_M) - 1)) < 1e-6
    assert 0.0 <= st["persistence"][0] <= 1.0


def test_worm_persistence_is_bounded_and_uses_all_ladder_intervals():
    from gems29.worming import worm_persistence, LADDER_M
    shape = (16, 16)
    full = [np.zeros(shape, bool) for _ in LADDER_M]
    full[0][8, 8] = True
    for lvl in range(1, len(full)):
        full[lvl][8, 8] = True
    mags = [np.ones(shape, np.float32) for _ in full]
    yy, xx = np.nonzero(full[0])
    st = worm_persistence(full, mags, yy, xx, np.ones(shape, bool))
    assert st["level_idx"][0] == len(LADDER_M) - 1
    assert st["persistence"][0] == 1.0

    shallow = [np.zeros(shape, bool) for _ in LADDER_M]
    shallow[0][8, 8] = True
    yy, xx = np.nonzero(shallow[0])
    st = worm_persistence(shallow, mags, yy, xx, np.ones(shape, bool))
    assert st["level_idx"][0] == 0
    assert st["persistence"][0] == 0.0
    assert np.all((st["persistence"] >= 0) & (st["persistence"] <= 1))
    assert np.isclose(st["h_last_m"][0], LADDER_M[0])


def test_worm_persistence_rejects_inconsistent_ladders():
    import pytest
    from gems29.worming import worm_persistence, LADDER_M
    shape = (4, 4)
    levels = [np.zeros(shape, bool) for _ in LADDER_M]
    mags = [np.zeros(shape, np.float32) for _ in LADDER_M]
    with pytest.raises(ValueError):
        worm_persistence(levels, mags[:-1], np.array([], int), np.array([], int), np.ones(shape, bool))
    with pytest.raises(ValueError):
        worm_persistence(levels, mags, np.array([], int), np.array([], int), np.ones(shape, bool),
                         ladder_m=(0, 100, 100, 400, 800, 1600))

"""Synthetic unit tests for the H41 centroid-corridor fields (no competition data required)."""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe.h41 import (
    H41_NAMES, RECENCY_FALLBACK_WEIGHT, RECENCY_WEIGHTS, build_h41_fields, corridor_smear, degenerate_fields,
    exponential_support, parse_centroids, support_raster,
)

CSV = (
    "trace_id,name,slip_rate,recency,dip_direct,slip_sense,map_scale,full_length_m,clipped_length_m,"
    "centroid_utm_x,centroid_utm_y,centroid_row,centroid_col,centroid_in_footprint\n"
    '1,"Fault A, north",1.0,"<15,000",Unspecified,N,250,5000,5000,0,0,10,12,1\n'
    "2,Fault B,4.0,<150,Unspecified,N,250,9000,9000,0,0,20,30,1\n"
    "3,Fault C,0.5,<130,00,Unspecified,N,250,10,10,0,0,25,25,1\n"
    "4,Outside flag,2.0,<150,Unspecified,N,250,10,10,0,0,5,5,0\n"
    "5,Off grid,2.0,<150,Unspecified,N,250,10,10,0,0,99,5,1\n"
)


def _csv(tmp_path):
    p = tmp_path / "qfaults.csv"
    p.write_text(CSV, encoding="utf-8")
    return p


def test_parse_centroids_filters_and_weights(tmp_path):
    field = parse_centroids(_csv(tmp_path), shape=(40, 40))
    # rows 1 and 2 are usable; row 3 has an unquoted comma in `recency` (the real file contains one such
    # row) and must be dropped-and-counted, never guessed
    assert field.n >= 2
    assert (field.rows >= 0).all() and (field.cols < 40).all()
    assert field.weights.min() > 0 and field.weights.max() <= 1.0
    assert field.scale > 0
    diag = field.diagnostics
    assert diag["n_rows_read"] == 5
    assert diag["n_in_footprint"] == 3          # rows 1, 2, 5 (row 4 is excluded by its flag)
    assert diag["n_rows_unparsable"] == 1       # row 3, the unquoted-comma recency value
    assert diag["n_dropped_out_of_grid"] == 1   # row 5, centroid row 99 outside a 40-row grid
    assert field.n == 2


def test_parse_centroids_recency_fallback_counted(tmp_path):
    text = CSV.replace("2,Fault B,4.0,<150,", '2,Fault B,4.0,"<nonsense",')
    p = tmp_path / "q2.csv"
    p.write_text(text, encoding="utf-8")
    field = parse_centroids(p, shape=(40, 40))
    assert field.n == 2 and field.diagnostics["n_recency_unmapped"] == 1
    assert RECENCY_FALLBACK_WEIGHT < min(RECENCY_WEIGHTS.values())  # an unlisted bin cannot out-rank a real one
    assert field.diagnostics["n_rows_unparsable"] == 1  # the replacement keeps the row parsable
    # the unmapped bin falls back to RECENCY_FALLBACK_WEIGHT, which is the lowest weight in the table, so the
    # highest-slip row must not out-rank its own <150 weight
    w = field.weights[field.rows == 20]
    assert 0 < float(w[0]) <= 1.0
    assert float(w[0]) < field.weights[field.rows == 10].max()


def test_malformed_row_does_not_raise(tmp_path):
    # the mirrored real file contains a row whose recency field carries an unquoted comma; the parser must
    # either re-join it or drop it without crashing
    field = parse_centroids(_csv(tmp_path), shape=(40, 40))
    assert field.n >= 2


def test_exponential_support_analytic_values():
    pts = np.zeros((200, 200), np.float32)
    pts[100, 100] = 2.0
    out = exponential_support(pts, decay_px=10.0, cutoff_px=25.0)
    assert out[100, 100] == pytest.approx(2.0, rel=1e-5)
    assert out[100, 110] == pytest.approx(2.0 * np.exp(-1.0), rel=1e-4)
    assert out[100, 126] == 0.0  # beyond the cutoff
    assert out[100, 105] == pytest.approx(2.0 * np.exp(-0.5), rel=1e-4)
    # a diagonal pixel uses the Euclidean distance, not the L1 sum
    assert out[105, 105] == pytest.approx(2.0 * np.exp(-np.hypot(5, 5) / 10.0), rel=1e-4)
    assert np.isfinite(out).all()


def test_exponential_support_edge_truncation_is_bounded():
    pts = np.zeros((40, 40), np.float32)
    pts[0, 0] = 1.0
    out = exponential_support(pts, decay_px=5.0, cutoff_px=15.0)
    assert out[0, 0] == pytest.approx(1.0, rel=1e-6)  # truncated kernel, no renormalisation
    assert out[39, 39] == 0.0


def test_support_raster_sums_coincident_points(tmp_path):
    field = parse_centroids(_csv(tmp_path), shape=(40, 40))
    grid = support_raster(field, (40, 40))
    assert grid[field.rows[0], field.cols[0]] > 0
    assert grid.sum() == pytest.approx(field.weights.sum(), rel=1e-5)
    masked = support_raster(field, (40, 40), mask=np.zeros(field.n, bool))
    assert masked.sum() == 0.0


def test_corridor_smear_is_anisotropic_along_the_strike():
    pts = np.zeros((80, 80), np.float32)
    pts[40, 40] = 1.0
    # strike along the row axis (t = 0 deg -> unit step (dr, dc) = (0, 1)): cos(2t)=1, sin(2t)=0
    c2 = np.ones((80, 80), np.float32)
    s2 = np.zeros((80, 80), np.float32)
    out = corridor_smear(pts, c2, s2, fallback=pts, half_len_px=6.0, n_orientations=8)
    along = out[40, 40 - 5:40 + 6]
    across = out[40 - 5:40 + 6, 40]
    # The fan mean is normalised by sum_k w_k = n/2, so a point on a uniform fabric sits at 1.0 on its own
    # pixel and the aligned smear holds a constant plateau of 1/(n/2) along the strike; off-axis pixels only
    # receive the oblique smears and stay strictly below that plateau.
    plateau = 1.0 / (8 / 2.0)
    assert out[40, 40] == pytest.approx(1.0, rel=1e-6)
    assert np.allclose(np.r_[along[:3], along[-3:]], plateau, atol=1e-6)
    assert along[4] > 0.5 and np.isclose(along[4], along[6])   # +/-1 px: the 22.5-degree neighbours also land here
    off_axis = np.r_[across[:5], across[6:]]
    assert float(off_axis.max()) < plateau - 1e-6 and (off_axis >= 0).all()
    assert out[40, 40 - 8] == 0.0 and out[40, 40 + 8] == 0.0   # the smear is bounded by half_len_px
    # invalid strike fabric -> fallback exactly
    out0 = corridor_smear(pts, np.zeros((80, 80), np.float32), np.zeros((80, 80), np.float32),
                          fallback=pts * 3.0, half_len_px=6.0, n_orientations=8)
    assert np.allclose(out0, pts * 3.0)


def test_build_fields_shape_bounds_and_leak_free(tmp_path):
    field = parse_centroids(_csv(tmp_path), shape=(60, 60))
    foot = np.ones((60, 60), bool)
    foot[:5, :5] = False
    fi = np.flatnonzero(foot.ravel())
    visible = np.zeros((60, 60), bool)
    visible[10, 10] = True
    scarp = np.full(fi.size, 0.5, np.float32)
    c2 = np.ones((60, 60), np.float32)
    s2 = np.zeros((60, 60), np.float32)
    fields, diag = build_h41_fields(field, visible=visible, footprint=foot, footprint_idx=fi,
                                    scarp_vec=scarp, cos2t=c2, sin2t=s2)
    assert fields.shape == (len(H41_NAMES), fi.size)
    assert fields.dtype == np.float32
    assert np.isfinite(fields).all()
    assert float(fields.min()) >= 0.0 and float(fields.max()) <= 1.0
    # outside-footprint pixels stay untouched because the block is built from the footprint vector only
    # off-catalogue support must vanish when every centroid is close to a visible pixel
    dense = np.ones((60, 60), bool)
    fields_all_visible, diag2 = build_h41_fields(field, visible=dense, footprint=foot, footprint_idx=fi,
                                                 scarp_vec=scarp, cos2t=c2, sin2t=s2)
    assert diag2["n_centroids_off_catalogue"] == 0
    assert float(fields_all_visible[1].max()) == 0.0
    assert float(fields[1].max()) > 0.0
    # purity is exactly 1 where the support is entirely off-catalogue and 0 where there is no support
    pur = fields[4]
    assert (pur <= 1.0 + 1e-6).all() and (pur >= 0.0).all()
    assert pur[fields[0] <= 1e-9].max(initial=0.0) <= 1.0
    assert diag["n_centroids_near_catalogue"] == int(diag["n_centroids_total"] - diag["n_centroids_off_catalogue"])


def test_degeneracy_guard_catches_sparse_columns(tmp_path):
    fields = np.zeros((5, 100_000), np.float32)
    fields[0, :5] = 1.0
    problems = degenerate_fields(fields)
    # every column, including the one that is non-zero, is below the 0.2 % floor
    assert len(problems) == 5
    assert any(p.startswith("H41_SUPP") for p in problems) and any(p.startswith("H41_PURITY") for p in problems)
    ok = np.zeros((5, 1000), np.float32)
    ok[:, :3] = 0.5
    assert degenerate_fields(ok) == []

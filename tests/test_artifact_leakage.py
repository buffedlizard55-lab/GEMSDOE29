"""Regression tests for IR-29-ARTIFACT-LEAK (knowledge/33).

The published repo-c0 artifact model separated its own training labels perfectly through a
distance-to-catalogue column, so it used 2 of 81 features and any new physics column was inert. These
tests pin the mechanism and the guards that now prevent it recurring silently.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.features import build_catalogue_features  # noqa: E402
from gemsdoe.h41 import H41_NAMES  # noqa: E402

CROSSFIT = ROOT / "scripts" / "build_crossfit_candidate.py"
REPO_CANDIDATE = ROOT / "scripts" / "build_repo_candidate.py"


def test_catalogue_distance_column_is_exactly_zero_on_the_catalogue() -> None:
    """The root cause: family E's first column is a perfect training-label look-up.

    Positives in ``build_repo_candidate.training_sample`` are exactly the catalogue pixels, so this column
    is 0.0 for every positive while negatives are sampled more than 1.5 px away. Any model trained with
    ``E`` built from the same catalogue it is predicting can therefore reach train AUC 1.0 on one split
    and never look at another feature. This test exists so that fact stays visible.
    """
    mask = np.zeros((40, 60), bool)
    mask[10:14, 20:34] = True  # a small "fault"
    E = build_catalogue_features(mask, np.flatnonzero(np.ones_like(mask).ravel()))
    dist = E[0]
    on = dist[mask.ravel()]
    off = dist[(~mask).ravel()]
    assert on.size == int(mask.sum())
    assert np.all(on == 0.0), "distance column must be exactly 0 on the catalogue - this is the leak"
    # negatives in the artifact sampler sit > 1.5 px away, so log1p(dist) >= log1p(2) > 1.09 for them;
    # the nearest non-catalogue pixel is at dist 1, giving log1p(1) = 0.693 > 0. Either way the two
    # classes are perfectly separated by this one column.
    assert float(off.min()) > 0.0
    assert float(off.max()) > 1.0


def test_crossfit_builder_aborts_on_an_inert_h41_block() -> None:
    """The guard that build_repo_candidate.py lacked: zero H41 splits must abort the build."""
    src = CROSSFIT.read_text()
    assert "h41_split_total == 0" in src
    assert "degeneracy guard" in src.lower()
    assert "Refusing to write a candidate that does not implement its own method" in src


def test_crossfit_builder_aborts_when_the_arms_are_indistinguishable() -> None:
    src = CROSSFIT.read_text()
    assert 'base["content_id"] == a4["content_id"]' in src
    assert "the H41 columns are still inert" in src


def test_crossfit_builder_trains_on_the_hidden_set_not_the_full_catalogue() -> None:
    """Training features must come from ``draw.visible``; only prediction may use the full catalogue."""
    src = CROSSFIT.read_text()
    assert "build_catalogue_features(d.visible, ctx.fi)" in src
    assert "build_tip_continuation(d.visible, ctx.foot, ctx.fi)" in src
    assert "visible=d.visible" in src
    assert "ctx.vec(d.hidden_train)" in src
    assert "777 + 31 * fold + seed" in src, "negative-sampling seed must match Cell.__init__"


def test_crossfit_arm_definition_matches_the_preregistered_a4_union() -> None:
    """A4_h41_union is 'all five' H41 columns (knowledge/24 section 3 table)."""
    src = CROSSFIT.read_text()
    assert '"A4_h41_union": list(range(len(H41_NAMES)))' in src
    assert '"C0_base": []' in src
    assert len(H41_NAMES) == 5


def test_deprecated_single_fit_builder_is_marked() -> None:
    """The defective path stays in the tree for provenance but must warn loudly."""
    src = REPO_CANDIDATE.read_text()
    assert "Do not use this script to produce a new artifact" in src
    assert "IR-29-ARTIFACT-LEAK" in src
    assert "knowledge/33_artifact_leakage_and_crossfit_2026-10-03.md" in src


def test_irregularity_is_registered_with_its_measurements() -> None:
    import json

    reg = json.loads((ROOT / "registry" / "irregularities.json").read_text())
    item = next(i for i in reg["items"] if i["id"] == "IR-29-ARTIFACT-LEAK")
    assert item["severity"] == "high"
    assert "only 2 distinct columns used across all 100 trees" in item["detail"]
    assert "3537e9fc47a46503" in item["detail"]
    assert reg["updated"] == "2026-10-03"

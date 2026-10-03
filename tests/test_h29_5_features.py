import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems29.features import add_h29_5_interactions  # noqa: E402


def toy_features():
    return {
        "worm_joint_persist": np.array([[1.0, 1.0], [0.5, 0.8]], np.float32),
        "worm_joint_defined": np.array([[1.0, 0.0], [1.0, 1.0]], np.float32),
        "worm_joint_strength_ratio": np.array([[2.0, 2.0], [1.0, 2.0]], np.float32),
        "raw_geod_2ndinv": np.array([[0.8, 1.0], [0.0, 0.3]], np.float32),
        "raw_geod_shearrate": np.array([[0.2, 0.2], [0.8, 0.3]], np.float32),
        "raw_geod_dilatationrate": np.array([[0.4, 0.4], [0.3, 0.5]], np.float32),
        "raw_deq_n100a15": np.array([[0.25, 1.0], [0.4, 0.8]], np.float32),
        "raw_ieq_n100a15": np.array([[1.0, 1.0], [1.0, 0.5]], np.float32),
    }


def test_h29_5_features_are_exact_interactions_and_masked():
    feats = toy_features()
    valid = np.array([[1, 1], [1, 0]], bool)
    names = add_h29_5_interactions(feats, valid)
    assert names == ["h29_5_worm_strain", "h29_5_worm_dep_eq", "h29_5_worm_ind_eq",
                     "h29_5_corridor_interaction"]
    # Cell 00: persistence=1, normalized retention=1, strain=max(.8,.2,.4)=.8,
    # dependent density=.25 and independent density=1.
    assert np.isclose(feats["h29_5_worm_strain"][0, 0], 0.8)
    assert np.isclose(feats["h29_5_worm_dep_eq"][0, 0], 0.25)
    assert np.isclose(feats["h29_5_worm_ind_eq"][0, 0], 1.0)
    assert np.isclose(feats["h29_5_corridor_interaction"][0, 0], 0.4)
    # No level-0 worm evidence or outside template footprint => no interaction.
    assert all(feats[name][0, 1] == 0.0 for name in names)
    assert all(feats[name][1, 1] == 0.0 for name in names)
    for name in names:
        assert feats[name].dtype == np.float32
        assert np.isfinite(feats[name]).all()
        assert np.all((feats[name] >= 0.0) & (feats[name] <= 1.0))


def test_h29_5_rejects_missing_features_and_shape_mismatch():
    feats = toy_features()
    feats.pop("raw_ieq_n100a15")
    with pytest.raises(ValueError, match="missing features"):
        add_h29_5_interactions(feats, np.ones((2, 2), bool))
    feats = toy_features()
    feats["raw_ieq_n100a15"] = np.zeros((1, 1), np.float32)
    with pytest.raises(ValueError, match="shapes"):
        add_h29_5_interactions(feats, np.ones((2, 2), bool))

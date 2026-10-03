import hashlib

from scripts.verify_downloads import receipt_after_verification, verify_build_hashes


def test_hash_mismatch_cannot_rebase_build_receipt(tmp_path):
    stem = "candidate"
    name = f"{stem}-nan.tif"
    expected_bytes = b"original artifact"
    actual_bytes = b"modified artifact"
    (tmp_path / name).write_bytes(actual_bytes)
    baseline = {name: {
        "bytes": len(expected_bytes),
        "sha256": hashlib.sha256(expected_bytes).hexdigest(),
    }}

    checks, observed = verify_build_hashes(tmp_path, stem, baseline)
    assert checks[f"sha256_receipt:{name}"]["pass"] is False
    assert observed[name]["sha256"] == hashlib.sha256(actual_bytes).hexdigest()

    checks["__summary__"] = {"pass": False, "detail": "hash mismatch"}
    updated = receipt_after_verification(baseline | {"files": baseline}, stem, checks, observed, "now")
    assert updated["files"] == baseline

    # A second verifier run still compares with the original build-time hash and still fails.
    checks_again, _ = verify_build_hashes(tmp_path, stem, updated["files"])
    assert checks_again[f"sha256_receipt:{name}"]["pass"] is False


def test_missing_baseline_hash_fails_closed(tmp_path):
    stem = "candidate"
    name = f"{stem}-nan.tif"
    (tmp_path / name).write_bytes(b"artifact")
    checks, observed = verify_build_hashes(tmp_path, stem, {})
    assert checks[f"sha256_receipt:{name}"]["pass"] is False
    assert "no build-time SHA-256" in checks[f"sha256_receipt:{name}"]["detail"]
    assert name in observed

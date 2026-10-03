#!/usr/bin/env python3
"""Independently verify the H29 WORMRANK and REFD28 TIFF/ZIP downloads."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from gems29.submission import sha256_file, verify_files  # noqa: E402


FILE_SUFFIXES = ("-nan.tif", "-zeros.tif", "-nan.zip")


def verify_build_hashes(dl: Path, stem: str, expected_files: dict) -> tuple[dict, dict]:
    """Compare published files to immutable build-time hashes; return checks and observations."""
    checks: dict[str, dict] = {}
    observed: dict[str, dict] = {}
    for suffix in FILE_SUFFIXES:
        name = f"{stem}{suffix}"
        path = dl / name
        key = f"sha256_receipt:{name}"
        if not path.is_file():
            checks[key] = {"pass": False, "detail": "missing file"}
            continue
        actual = sha256_file(path)
        observed[name] = {"bytes": path.stat().st_size, "sha256": actual}
        baseline = expected_files.get(name)
        if not isinstance(baseline, dict) or not baseline.get("sha256"):
            checks[key] = {"pass": False, "detail": "no build-time SHA-256 in receipt"}
        else:
            expected = baseline["sha256"]
            checks[key] = {"pass": bool(actual == expected),
                           "detail": f"actual={actual}, build_receipt={expected}"}
    return checks, observed


def receipt_after_verification(old: dict, stem: str, checks: dict,
                               observed_files: dict, verified_at: str) -> dict:
    """Add current verification without replacing the immutable build-time file hashes."""
    return {
        **old,
        "stem": stem,
        "local_format_verified": bool(checks.get("__summary__", {}).get("pass", False)),
        "organizer_portal_acceptance": "not verified; owner must upload manually",
        "independent_verification": "scripts/verify_downloads.py",
        "independent_verification_utc": verified_at,
        "independent_verification_files": observed_files,
        "checks": checks,
        # `files` is the build-time baseline. Never refresh it after observing a mismatch; doing so
        # would let a later verifier run silently bless a corrupted or replaced artifact.
        "files": old.get("files", {}),
    }


def main() -> int:
    dl = ROOT / "docs" / "downloads"
    ledger = json.loads((ROOT / "registry" / "artifact_ledger.json").read_text())
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    failures = 0
    verified_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    # The repository ledger also records H31/H34/factorial reports and C0 candidates that use
    # separate receipt tooling; this verifier is scoped to the two H29 builds it creates.
    for key in ("WORMRANK", "REFD28"):
        art = ledger.get("artifacts", {}).get(key, {})
        stem = art.get("stem")
        if not stem:
            print(f"{key}: missing artifact stem in artifact ledger")
            failures += 1
            continue
        checks = verify_files(dl, stem, foot_mask=foot, expected_px=art.get("px"))
        receipt_path = dl / f"checks-{stem}.json"
        old = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        expected_files = old.get("files", {})
        hash_checks, observed_files = verify_build_hashes(dl, stem, expected_files)
        checks.update(hash_checks)
        n_fails = sum(not c["pass"] for name, c in checks.items() if name != "__summary__")
        checks["__summary__"] = {"pass": n_fails == 0,
                                 "detail": f"{len(checks)} checks, {n_fails} failures"}
        receipt = receipt_after_verification(old, stem, checks, observed_files, verified_at)
        receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        failures += n_fails
        print(f"{key}: {len(checks)} checks, fails={n_fails}")
    print("verify_downloads:", "ALL LOCAL CHECKS PASS" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

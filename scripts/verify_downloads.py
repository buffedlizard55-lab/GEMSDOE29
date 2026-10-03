#!/usr/bin/env python3
"""Independently verify the registered candidate TIFF/ZIP downloads against the local template.

Two scopes, both local-only:

* the two H29 builds (WORMRANK, REFD28): re-check the published files against the build-time hashes recorded in
  ``docs/downloads/checks-<stem>.json`` (never refreshing the baseline) and rewrite only the verification fields;
* every artifact registered in ``registry/submissions.json``: run the strict ``gemsdoe.submission.check_file``
  against the resolved template, confirm the ``.zip`` companion contains exactly the same GeoTIFF bytes, and
  record the outcome in ``evidence/format_checks/registered_downloads_recheck.json`` (a separate file, so no
  build-time baseline is ever rewritten).
"""
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
from gemsdoe.paths import template_path  # noqa: E402


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
    # One shared resolver for both restore layouts (IR-29-CHECK-TEMPLATE-ROOT): this script used to
    # hard-code data/bridge/, which an H31-group restore does not create.
    template = template_path()
    if not template.is_file():
        print(f"verify_downloads: template not found ({template}); restore the hash-pinned inputs first")
        return 1
    print(f"verify_downloads: using template {template.relative_to(ROOT)}")
    with rasterio.open(template) as ds:
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

    failures += verify_registered(dl, template)
    print("verify_downloads:", "ALL LOCAL CHECKS PASS" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


def verify_registered(downloads_dir: Path, template: Path) -> int:
    """Strict template check plus ZIP-integrity check for every entry in registry/submissions.json.

    Read-only with respect to the build-time receipts: the outcome goes to a separate evidence file so a later
    verifier run can never bless a replaced artifact by rewriting its baseline.
    """
    import zipfile

    from gemsdoe.submission import check_file  # local import: keeps the H29 scope above dependency-light

    submissions = json.loads((ROOT / "registry" / "submissions.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    failures = 0
    for entry in submissions.get("files", []):
        path = Path(entry.get("path", ""))
        tif = path if path.is_absolute() else ROOT / path
        record = dict(id=entry.get("id"), file=entry.get("file"), slot_approved=bool(entry.get("slot_approved")),
                      path=str(path), present=tif.is_file())
        if not tif.is_file():
            record.update(ok=False, detail="registered artifact missing from this checkout")
            failures += 1
        else:
            result = check_file(tif, template)
            zip_path = tif.with_suffix(".zip")
            if zip_path.is_file():
                with zipfile.ZipFile(zip_path) as archive:
                    names = archive.namelist()
                    zip_ok = bool(names == [tif.name] and archive.read(tif.name) == tif.read_bytes())
                zip_detail = "single member, byte-identical to the GeoTIFF" if zip_ok else "ZIP does not match the GeoTIFF"
            else:
                # The portal accepts a bare .tif; a missing companion is not a defect unless one is published
                # and corrupt, so this is recorded as not-applicable rather than counted as a failure.
                zip_ok, zip_detail = None, "no .zip companion published for this artifact"
            record.update(
                ok=bool(result["ok_to_upload"]) and zip_ok is not False,
                ok_to_upload=bool(result["ok_to_upload"]),
                sha256=result["sha256"], bytes=result["bytes"],
                positive_pixels=result.get("positive_pixels"),
                hard_failures=result.get("hard_failures", []),
                zip_ok=zip_ok, zip_detail=zip_detail,
            )
            if not record["ok"]:
                failures += 1
        rows.append(record)
        print(f"  {record['id']}: {'ok' if record['ok'] else 'FAIL'} "
              f"(ok_to_upload={record.get('ok_to_upload')}, zip={record.get('zip_ok')})")
    out = ROOT / "evidence" / "format_checks" / "registered_downloads_recheck.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(
        schema_version=1,
        checked_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        checker="scripts/verify_downloads.py::verify_registered",
        template=str(template.relative_to(ROOT)),
        n_registered=len(rows), n_ok=sum(1 for row in rows if row["ok"]), files=rows,
        note=("Local checks only: they cannot authenticate the owner-mirror template or guarantee organizer "
              "acceptance, and they never rewrite a build-time receipt."),
    ), indent=2, allow_nan=False) + "\n")
    print(f"registered downloads: {sum(1 for row in rows if row['ok'])}/{len(rows)} ok -> {out.relative_to(ROOT)}")
    return failures


if __name__ == "__main__":
    sys.exit(main())

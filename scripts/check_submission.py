#!/usr/bin/env python3
"""Check a GeoTIFF against the local competition template and optionally write a hash receipt.

This verifier reads local files only. It does not upload or contact DrivenData.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.paths import template_path  # noqa: E402
from gemsdoe.submission import check_file, sha256_file  # noqa: E402


def default_template_path() -> Path:
    """Return the template path, honouring whichever restore layout is actually on disk.

    The resolution lives in :func:`gemsdoe.paths.template_path` so that ``scripts/verify_downloads.py`` and
    any future checker agree on one answer (both layouts are real: see IR-29-CHECK-TEMPLATE-ROOT).
    """
    return template_path()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="GeoTIFF to check")
    parser.add_argument("--template", type=Path, default=None,
                        help="defaults to GEMS_DATA_DIR/bridge/sample_submission.tif when present, else "
                             "GEMS_DATA_DIR/sample_submission.tif (the H31-group restore location)")
    parser.add_argument("--receipt", type=Path, default=None, help="optional JSON receipt path")
    args = parser.parse_args()
    template = args.template or default_template_path()
    if not args.path.is_file():
        parser.error(f"GeoTIFF not found: {args.path}")
    if not template.is_file():
        parser.error(f"template not found: {template}; restore the hash-pinned core inputs first")
    result = check_file(args.path, template)
    receipt = {
        "schema_version": 1,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "checker": "gemsdoe.submission.check_file",
        "input": str(args.path),
        "input_sha256": sha256_file(args.path),
        "template": str(template),
        "template_sha256": sha256_file(template),
        "provenance_note": "Local check against the restored owner-mirror template; neither template nor result is organizer-authenticated.",
        "result": result,
    }
    print(json.dumps(receipt, indent=2))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"receipt written: {args.receipt}")
    return 0 if result["ok_to_upload"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

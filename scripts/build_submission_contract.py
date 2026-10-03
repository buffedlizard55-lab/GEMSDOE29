#!/usr/bin/env python3
"""Write the locally verified official submission contract used by the Pages builder.

All numeric terms were transcribed during the dated official-source review; this script is offline.
It does not contact DrivenData, inspect a leaderboard, or claim portal acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = {
    "schema_version": 1,
    "generated_by": "scripts/build_submission_contract.py",
    "verified_local_date": "2026-10-03",
    "source_ids": ["dd-problem", "dd-rules"],
    "provenance": (
        "Official submission/metric facts transcribed from the linked competition page and NLR rules; "
        "manually checked in the 2026-10-03 source review. No leaderboard or DrivenData API was accessed."
    ),
    "format": {
        "band_count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "pixel_size_m": 100,
        "probability_min": 0.0,
        "probability_max": 1.0,
        "outside_footprint": "NaN",
    },
    # Observed portal behaviour, owner-reported 2026-10-03 (IR-PORTAL-01). This does NOT contradict the
    # official format above: the sample template is null/NaN outside the data bounds, but the upload form
    # validates the whole array against [0, 1] and rejects NaN. Both files are published; the zero-outside
    # one is the recommended upload, and the site says so wherever it mentions the outside-footprint rule.
    "portal_validation": {
        "observed_local_date": "2026-10-03",
        "rejection_message_owner_reported": "Predicted values must be in range [0, 1]",
        "reproduced_locally": "the NaN-outside raster fails a strict whole-array [0,1] check and the "
                              "zero-outside raster of the same emission passes it (scripts/check_submission.py)",
        "recommended_upload": "the zero-outside variant of every artifact",
        "irregularity_id": "IR-PORTAL-01",
    },
    "metric": {"support_radius_m": 300, "alpha": 0.2, "beta": 0.8},
    "rules": {
        "rules_year": 2026,
        "weekly_feedback_max": 3,
        "final_prediction_count": 1,
        "prize_round_count": 2,
        "ai_use_disclosure_required_when_applicable": True,
    },
}


def main() -> int:
    sources = json.loads((ROOT / "registry" / "sources.json").read_text(encoding="utf-8"))
    source_ids = {source.get("id") for source in sources.get("sources", [])}
    missing = set(CONTRACT["source_ids"]) - source_ids
    if missing:
        raise SystemExit(f"contract references missing source ids: {sorted(missing)}")
    out = ROOT / "registry" / "submission_contract.json"
    out.write_text(json.dumps(CONTRACT, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} from the offline verified-source register")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Check generated Pages links, local data registers, and score-claim boundaries."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
fail = 0
pages = [
    ROOT / "index.html",
    DOCS / "index.html",
    DOCS / "executive-summary.html",
    DOCS / "research.html",
    DOCS / "status.html",
    DOCS / "sources.html",
    DOCS / "irregularities.html",
]
claim_values = ("0.3195", "0.2941", "0.2477", "0.2600")

for page in pages:
    if not page.is_file():
        print(f"MISSING PAGE {page.relative_to(ROOT)}")
        fail += 1
        continue
    text = page.read_text(encoding="utf-8")
    if re.search(r"\bTODO\b|\bFIXME\b|lorem ipsum", text, re.I):
        print(f"PLACEHOLDER TEXT in {page.relative_to(ROOT)}")
        fail += 1

    if page != DOCS / "irregularities.html":
        leaked = [value for value in claim_values if value in text]
        if leaked:
            print(f"UNVERIFIED COMPETITION SCORE CLAIM in {page.relative_to(ROOT)}: {leaked}")
            fail += 1

    for match in re.finditer(r'(?:href|src)="([^"#]+)"', text):
        ref = html.unescape(match.group(1))
        parts = urlsplit(ref)
        if parts.scheme or parts.netloc or ref.startswith(("mailto:", "data:")):
            continue
        target = (page.parent / parts.path).resolve()
        if not target.exists():
            print(f"BROKEN LOCAL LINK in {page.relative_to(ROOT)}: {ref}")
            fail += 1

    if re.search(r'href=["\'][^"\']*leaderboard', text, flags=re.IGNORECASE):
        print(f"LEADERBOARD LINK in {page.relative_to(ROOT)}")
        fail += 1

json_paths = [
    ROOT / "data" / "manifest.json",
    ROOT / "registry" / "sources.json",
    ROOT / "registry" / "irregularities.json",
    ROOT / "registry" / "submissions.json",
    ROOT / "registry" / "status_feed.json",
    ROOT / "registry" / "hypotheses.json",
    ROOT / "registry" / "artifact_ledger.json",
    ROOT / "registry" / "score_claims.json",
    ROOT / "registry" / "submission_contract.json",
    ROOT / "registry" / "data_manifest.json",
]
for path in json_paths:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"BAD JSON {path.relative_to(ROOT)}: {exc}")
        fail += 1

try:
    status = json.loads((ROOT / "registry" / "status_feed.json").read_text(encoding="utf-8"))
    screen = status["current"]["screen_status"]
    html_status = (DOCS / "status.html").read_text(encoding="utf-8")
    if html.escape(screen, quote=True) not in html_status:
        print("STALE STATUS PAGE: current screen_status from registry/status_feed.json is absent")
        fail += 1
    if "all five arms FAIL" not in screen or "no file is slot-approved" not in status["current"]["confirmation_status"]:
        print("STATUS REGISTER lacks the corrected H29 failure or no-slot decision")
        fail += 1
except (KeyError, json.JSONDecodeError, OSError) as exc:
    print(f"BAD CURRENT STATUS: {exc}")
    fail += 1

try:
    sources = json.loads((ROOT / "registry" / "sources.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "registry" / "submission_contract.json").read_text(encoding="utf-8"))
    source_ids = {item.get("id") for item in sources.get("sources", [])}
    if set(contract.get("source_ids", [])) - source_ids:
        print("SUBMISSION CONTRACT references missing source-register ids")
        fail += 1
    guide = (DOCS / "executive-summary.html").read_text(encoding="utf-8")
    for required in (contract["format"]["crs"], str(contract["format"]["pixel_size_m"]),
                     contract["format"]["outside_footprint"]):
        if required not in guide:
            print(f"SUBMISSION CONTRACT value absent from generated guide: {required}")
            fail += 1
except (KeyError, json.JSONDecodeError, OSError) as exc:
    print(f"BAD SUBMISSION CONTRACT: {exc}")
    fail += 1

print("check_site:", "OK" if fail == 0 else f"{fail} FAILURES")
sys.exit(1 if fail else 0)

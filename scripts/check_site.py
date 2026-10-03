#!/usr/bin/env python3
"""Static link/content checks for generated Pages, including single-quoted links."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "index.html", ROOT / "docs" / "executive-summary.html",
         ROOT / "docs" / "research.html", ROOT / "docs" / "sources.html"]
failures = 0


def fail(message: str) -> None:
    global failures
    failures += 1
    print(message)


for page in PAGES:
    if not page.is_file():
        fail(f"MISSING PAGE {page}")
        continue
    text = page.read_text()
    for match in re.finditer(r"\bhref\s*=\s*([\"'])(.*?)\1", text, re.I | re.S):
        href = html.unescape(match.group(2).strip())
        parsed = urlsplit(href)
        if parsed.scheme.lower() in ("http", "https", "mailto", "tel", "data", "javascript"):
            continue
        path = unquote(parsed.path)
        target = (page.parent / path).resolve() if path else page.resolve()
        if not target.exists():
            fail(f"BROKEN LINK in {page.relative_to(ROOT)}: {href}")
            continue
        if parsed.fragment and target.is_file() and target.suffix.lower() in (".html", ".htm"):
            target_text = target.read_text()
            frag = re.escape(unquote(parsed.fragment))
            if not re.search(rf"\bid\s*=\s*([\"']){frag}\1|\bname\s*=\s*([\"']){frag}\2", target_text, re.I):
                fail(f"BROKEN FRAGMENT in {page.relative_to(ROOT)}: {href}")
    if re.search(r"\bTODO\b|\bFIXME\b|lorem ipsum", text, re.I):
        fail(f"PLACEHOLDER TEXT in {page.relative_to(ROOT)}")

index = (ROOT / "index.html").read_text() if (ROOT / "index.html").is_file() else ""
if not re.search(r"""href=[\"']docs/downloads/[^\"']+-nan\.tif[\"']""", index):
    fail("HOME PAGE HAS NO OBVIOUS NAN-OUTSIDE TIFF DOWNLOAD")
try:
    ledger = json.loads((ROOT / "registry" / "artifact_ledger.json").read_text())
    arts = ledger["artifacts"]
    worm = arts["WORMRANK"]
    expected_tif = f"{worm['stem']}-nan.tif"
    if f'href="docs/downloads/{expected_tif}"' not in index:
        fail("HOME PAGE DOES NOT LINK THE CURRENT WORMRANK ARTIFACT FROM THE LEDGER")
    note = html.escape(worm["note"])
    if note not in index:
        fail("HOME PAGE DOES NOT SHOW THE CURRENT ARTIFACT'S NOTE")
    if worm.get("local_format_verified") is not True:
        fail("CURRENT WORMRANK ARTIFACT HAS NO PASSING LOCAL FORMAT RECEIPT")
    if worm.get("holdout_gate", {}).get("PASS") is not True:
        if "FROZEN A2 GATE NOT PASSED" not in index or "no weekly slot is recommended" not in index:
            fail("HOME PAGE DOES NOT CLEARLY FLAG THE FAILED GATE / NO-SLOT DECISION")
    if "do not resubmit" not in index.lower():
        fail("HOME PAGE DOES NOT WARN AGAINST RESUBMITTING THE D2.8 DUPLICATE")
except Exception as exc:
    fail(f"ARTIFACT LEDGER / HOME PAGE CHECK FAILED: {exc}")
source_page = (ROOT / "docs" / "sources.html").read_text() if (ROOT / "docs" / "sources.html").is_file() else ""
if "-'" in source_page or "'-'" in source_page:
    fail("SOURCE CLAIMS MAY STILL BE HIDDEN BY A PLACEHOLDER")

json_paths = [
    "data/manifest.json", "registry/live_scores.json", "registry/sources.json",
    "registry/irregularities.json", "registry/hypotheses_h29.json", "registry/hypotheses_next.json",
    "registry/artifact_ledger.json", "evidence/h29_holdout.json", "evidence/h29_gate.json",
    "evidence/worming_receipt.json",
]
for rel in json_paths:
    path = ROOT / rel
    try:
        json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        fail(f"BAD JSON {rel}: {exc}")

print("check_site:", "OK" if failures == 0 else f"{failures} FAILURES")
sys.exit(1 if failures else 0)

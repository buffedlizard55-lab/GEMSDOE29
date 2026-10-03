#!/usr/bin/env python3
"""Static checks for the site: every referenced local file exists, JSON embeds are parseable,
no placeholder text remains. Run after build_site.py."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fail = 0
pages = [ROOT / "index.html", ROOT / "docs" / "executive-summary.html",
         ROOT / "docs" / "research.html", ROOT / "docs" / "sources.html"]
for p in pages:
    if not p.exists():
        print(f"MISSING PAGE {p}")
        fail += 1
        continue
    html = p.read_text()
    for m in re.finditer(r'href="([^"#]+)"', html):
        href = m.group(1)
        if href.startswith(("http", "mailto")):
            continue
        target = (p.parent / href).resolve()
        if not target.exists():
            print(f"BROKEN LINK in {p.name}: {href}")
            fail += 1
    if re.search(r"\bTODO\b|\bFIXME\b|lorem ipsum", html, re.I):
        print(f"PLACEHOLDER TEXT in {p.name}")
        fail += 1
# No registry/live_scores.json exists by design: this project stores no leaderboard or live-score feed
# (DrivenData terms prohibit automated monitoring/copying). Register files checked below.
for j in ((ROOT / "data" / "manifest.json"),
          (ROOT / "registry" / "sources.json"), (ROOT / "registry" / "irregularities.json"),
          (ROOT / "registry" / "submissions.json"), (ROOT / "registry" / "status_feed.json"),
          (ROOT / "registry" / "hypotheses_h29.json"), (ROOT / "registry" / "artifact_ledger.json")):
    try:
        json.loads(j.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"BAD JSON {j}: {e}")
        fail += 1
print("check_site:", "OK" if fail == 0 else f"{fail} FAILURES")
sys.exit(1 if fail else 0)

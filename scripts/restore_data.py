#!/usr/bin/env python3
"""Restore + verify every pinned input (data/manifest.json). Idempotent. Never touches drivendata.org.

Sources in order: (1) existing file that already hashes right; (2) local mirrors via env
GEMSDOE_MIRROR / GEMSDOE24_MIRROR (checked first in CI-free sandboxes); (3) GitHub raw blobs at the
pinned commits (github.com is reachable from the agent sandbox). The 419 MB feature stack is
reassembled from five parts, each part verified against its own pin before concatenation, and the
whole file is verified against the canonical pin before it replaces any existing copy. Corrupt
parts are deleted (this is the fix for GEMSDOE27's Session-4 'restore-part-truncation-bug').
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def fetch_raw(repo: str, commit: str, rel: str, dest: Path, retries: int = 3) -> bool:
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{rel}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GEMSDOE29-restore/1.0"})
            with urllib.request.urlopen(req, timeout=240) as r, open(part, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            part.rename(dest)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"  attempt {attempt}/{retries} failed: {e}", flush=True)
            part.unlink(missing_ok=True)
            time.sleep(3 * attempt)
    return False


def ensure(f: dict, mirrors: list[Path]) -> str:
    rel, sha = f["path"], f["sha256"]
    dest = ROOT / rel
    if dest.exists() and sha256(dest) == sha:
        return "cached"
    cands = []
    for root in mirrors:
        if not root.exists():
            continue
        cands.append(root / rel)                      # same layout
        cands.append(root / rel.split("/", 1)[1])      # layout under repo root without "data"
        if "sibling_path" in f:
            cands.append(root / f["sibling_path"])
        if not any(c.exists() for c in cands):        # last local resort: basename search
            cands.extend(sorted(root.rglob(Path(rel).name)))
    for cand in cands:
        if cand.exists() and sha256(cand) == sha:
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(cand, dest)
            return "mirror-copy"
    rels = [rel.split("/", 1)[1], f.get("sibling_path", rel)]
    for src in MANIFEST["sources"].values():
        for sub in rels:
            if not sub:
                continue
            if fetch_raw(src["repo"], src["commit"], sub, dest):
                if dest.exists() and sha256(dest) == sha:
                    return "github-raw"
    dest.unlink(missing_ok=True)
    return "FAILED"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="hash-check what exists; do not download")
    args = ap.parse_args()
    gemsdoe = Path(os.environ.get("GEMSDOE_MIRROR", "/home/user/refs/GEMSDOE"))
    s24 = Path(os.environ.get("GEMSDOE24_MIRROR", "/home/user/refs/GEMSDOE24"))
    fails = 0
    for f in MANIFEST["files"]:
        rel, sha = f["path"], f["sha256"]
        dest = ROOT / rel
        if f.get("assembled_from_parts"):
            parts_ok = all((gemsdoe / "data" / "bridge" / p["name"]).exists()
                           and sha256(gemsdoe / "data" / "bridge" / p["name"]) == p["sha256"]
                           for p in f["assembled_from_parts"])
            if dest.exists() and sha256(dest) == sha:
                print(f"[cached] {rel}")
                continue
            if not parts_ok:
                print(f"[assemble-FAILED] {rel}: parts missing or mismatched")
                fails += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".tmp")
            h = hashlib.sha256()
            n = 0
            with open(tmp, "wb") as out:
                for p in f["assembled_from_parts"]:
                    src = gemsdoe / "data" / "bridge" / p["name"]
                    with open(src, "rb") as inp:
                        while chunk := inp.read(1 << 22):
                            out.write(chunk)
                            h.update(chunk)
                            n += len(chunk)
            if n == f["bytes"] and h.hexdigest() == sha:
                tmp.rename(dest)
                print(f"[assembled+verified] {rel} ({n:,} B)")
            else:
                tmp.unlink(missing_ok=True)
                print(f"[assemble-BAD] {rel}: n={n}, sha={h.hexdigest()}")
                fails += 1
            continue
        if dest.exists() and sha256(dest) == sha:
            print(f"[cached] {rel}")
            continue
        if args.verify:
            print(f"[MISSING] {rel}")
            fails += 1
            continue
        status = ensure(f, [s24, gemsdoe])
        print(f"[{status}] {rel}")
        if status == "FAILED":
            fails += 1
    print("restore_data:", "ALL VERIFIED" if fails == 0 else f"{fails} FAILURES")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

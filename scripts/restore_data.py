#!/usr/bin/env python3
"""Restore the hash-pinned local working set without contacting DrivenData.

Each manifest entry names an exact GitHub repository, commit and path. The large feature
GeoTIFF is assembled from five individually verified split blobs; the final file is not
installed until both its byte count and SHA-256 match the manifest. Download order is:

1. already-correct local file;
2. optional local mirror (GEMSDOE_MIRROR / GEMSDOE24_MIRROR / GEMSDOE25_MIRROR);
3. authenticated/public `gh api` raw-content request when GitHub CLI is installed;
4. the corresponding raw.githubusercontent.com URL.

DrivenData is deliberately never contacted by this script. Retrieved rasters remain in ignored
`data/`; never commit them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text())
LOCAL_MIRRORS = {
    "sibling_gemsdoe": Path(os.environ.get("GEMSDOE_MIRROR", "/home/user/refs/GEMSDOE")),
    "sibling24": Path(os.environ.get("GEMSDOE24_MIRROR", "/home/user/refs/GEMSDOE24")),
    "sibling24_public_layers": Path(os.environ.get("GEMSDOE24_MIRROR", "/home/user/refs/GEMSDOE24")),
    "sibling25": Path(os.environ.get("GEMSDOE25_MIRROR", "/home/user/refs/GEMSDOE25")),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def matches(path: Path, item: dict) -> bool:
    return path.is_file() and path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"]


def source_info(item: dict) -> tuple[str, dict, str] | None:
    key = item.get("source")
    rel = item.get("source_path")
    if not key or not rel or key not in MANIFEST["sources"]:
        return None
    return key, MANIFEST["sources"][key], rel


def local_copy(item: dict, dest: Path, *, search_roots: list[Path]) -> str | None:
    info = source_info(item)
    candidates: list[tuple[Path, str]] = []
    if info:
        key, _, rel = info
        mirror = LOCAL_MIRRORS.get(key)
        if mirror:
            candidates.append((mirror / rel, f"local-mirror:{key}"))
    rel = item.get("path") or item.get("source_path") or item.get("name")
    if rel:
        for root in search_roots:
            candidates.extend([
                (root / rel, "local-cache"),
                (root / Path(rel).name, "local-cache"),
            ])
    for candidate, label in candidates:
        if matches(candidate, item):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, dest)
            return label
    return None


def github_api_fetch(item: dict, tmp: Path) -> tuple[bool, str]:
    info = source_info(item)
    if not info or shutil.which("gh") is None:
        return False, "GitHub CLI or pinned source unavailable"
    _, src, rel = info
    endpoint = f"repos/{src['repo']}/contents/{quote(rel, safe='/')}?ref={src['commit']}"
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github.raw", endpoint]
    try:
        with tmp.open("wb") as out:
            result = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, check=False, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        tmp.unlink(missing_ok=True)
        return False, f"gh api error: {exc}"
    if result.returncode != 0:
        tmp.unlink(missing_ok=True)
        err = result.stderr.decode("utf-8", errors="replace").strip()
        return False, f"gh api exit {result.returncode}: {err[:500]}"
    if not matches(tmp, item):
        got = f"bytes={tmp.stat().st_size:,}, sha256={sha256(tmp)}" if tmp.exists() else "no output"
        tmp.unlink(missing_ok=True)
        return False, f"GitHub raw response did not match pin ({got})"
    return True, "github-api"


def raw_fetch(item: dict, tmp: Path) -> tuple[bool, str]:
    info = source_info(item)
    if not info:
        return False, "manifest item has no pinned source_path"
    _, src, rel = info
    url = f"https://raw.githubusercontent.com/{src['repo']}/{src['commit']}/{quote(rel, safe='/')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GEMSDOE29-restore/2.0"})
        with urllib.request.urlopen(req, timeout=900) as response, tmp.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        tmp.unlink(missing_ok=True)
        return False, f"raw.githubusercontent.com error: {exc}"
    if not matches(tmp, item):
        got = f"bytes={tmp.stat().st_size:,}, sha256={sha256(tmp)}" if tmp.exists() else "no output"
        tmp.unlink(missing_ok=True)
        return False, f"raw response did not match pin ({got})"
    return True, "github-raw"


def ensure_file(item: dict, dest: Path, *, verify_only: bool = False,
                local_search_roots: list[Path] | None = None) -> str:
    if matches(dest, item):
        return "cached+verified"
    roots = local_search_roots or []
    if not verify_only:
        source = local_copy(item, dest, search_roots=roots)
        if source:
            return source
    if verify_only:
        return "MISSING_OR_HASH_MISMATCH"

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".download.part")
    tmp.unlink(missing_ok=True)
    ok, detail = github_api_fetch(item, tmp)
    if not ok:
        print(f"  GitHub API fallback: {detail}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        ok, detail = raw_fetch(item, tmp)
    if not ok:
        tmp.unlink(missing_ok=True)
        return f"FAILED ({detail})"
    os.replace(tmp, dest)
    return detail


def restore_assembled(item: dict, dest: Path, *, verify_only: bool) -> tuple[str, bool]:
    if matches(dest, item):
        return "cached+verified", True
    parts = item.get("assembled_from_parts", [])
    cache = ROOT / "data" / "work" / "restore_parts"
    cache.mkdir(parents=True, exist_ok=True)
    part_paths: list[Path] = []
    status: list[str] = []
    for part in parts:
        part_dest = cache / part["name"]
        if matches(part_dest, part):
            status.append("cached-part")
        elif verify_only:
            # A mirror may contain the split parts under its original upstream names.
            key, rel = part.get("source"), part.get("source_path")
            mirror = LOCAL_MIRRORS.get(key) if key else None
            mirror_part = mirror / rel if mirror and rel else None
            if mirror_part and matches(mirror_part, part):
                part_paths.append(mirror_part)
                status.append("mirror-part-verified")
                continue
            status.append("missing-part")
            continue
        else:
            result = ensure_file(part, part_dest, local_search_roots=[ROOT / "data"])
            status.append(result)
            if not matches(part_dest, part):
                return "; ".join(status), False
        part_paths.append(part_dest)

    if verify_only:
        return ("assembled file missing; " + ", ".join(status)), False
    if len(part_paths) != len(parts):
        return ("not all split parts are available; " + ", ".join(status)), False

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".assemble.tmp")
    h = hashlib.sha256()
    n = 0
    try:
        with tmp.open("wb") as out:
            for part_path in part_paths:
                with part_path.open("rb") as inp:
                    while chunk := inp.read(1 << 22):
                        out.write(chunk)
                        h.update(chunk)
                        n += len(chunk)
        if n != item["bytes"] or h.hexdigest() != item["sha256"]:
            tmp.unlink(missing_ok=True)
            return f"ASSEMBLY_HASH_MISMATCH bytes={n:,} sha256={h.hexdigest()}", False
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    # The parts are cache only; the verified assembled raster is the retained data product.
    for part_path in part_paths:
        if part_path.parent == cache:
            part_path.unlink(missing_ok=True)
    try:
        cache.rmdir()
    except OSError:
        pass
    return "assembled+verified; " + ", ".join(status), True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="hash-check existing files only; do not download")
    args = parser.parse_args()
    failures = 0
    for item in MANIFEST["files"]:
        dest = ROOT / item["path"]
        if item.get("assembled_from_parts"):
            status, ok = restore_assembled(item, dest, verify_only=args.verify)
        else:
            status = ensure_file(item, dest, verify_only=args.verify,
                                 local_search_roots=[ROOT / "data"])
            ok = matches(dest, item)
        print(f"[{status if ok else 'FAILED: ' + status}] {item['path']}")
        if not ok:
            failures += 1
    print("restore_data:", "ALL VERIFIED" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

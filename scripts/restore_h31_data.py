#!/usr/bin/env python3
"""Restore the hash-pinned inputs listed in ``registry/data_manifest.json`` into ``GEMS_DATA_DIR``.

Everything comes from the owner's *public* GitHub repositories (the sandbox cannot log in to DrivenData),
via ``gh api`` when available, else ``raw.githubusercontent.com``. Every file is verified against its
SHA-256 pin; a mismatch aborts. A pin proves the mirror is unchanged - it does NOT authenticate the bytes
as organizer files (see registry/irregularities.json IR-DATA-01).

    python scripts/restore_h31_data.py --group core      # labels, template, feature raster
    python scripts/restore_h31_data.py --group external  # LiDAR / radiometric / GDR layers
    python scripts/restore_h31_data.py --group all       # all hash-pinned owner-mirror inputs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe.paths import data_dir  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(repo: str, ref: str, path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        if shutil.which("gh"):
            with tmp.open("wb") as out:
                subprocess.run(
                    ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}", "-H",
                     "Accept: application/vnd.github.raw"],
                    stdout=out, check=True,
                )
        else:
            import requests

            url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with tmp.open("wb") as out:
                    for chunk in r.iter_content(1 << 20):
                        out.write(chunk)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


def restore(entry: dict, root: Path) -> dict:
    dest = root / entry["dest"]
    if dest.exists() and sha256_file(dest) == entry["sha256"]:
        return dict(id=entry["id"], status="present", sha256=entry["sha256"])
    if "parts" in entry:
        tmp = dest.with_suffix(".assembling")
        with tmp.open("wb") as out:
            for part in entry["parts"]:
                p = root / "raw" / Path(part).name
                fetch(entry["repo"], entry["ref"], part, p)
                with p.open("rb") as src:
                    shutil.copyfileobj(src, out, 1 << 20)
                p.unlink()
        got = sha256_file(tmp)
        if got != entry["sha256"]:
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH for {entry['id']}: {got} != {entry['sha256']}")
        tmp.replace(dest)
    else:
        fetch(entry["repo"], entry["ref"], entry["path"], dest)
        got = sha256_file(dest)
        if got != entry["sha256"]:
            dest.unlink(missing_ok=True)
            raise SystemExit(f"HASH MISMATCH for {entry['id']}: {got} != {entry['sha256']}")
    return dict(id=entry["id"], status="restored", sha256=entry["sha256"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", default="core", choices=["core", "external", "all"])
    ap.add_argument("--manifest", default=str(ROOT / "registry" / "data_manifest.json"))
    args = ap.parse_args()
    man = json.loads(Path(args.manifest).read_text())
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for e in man["files"]:
        if args.group in ("all", e["group"]):
            r = restore(e, root)
            results.append(r)
            print(f"{r['status']:>8}  {e['dest']}  sha256={r['sha256'][:12]}…")
    (root / "restore_receipt.json").write_text(json.dumps(results, indent=1))
    print(f"{len(results)} files verified in {root}")


if __name__ == "__main__":
    main()

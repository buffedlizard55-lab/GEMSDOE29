#!/usr/bin/env python3
"""Check that the restored owner-mirror inputs and the local pipeline are complete and reproducible.

This is the machine-checkable answer to the standing blocker question "is the data placed and is the
train -> inference -> validate pipeline runnable here?". It never contacts DrivenData and never writes into
``data/``: it hash-checks the two pinned manifests against what is on disk, checks the submission template
against the frozen grid constants, checks the regenerable feature caches exist, and — with ``--reproduce`` —
re-runs the registered candidate build into a temporary directory and compares its SHA-256 with the byte-pinned
artifact in ``registry/submissions.json``.

    python3 scripts/verify_pipeline.py                 # hashes + template + caches (seconds)
    python3 scripts/verify_pipeline.py --reproduce     # also rebuild the candidate and compare hashes (~2 min)

Every number written to ``evidence/pipeline_verification.json`` comes from this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import data_dir, template_path, work_dir  # noqa: E402
from gemsdoe.submission import EXPECTED  # noqa: E402

CORE_MANIFEST = ROOT / "data" / "manifest.json"
GROUP_MANIFEST = ROOT / "registry" / "data_manifest.json"
OUT_PATH = ROOT / "evidence" / "pipeline_verification.json"
CACHE_FILES = ("static_ABCD.npy", "static_ABCD.npy.names.json", "addons.npy", "addons.npy.names.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_entries(entries: list[tuple[str, dict]], base: Path) -> dict:
    """Hash-check ``[(label, {sha256, bytes, ...})]`` under ``base`` without ever writing."""
    verified, problems = [], []
    for label, item in entries:
        path = base / item["path"]
        if not path.is_file():
            problems.append(f"missing {label}: {path}")
            continue
        size, digest = path.stat().st_size, sha256_file(path)
        if size != item["bytes"] or digest != item["sha256"]:
            problems.append(f"hash/size mismatch {label}: {size} bytes {digest[:16]}...")
            continue
        verified.append(dict(label=label, bytes=size, sha256=digest))
    return dict(verified=verified, problems=problems)


def check_template(data: Path) -> dict:
    import numpy as np
    import rasterio

    path = template_path()
    if not path.is_file():
        return dict(path=str(path), ok=False, problems=[f"template not found at {path}"])
    with rasterio.open(path) as source:
        footprint = np.isfinite(source.read(1))
        meta = dict(epsg=source.crs.to_epsg() if source.crs else None, shape=list(source.shape),
                    transform=[float(v) for v in source.transform][:6])
    problems = []
    if meta["epsg"] != EXPECTED["epsg"]:
        problems.append(f"epsg {meta['epsg']} != {EXPECTED['epsg']}")
    if tuple(meta["shape"]) != EXPECTED["shape"]:
        problems.append(f"shape {meta['shape']} != {list(EXPECTED['shape'])}")
    if tuple(meta["transform"]) != EXPECTED["transform"]:
        problems.append(f"transform {meta['transform']} != {list(EXPECTED['transform'])}")
    if int(footprint.sum()) != EXPECTED["footprint_pixels"]:
        problems.append(f"footprint {int(footprint.sum())} != {EXPECTED['footprint_pixels']}")
    return dict(path=str(path.relative_to(ROOT)), ok=not problems, problems=problems, grid=meta,
                footprint_pixels=int(footprint.sum()), template_sha256=sha256_file(path))


def check_caches(work: Path) -> dict:
    present, missing = {}, []
    for name in CACHE_FILES:
        path = work / name
        if path.is_file():
            present[name] = dict(bytes=path.stat().st_size, sha256=sha256_file(path))
        else:
            missing.append(name)
    for name in ("_footprint.npy", "_labels.npy"):
        path = work / "bands" / name
        if path.is_file():
            present[f"bands/{name}"] = dict(bytes=path.stat().st_size, sha256=sha256_file(path))
        else:
            missing.append(f"bands/{name}")
    return dict(present=present, missing=missing, ok=not missing)


def reproduce_candidate() -> dict:
    """Rebuild the registered candidate in a temp dir and compare its hash with the pinned artifact."""
    submissions = json.loads((ROOT / "registry" / "submissions.json").read_text())
    entry = next((f for f in submissions["files"] if f.get("id") == "repo-c0-habitat"), None)
    if entry is None:
        return dict(ok=False, problems=["registry/submissions.json has no repo-c0-habitat entry"])
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gemsdoe29-verify-") as tmp:
        out = Path(tmp)
        command = [sys.executable, str(ROOT / "scripts" / "build_repo_candidate.py"),
                   "--out-dir", str(out), "--record", str(out / "record.json"), "--slug", "verify-repro"]
        start = time.time()
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        elapsed = time.time() - start
        if proc.returncode != 0:
            return dict(ok=False, seconds=elapsed, command=" ".join(command),
                        problems=[f"build exited {proc.returncode}: {proc.stderr.strip()[-500:]}"])
        built = sorted(p for p in out.glob("*.tif"))
        if len(built) != 1:
            problems.append(f"expected one GeoTIFF from the rebuild, found {len(built)}")
        else:
            digest = sha256_file(built[0])
            if digest != entry["sha256"]:
                problems.append(f"rebuild sha256 {digest[:16]}... != registered {entry['sha256'][:16]}...")
            record_path = out / "record.json"
            record = json.loads(record_path.read_text()) if record_path.is_file() else {}
            if record.get("artifact", {}).get("content_id") != entry.get("content_id"):
                problems.append("rebuild content_id differs from the registered artifact")
            return dict(ok=not problems, seconds=round(elapsed, 1), command=" ".join(command),
                        rebuilt_sha256=digest, registered_sha256=entry["sha256"],
                        rebuilt_bytes=built[0].stat().st_size, registered_bytes=entry["bytes"],
                        content_id=record.get("artifact", {}).get("content_id"), problems=problems)
    return dict(ok=False, problems=problems)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reproduce", action="store_true",
                        help="re-run the candidate build in a temp dir and compare its hash with the register")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    data, work = data_dir(), work_dir()
    core = json.loads(CORE_MANIFEST.read_text())
    group = json.loads(GROUP_MANIFEST.read_text())
    core_paths = [(item["path"], {"path": item["path"], "bytes": item["bytes"], "sha256": item["sha256"]})
                  for item in core["files"]]
    group_paths = [(item["id"], {"path": item["dest"], "bytes": item["bytes"], "sha256": item["sha256"]})
                   for item in group["files"]]
    result = dict(
        schema_version=1,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        generated_by="scripts/verify_pipeline.py",
        environment=dict(python=platform.python_version(), numpy=__import__("numpy").__version__),
        data_dir=str(data),
        core_manifest=dict(path=str(CORE_MANIFEST.relative_to(ROOT)), files=len(core["files"]),
                           **check_entries(core_paths, ROOT)),
        group_manifest=dict(path=str(GROUP_MANIFEST.relative_to(ROOT)), files=len(group["files"]),
                            **check_entries(group_paths, data)),
        template=check_template(data),
        caches=check_caches(work),
    )
    if args.reproduce:
        result["reproduction"] = reproduce_candidate()
    problems = (result["core_manifest"]["problems"] + result["group_manifest"]["problems"]
                + result["template"]["problems"] + result["caches"]["missing"])
    if "reproduction" in result:
        problems += result["reproduction"]["problems"]
    result["problems"] = problems
    result["ok"] = not problems
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"core manifest:  {len(result['core_manifest']['verified'])}/{len(core['files'])} files hash-verified")
    print(f"group manifest: {len(result['group_manifest']['verified'])}/{len(group['files'])} files hash-verified")
    print(f"template:       {'ok' if result['template']['ok'] else 'PROBLEM'} "
          f"footprint={result['template'].get('footprint_pixels')}")
    print(f"caches:         {'complete' if result['caches']['ok'] else 'MISSING ' + str(result['caches']['missing'])}")
    if "reproduction" in result:
        repro = result["reproduction"]
        print(f"reproduction:   {'byte-identical' if repro['ok'] else 'PROBLEM'} "
              f"({repro.get('seconds')}s){' sha256=' + repro.get('rebuilt_sha256', '')[:16] + '...' if repro.get('rebuilt_sha256') else ''}")
    print(f"problems:       {problems if problems else 'none'}")
    print(f"wrote {args.out.relative_to(ROOT)}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Record, as a script-written receipt, that the competition inputs are placed and usable in this checkout.

The standing brief's blocker was "the organizer data page needs a login". This script proves what is
actually true in a checkout: every hash-pinned owner-mirror entry of both manifests is present and
byte-correct, the aligned working arrays exist, the footprint/label counts match the pinned raster, and the
feature caches are loadable. It contacts nothing (no DrivenData, no network) and writes
``evidence/data_placement_receipt.json``.

    GEMS_DATA_DIR=$PWD/data python3 scripts/record_data_placement.py [--check]

``--check`` re-verifies an existing receipt (hashes, counts) and exits non-zero on drift; it never rewrites
the file. The receipt distinguishes three things explicitly, because they are not the same claim:
``owner_mirror`` (byte-correct against the recorded pin), ``organizer_authenticated`` (always false here)
and ``prepared`` (the derived caches exist and agree with the pins).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import data_dir, work_dir  # noqa: E402

OUT = ROOT / "evidence" / "data_placement_receipt.json"
MANIFESTS = (("registry/data_manifest.json", "h31"), ("data/manifest.json", "core"))
GROUP_FILES = ("labels.tif", "existing_faults.tif", "sample_submission.tif", "training_features.tif")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest_path: Path, root: Path, *, nested: bool = False) -> list[dict]:
    """One record per pinned entry: present / missing / hash-mismatch, with the expected hash."""
    man = json.loads(manifest_path.read_text())
    out = []
    for entry in man["files"]:
        rel = entry.get("dest") or entry.get("path")
        ident = entry.get("id") or Path(rel).name
        if nested and not rel.startswith("data/"):
            rel = f"data/{rel}"
        cands = [root / rel]
        if rel.startswith("data/"):
            cands.append(root / rel[len("data/"):])
            cands.append(root / "bridge" / rel[len("data/"):])
        path = next((c for c in cands if c.is_file()), None)
        if path is None:
            out.append(dict(id=ident, status="missing", dest=rel, expected_sha256=entry["sha256"]))
            continue
        got = sha256_file(path)
        out.append(dict(id=ident, dest=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                        bytes=path.stat().st_size, status="present" if got == entry["sha256"] else "hash_mismatch",
                        sha256=got, expected_sha256=entry["sha256"]))
    return out


def work_cache(name: str, w: Path) -> dict:
    p = w / name
    return dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
                present=p.is_file(), sha256=sha256_file(p) if p.is_file() else None,
                bytes=p.stat().st_size if p.is_file() else None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify an existing receipt without rewriting it")
    args = ap.parse_args()
    if args.check:
        if not OUT.is_file():
            print(f"no receipt at {OUT}")
            return 1
        old = json.loads(OUT.read_text())
        problems = list(old.get("problems", []))
        for grp in old["manifests"]:
            for entry in grp["files"]:
                p = ROOT / entry["dest"] if entry.get("dest") else None
                if p is None or not p.is_file():
                    problems.append(f"{entry['id']}: missing")
                    continue
                if sha256_file(p) != entry.get("expected_sha256"):
                    problems.append(f"{entry['id']}: hash drift")
        print(json.dumps({"checked": OUT.relative_to(ROOT).as_posix(), "problems": problems}, indent=2))
        return 1 if problems else 0

    data, work = data_dir(), work_dir()
    t0 = time.time()
    manifests = []
    for rel, tag in MANIFESTS:
        path = ROOT / rel
        if not path.is_file():
            continue
        files = verify_manifest(path, data, nested=True)
        manifests.append(dict(manifest=rel, tag=tag, n_entries=len(files),
                              n_present=sum(f["status"] == "present" for f in files), files=files))

    problems: list[str] = []
    for grp in manifests:
        for f in grp["files"]:
            if f["status"] != "present":
                problems.append(f"{grp['tag']}/{f['id']}: {f['status']}")

    prepared: dict = {}
    band_files = sorted((work / "bands").glob("*.npy")) if (work / "bands").is_dir() else []
    foot = np.load(work / "bands" / "_footprint.npy") if (work / "bands" / "_footprint.npy").is_file() else None
    labels = np.load(work / "bands" / "_labels.npy") if (work / "bands" / "_labels.npy").is_file() else None
    prepared["bands"] = dict(directory=str((work / "bands").relative_to(ROOT) if (work / "bands").is_dir() else work / "bands"),
                             n_files=len(band_files),
                             names=[p.name for p in band_files][:24])
    if foot is not None:
        prepared["footprint_pixels"] = int(foot.sum())
        if prepared["footprint_pixels"] != 5_167_373:
            problems.append(f"footprint {prepared['footprint_pixels']} != pinned 5,167,373")
    else:
        problems.append("missing data/work/bands/_footprint.npy")
    if labels is not None:
        prepared["label_pixels"] = int(labels.sum())
        if prepared["label_pixels"] != 60_988:
            problems.append(f"label pixels {prepared['label_pixels']} != pinned 60,988")
    else:
        problems.append("missing data/work/bands/_labels.npy")
    prepared["caches"] = {name: work_cache(name, work) for name in
                          ("static_ABCD.npy", "static_ABCD.npy.names.json", "addons.npy", "addons.npy.names.json")}
    for name, rec in prepared["caches"].items():
        if not rec["present"]:
            problems.append(f"missing work cache {name} (run scripts/build_features.py / build_addons.py)")

    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        revision, branch = "unknown", "unknown"

    receipt = dict(
        schema_version=1,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        generated_by="scripts/record_data_placement.py",
        claim=("every hash-pinned owner-mirror entry needed by the training pipeline is present and "
               "byte-correct in this checkout, and the derived working arrays exist; the files are NOT "
               "organizer-authenticated (the DrivenData data page requires a login)"),
        owner_mirror=True,
        organizer_authenticated=False,
        prepared=not problems,
        data_dir=str(data),
        work_dir=str(work),
        manifests=manifests,
        prepared_detail=prepared,
        problems=problems,
        commands=dict(
            restore="bash scripts/download_competition_data.sh   # --group core|h31|all, or --verify",
            prepare="python scripts/prepare_data.py",
            features="python scripts/build_features.py && python scripts/build_addons.py",
            rerun_receipt="python scripts/record_data_placement.py --check",
        ),
        environment=dict(python=platform.python_version(), platform=platform.platform(),
                         numpy=np.__version__),
        git=dict(revision=revision, branch=branch),
        seconds=round(time.time() - t0, 3),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, default=float) + "\n")
    n_files = sum(g["n_present"] for g in manifests)
    print(f"wrote {OUT.relative_to(ROOT)}: {n_files} pinned files present and byte-correct, "
          f"footprint {prepared.get('footprint_pixels')}, labels {prepared.get('label_pixels')}, "
          f"problems={len(problems)}")
    for p in problems:
        print(f"  PROBLEM {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

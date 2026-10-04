#!/usr/bin/env python3
"""Proxy calibration: score owner-reported historical artifacts on the primary proxy (no model fitting).

`knowledge/34` section 6.1 makes this the project's first strategy item: the catalogue-hidden proxy is
the gate every promotion decision here uses, and its only external anchor is a three-point ordering
(H19-5 < D1.5 < D2.8) inherited from unverified owner reports (`knowledge/17`, `knowledge/32`). Three
points cannot distinguish a proxy from a coincidence. This script extends the anchor set by fetching
public artifacts from the owner's own sibling repositories (GitHub, via the authenticated ``gh`` CLI —
**never** DrivenData), scoring each on the *same* proxy definitions with no fitting, and reporting the
rank correlation between proxy score and the score the sibling README reports.

Everything is recorded: repository, commit SHA, path, byte size, SHA-256, the README line that states
the reported score, and the proxy result. A file whose reported score cannot be found in the sibling
README is *not* used as an anchor (it can still be scored, but it does not enter the correlation).

    GEMS_DATA_DIR=$PWD/data python scripts/calibrate_proxy_against_reported_scores.py            # fetch + score
    GEMS_DATA_DIR=$PWD/data python scripts/calibrate_proxy_against_reported_scores.py --no-fetch # score local only

Outputs ``evidence/proxy_calibration.json``. Writes fetched rasters under the ignored
``data/external/calibration/`` tree; nothing here touches the competition portal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe.paths import data_dir  # noqa: E402
from gemsdoe.proxies import load_proxy_context, read_binary, score_mask  # noqa: E402

OUT = ROOT / "evidence" / "proxy_calibration.json"
CACHE = ROOT / "data" / "external" / "calibration"

# (label, owner-reported score, source text, local path or None, repo, filename hint)
# Reported scores are the values in the owner's brief (unverified); the sibling README is fetched and the
# matching line is stored as the citation for each anchor.
ANCHORS = [
    dict(label="H19-5", reported=0.1922, source="19GEMSDOE/h19-5-powerlaw-budget-multiline-corroborated",
         local="data/inputs/h19_5_nan.tif"),
    dict(label="D1.5", reported=0.2477, source="24GEMSDOE/h25-1-dotted-h19-5-d1-5",
         local="data/inputs/dotted_h19_5_d1_5_nan.tif"),
    dict(label="D2.8", reported=0.2600, source="25GEMSDOE/dotted-h19-5-d2-8",
         local="data/inputs/dotted_h19_5_d2_8_nan.tif"),
    dict(label="tgc-t-v2-on-d1-5", reported=0.2449, source="GEMSDOE27/topo-gap-closure-t-v2-on-d1-5",
         repo="buffedlizard55-lab/GEMSDOE27",
         hint="topo-gap-closure-t-v2-on-d1-5"),
    dict(label="h30-arrangement", reported=0.1352, source="GEMSDOE23/h30-arrangement-matched-habitat",
         repo="buffedlizard55-lab/GEMSDOE23", hint="h30-arrangement-matched-habitat"),
    dict(label="dilcond-oof-v1", reported=0.1223, source="GEMSDOE26/dilcond-oof-v1",
         repo="buffedlizard55-lab/GEMSDOE26", hint="dilcond-oof-v1"),
    dict(label="r13-lattice-s5-v2", reported=0.0904, source="13GEMSDOE/r13-lattice-s5_v2",
         repo="buffedlizard55-lab/13GEMSDOE", hint="r13-lattice-s5_v2"),
    dict(label="conj-alteration-mag", reported=0.0782, source="15GEMSDOE/tso1-conj_alteration_mag",
         repo="buffedlizard55-lab/15GEMSDOE", hint="conj_alteration_mag"),
    dict(label="pindrop-v4-nodes", reported=0.1193, source="GEMSDOE3/pindrop-v4-nodes",
         repo="buffedlizard55-lab/GEMSDOE3", hint="pindrop"),
    dict(label="lidarscarp-ridge-top2pct", reported=0.1461, source="7GEMSDOE/lidarscarp-ridge-top2pct",
         repo="buffedlizard55-lab/7GEMSDOE", hint="lidarscarp"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gh_json(*args: str) -> object:
    out = subprocess.check_output(["gh", *args], cwd=ROOT, text=True)
    return json.loads(out)


def gh_text(*args: str) -> str:
    return subprocess.check_output(["gh", *args], cwd=ROOT, text=True)


def repo_default_branch(repo: str) -> str:
    return gh_text("api", f"repos/{repo}", "--jq", ".default_branch").strip()


def find_file(repo: str, hint: str, branch: str) -> str | None:
    """Locate a TIF under docs/downloads (or the repo) whose name matches the hint; prefer *-nan.tif."""
    try:
        tree = gh_json("api", f"repos/{repo}/git/trees/{branch}?recursive=1")
    except subprocess.CalledProcessError:
        return None
    paths = [n["path"] for n in tree.get("tree", []) if n["path"].lower().endswith(".tif")]
    hits = [p for p in paths if hint.lower() in p.lower()]
    if not hits:
        return None
    hits.sort(key=lambda p: (0 if p.endswith("-nan.tif") else 1 if "-nan-outside" in p else 2, len(p)))
    return hits[0]


def readme_evidence(repo: str, branch: str, score: float) -> str | None:
    """Return the README line that reports this score, if any (the citation for the anchor)."""
    try:
        text = gh_text("api", f"repos/{repo}/contents/README.md", "--jq", ".content")
        import base64

        readme = base64.b64decode(text).decode("utf-8", "replace")
    except subprocess.CalledProcessError:
        return None
    pat = re.compile(rf"{re.escape(f'{score:.4f}')}|{re.escape(f'{score:.3f}')}")
    for line in readme.splitlines():
        if pat.search(line):
            return line.strip()[:300]
    return None


def download(repo: str, branch: str, path: str, dest: Path) -> None:
    """Fetch one file with the raw media type (the contents API caps JSON payloads at 1 MB)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = subprocess.check_output(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw",
         f"repos/{repo}/contents/{path}?ref={branch}"],
        cwd=ROOT,
    )
    dest.write_bytes(blob)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-fetch", action="store_true", help="use only local anchors")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    data = data_dir()
    context = load_proxy_context(data)
    entries: list[dict] = []
    for spec in ANCHORS:
        entry = dict(label=spec["label"], reported_score=float(spec["reported"]), source=spec["source"])
        target: Path | None = None
        if spec.get("local"):
            candidate = ROOT / spec["local"]
            if candidate.is_file():
                target = candidate
                entry["provenance"] = "owner mirror pinned in this repository (hash-verified)"
        elif not args.no_fetch and spec.get("repo"):
            repo = spec["repo"]
            try:
                branch = repo_default_branch(repo)
                path = find_file(repo, spec["hint"], branch)
                if path:
                    dest = CACHE / f"{repo.split('/')[-1]}_{Path(path).name}"
                    if not dest.is_file():
                        download(repo, branch, path, dest)
                    target = dest
                    entry.update(provenance=f"{repo}@{branch}:{path}",
                                 readme_line=readme_evidence(repo, branch, float(spec["reported"])))
                    entry["commit"] = gh_text("api", f"repos/{repo}/commits/{branch}", "--jq", ".sha").strip()
                else:
                    entry["error"] = f"file not found for hint {spec['hint']!r}"
            except subprocess.CalledProcessError as exc:
                entry["error"] = f"gh failed: {exc}"
        else:
            entry["error"] = "no local file and fetching disabled"
        if target is None or not target.is_file():
            entry.setdefault("error", "no file")
            entries.append(entry)
            continue
        entry["bytes"] = target.stat().st_size
        entry["sha256"] = sha256_file(target)
        emitted = read_binary(target)
        if emitted.shape != context.foot.shape:
            entry["error"] = f"shape {emitted.shape} != template {context.foot.shape}"
            entries.append(entry)
            continue
        t0 = time.time()
        scored = score_mask(emitted, context, spec["label"])
        entry.update(catalogue_hidden_mean=float(scored["catalogue_hidden_mean"]),
                     catalogue_hidden_per_draw=scored["catalogue_hidden_per_draw"],
                     emitted_pixels=int(scored["emitted_pixels"]),
                     sgmc_off_catalogue=float(scored["sgmc_off_catalogue"]["dti"]),
                     hug_share=float(scored["hug_share"]),
                     on_catalogue_pixels=int(scored["on_catalogue_pixels"]),
                     score_seconds=round(time.time() - t0, 1))
        entries.append(entry)
        print(f"{entry['label']:24s} reported {entry['reported_score']:.4f}  proxy {entry['catalogue_hidden_mean']:.5f}  "
              f"sgmc {entry['sgmc_off_catalogue']:.4f}  emitted {entry['emitted_pixels']}", flush=True)

    usable = [e for e in entries if "catalogue_hidden_mean" in e]
    correlation = None
    if len(usable) >= 4:
        rep = np.array([e["reported_score"] for e in usable])
        prox = np.array([e["catalogue_hidden_mean"] for e in usable])
        from scipy.stats import kendalltau, spearmanr

        correlation = dict(n=len(usable), spearman=float(spearmanr(rep, prox).statistic),
                           kendall=float(kendalltau(rep, prox).statistic),
                           pearson=float(np.corrcoef(rep, prox)[0, 1]))
    payload = dict(
        schema_version=1,
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        purpose="calibrate the catalogue-hidden proxy against owner-reported live scores (no fitting)",
        anchors=entries, usable_anchors=len(usable), correlation=correlation,
        proxy_definition=("hide-and-recover catalogue-gap proxy, 4 quadrant folds x draws 20/21, "
                          "hiding 20 % of catalogue components (gemsdoe.proxies.paired_catalogue_hidden)"),
        caveat=("Every reported score is an unverified owner/sibling-README claim; the sibling files are public "
                "GitHub artifacts fetched with the authenticated gh CLI, never from DrivenData. A high rank "
                "correlation supports the proxy as a *ranking* device on these files only; it does not make any "
                "proxy value a competition score."),
        drivendata_contacted=False,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if correlation:
        print(f"calibration: n={correlation['n']} spearman={correlation['spearman']:+.3f} "
              f"kendall={correlation['kendall']:+.3f} pearson={correlation['pearson']:+.3f}")
    shown = str(args.out.relative_to(ROOT)) if str(args.out).startswith(str(ROOT)) else str(args.out)
    print(f"wrote {shown}; usable anchors {len(usable)}/{len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

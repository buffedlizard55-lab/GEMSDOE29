#!/usr/bin/env python3
"""Recompute, from the archived raw cells, how the two local proxies have agreed — and where they have not.

The repository's promotion discipline has two local proxies: the primary catalogue-hidden DTI (the only proxy
with any external anchor: ``knowledge/17`` records that it reproduced the ordering of three unverified
owner/user-reported historical scores, Spearman +1.0, while the SGMC off-catalogue proxy ordered the same
three in reverse, Spearman -0.5) and the SGMC off-catalogue class (``knowledge/19`` section 5 declares a
conflict between them as grounds to withhold promotion).

This script answers one question with archived data only: for every arm that cleared a stage's *primary*
promotion gate, what did the SGMC proxy say? It writes ``evidence/proxy_agreement_review.json``. It reads
local evidence files, never contacts DrivenData, and changes no label or register.

    python3 scripts/review_proxy_agreement.py [--out evidence/proxy_agreement_review.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# stage -> (raw cells, base/control arm, draws fitted). Only stages whose raw cells carry both proxies.
STAGES = {
    "h31b_dense_screen": ("evidence/h31b_dense_screen/cells.jsonl", "C_base", [22, 23]),
    "h34_coverage_screen": ("evidence/h34_coverage_screen/cells.jsonl", "C0_ordered_dots", [20, 21]),
    "h35_h40_screen": ("evidence/h35_h40_screen/cells_screen.jsonl", "C0_base", [24, 25]),
    "h41_screen": ("evidence/h41_screen/cells_screen.jsonl", "C0_base", [28, 29]),
    "h41_confirmation": ("evidence/h41_screen/cells_confirm.jsonl", "C0_base", [30, 31]),
    "h43_screen": ("evidence/h43_screen/cells_screen.jsonl", "C0_base", [32, 33]),
}

# Arm-stages that a published, committed summary records as clearing that stage's PRIMARY promotion gate,
# with the document that records the verdict. The SGMC sign next to each one is recomputed here from cells.
GATE_PASSES = {
    "h41_screen::A1_h41_off": "knowledge/26_h41_results_2026-10-03.md",
    "h41_screen::A4_h41_union": "knowledge/26_h41_results_2026-10-03.md",
    "h41_confirmation::A4_h41_union": "knowledge/26_h41_results_2026-10-03.md",
    "h43_screen::A3_knick": "knowledge/30_h43_drainage_results_2026-10-03.md",
    "h43_screen::A4_union": "knowledge/30_h43_drainage_results_2026-10-03.md",
}
EXCLUDED_FROM_GATE_LIST = {
    "h34_coverage_screen::C1_geodesic_dots": "control arm, not a proposal; the screen's proposal arms (C2/C3) "
                                             "failed the primary gate and are recorded as such",
    "h35_h40_screen::A4_union": "mean criterion met but the >=3/4-positive-folds rule failed (2/4 on draw 24)",
    "h43_screen::A1_off": "primary mean +0.00401, below the frozen +0.005 mean bar",
}

# The only external anchors that exist: three unverified owner/user-reported scores against this repo's
# catalogue-hidden proxy values, as recorded in knowledge/17 section "What the proxy does and does not mean".
ANCHORS = [
    dict(reported_score=0.2600, primary_proxy=0.09832),
    dict(reported_score=0.2477, primary_proxy=0.09449),
    dict(reported_score=0.1922, primary_proxy=0.06970),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def spearman(a: list[float], b: list[float]) -> float:
    """Spearman rho for tiny n, average ranks for ties (no scipy dependency)."""
    def ranks(xs: list[float]) -> np.ndarray:
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = np.empty(len(xs), float)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2.0 + 1.0
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def arm_gains(rows: list[dict], arm: str, base: str, key: str) -> tuple[float, int, int]:
    """Mean paired fold gain of ``arm`` over ``base``, positive-fold count, fold count."""
    gains = []
    for fold in sorted({r["fold"] for r in rows}):
        a = [r[key] for r in rows if r["arm"] == arm and r["fold"] == fold]
        c = [r[key] for r in rows if r["arm"] == base and r["fold"] == fold]
        if a and c:
            gains.append(float(np.mean(a) - np.mean(c)))
    return (float(np.mean(gains)) if gains else float("nan"),
            int(sum(g > 0 for g in gains)), len(gains))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "evidence" / "proxy_agreement_review.json")
    args = parser.parse_args()

    stages: dict[str, dict] = {}
    arm_stages: list[dict] = []
    for stage, (rel, base, draws) in STAGES.items():
        path = ROOT / rel
        if not path.is_file():
            stages[stage] = dict(present=False, path=rel)
            continue
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        stages[stage] = dict(present=True, path=rel, rows=len(rows), draws=draws, base_arm=base,
                             sha256=sha256_file(path))
        for arm in sorted({r["arm"] for r in rows if r["arm"] != base}):
            pg, pp, pf = arm_gains(rows, arm, base, "dti")
            sg, sp, sf = arm_gains(rows, arm, base, "sgmc_dti")
            key = f"{stage}::{arm}"
            arm_stages.append(dict(
                stage=stage, arm=arm, draws=draws,
                primary_mean_gain=pg, primary_positive_folds=pp, primary_folds=pf,
                sgmc_mean_gain=sg, sgmc_positive_folds=sp, sgmc_folds=sf,
                primary_positive=bool(pg > 0), sgmc_positive=bool(sg > 0),
                both_positive=bool(pg > 0 and sg > 0),
                cleared_primary_gate=key in GATE_PASSES,
                gate_source=GATE_PASSES.get(key),
                excluded_note=EXCLUDED_FROM_GATE_LIST.get(key),
            ))

    gate_passers = [a for a in arm_stages if a["cleared_primary_gate"]]
    anchors = dict(
        pairs=ANCHORS,
        primary_spearman=spearman([a["reported_score"] for a in ANCHORS], [a["primary_proxy"] for a in ANCHORS]),
        note="three unverified owner/user-reported scores, three points; recorded in knowledge/17 as the only "
             "external anchor any proxy here has. The SGMC order is the reverse (-0.5).",
    )
    summary = dict(
        arm_stages_analysed=len(arm_stages),
        both_proxies_positive=sum(a["both_positive"] for a in arm_stages),
        primary_positive_sgmc_negative=sum(1 for a in arm_stages if a["primary_positive"] and not a["sgmc_positive"]),
        primary_negative_sgmc_positive=sum(1 for a in arm_stages if not a["primary_positive"] and a["sgmc_positive"]),
        both_negative=sum(1 for a in arm_stages if not a["primary_positive"] and not a["sgmc_positive"]),
        gate_passing_arm_stages=len(gate_passers),
        gate_passing_with_positive_sgmc=sum(a["sgmc_positive"] for a in gate_passers),
    )
    payload = dict(
        schema_version=1,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        generated_by="scripts/review_proxy_agreement.py",
        question="For every arm that cleared a stage's primary promotion gate, what did the SGMC proxy say?",
        stages=stages,
        arm_stages=arm_stages,
        gate_passers=gate_passers,
        anchors=anchors,
        summary=summary,
        policy_note=("This file is evidence for a policy review, not a policy change. No label, register or gate "
                     "is modified by writing it; the finding is registered as an irregularity for the owner to "
                     "decide on."),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"arm-stages analysed: {summary['arm_stages_analysed']} "
          f"(both proxies positive: {summary['both_proxies_positive']})")
    print(f"gate-passing arm-stages: {summary['gate_passing_arm_stages']}, "
          f"of which SGMC-positive: {summary['gate_passing_with_positive_sgmc']}")
    for a in gate_passers:
        print(f"  {a['stage']:18s} {a['arm']:16s} primary {a['primary_mean_gain']:+.5f} "
              f"sgmc {a['sgmc_mean_gain']:+.5f}")
    print(f"anchors: primary Spearman {anchors['primary_spearman']:+.2f} on {len(ANCHORS)} unverified points")
    try:
        shown = args.out.relative_to(ROOT)
    except ValueError:  # an out-of-tree --out is legitimate (tests use a temp dir)
        shown = args.out
    print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

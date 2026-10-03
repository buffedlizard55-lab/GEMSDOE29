#!/usr/bin/env python3
"""Build ``registry/draw_ledger.json`` from the committed evidence, so draw reuse is machine-checkable.

`knowledge/18` keeps the draw ledger as prose; every screen in this family reserves a fresh draw pair, so a
future session had to read prose to know which seeds are spent. This script derives the same ledger from the
``draws`` arrays inside ``evidence/**/design*.json`` (and the H29 gate file), records the pairs that were
authorized then released without a fit, and refuses to write a ledger in which any draw is claimed by two
*fitted* stages. It reads local files only.

    python3 scripts/build_draw_ledger.py [--check]

``--check`` compares the committed ledger to a fresh derivation and exits 1 on drift (used by the test).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
OUT = ROOT / "registry" / "draw_ledger.json"

# Stages whose evidence lives in a non-standard place or whose reserved-but-unfitted draws must be recorded
# explicitly, because "the file mentions the draw" is not the same as "a model was fit on it".
STAGE_SOURCES = {
    "h29_corrected_screen": dict(files=["evidence/h29_gate.json"], fitted_key="screen_draws",
                                 reserved_key="confirmation_draws"),
    "h31_worm_screen": dict(files=["evidence/h31_worm_screen/design.json"], fitted_key="draws"),
    "factorial_families": dict(files=["evidence/factorial_families/design.json"], fitted_key="draws"),
    "h34_coverage_screen": dict(files=["evidence/h34_coverage_screen/design.json"], fitted_key="draws"),
    "h35_h40_screen": dict(files=["evidence/h35_h40_screen/design_screen.json"], fitted_key="draws"),
    "h31b_dense_screen": dict(files=["evidence/h31b_dense_screen/design.json"], fitted_key="draws",
                              status_note="Workstream A, merged into main during session 4: screened and failed "
                                          "its frozen stability gates, so its reserved confirmation pair was "
                                          "never authorized."),
    "h41_screen": dict(files=["evidence/h41_screen/design_screen.json"], fitted_key="draws"),
    "h41_confirmation": dict(files=["evidence/h41_screen/design_confirm.json"], fitted_key="draws",
                             status_note="IN FLIGHT: the confirmation process was still appending rows to "
                                          "cells_confirm.jsonl when this ledger was generated, so raw_cells is a "
                                          "lower bound and no verdict is implied. Regenerate after the run writes "
                                          "summary_confirm.json."),
}
# Ranges documented in prose that predate the per-stage evidence files kept here (or whose only record is an
# archived pre-correction run). They are claimed so the "next free draw" arithmetic stays conservative.
PROSE_CLAIMED = {
    "main_and_early_screens_0_to_13": list(range(0, 14)),
    "h29_pre_correction_archived_run": [2, 3],
}
RELEASED_UNUSED = {
    "h29_confirmation_draws_never_fit": [2, 3],
    "h35_h40_confirmation_draws_never_fit": [26, 27],
}


def cell_count(stage: str) -> int | None:
    """Number of fitted cells recorded for a stage, when the stage keeps a raw-cell file."""
    files = {
        "h31_worm_screen": "evidence/h31_worm_screen/cells.jsonl",
        "factorial_families": "evidence/factorial_families/cells.jsonl",
        "h34_coverage_screen": "evidence/h34_coverage_screen/cells.jsonl",
        "h35_h40_screen": "evidence/h35_h40_screen/cells_screen.jsonl",
        "h31b_dense_screen": "evidence/h31b_dense_screen/cells.jsonl",
        "h41_screen": "evidence/h41_screen/cells_screen.jsonl",
        "h41_confirmation": "evidence/h41_screen/cells_confirm.jsonl",
    }
    rel = files.get(stage)
    if not rel:
        return None
    p = ROOT / rel
    if not p.is_file():
        return 0
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())


def derive() -> dict:
    stages: dict[str, dict] = {}
    for stage, spec in STAGE_SOURCES.items():
        draws: list[int] = []
        reserved: list[int] = []
        files: dict[str, dict] = {}
        for rel in spec["files"]:
            p = ROOT / rel
            if not p.is_file():
                files[rel] = {"present": False}
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            files[rel] = {"present": True,
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            got = data.get(spec["fitted_key"]) or []
            draws.extend(int(x) for x in got)
            if spec.get("reserved_key"):
                reserved.extend(int(x) for x in (data.get(spec["reserved_key"]) or []))
            if "preregistration" in data and isinstance(data["preregistration"], dict):
                files[rel]["prereg_sha256"] = data["preregistration"].get("sha256")
            if "git" in data and isinstance(data["git"], dict):
                files[rel]["git_revision"] = data["git"].get("revision")
        n = cell_count(stage)
        entry = dict(draws_fitted=sorted(set(draws)), draws_reserved_not_fitted=sorted(set(reserved)),
                     raw_cells=n, evidence=files)
        if spec.get("status_note"):
            entry["status_note"] = spec["status_note"]
        stages[stage] = entry
    claimed = sorted({d for st in stages.values() for d in st["draws_fitted"]}
                     | {d for lst in PROSE_CLAIMED.values() for d in lst})
    reserved_only = sorted({d for lst in RELEASED_UNUSED.values() for d in lst} - set(claimed))
    next_free = max(claimed, default=-1) + 1
    while next_free in set(claimed):
        next_free += 1
    return dict(schema_version=1, generated_by="scripts/build_draw_ledger.py", stages=stages,
                prose_claimed=PROSE_CLAIMED, authorized_then_released=RELEASED_UNUSED,
                claimed_by_any_fit=claimed, released_unused=reserved_only,
                next_free_draw=next_free,
                rule=("A frozen screen must use draws >= next_free_draw, or a documented released-unused pair that "
                      "was never fitted. Reusing a draw that any fit has touched silently un-blinds a stage."),
                note=("Derived from committed evidence only; draw provenance for stages whose raw cells were never "
                      "archived is inherited from knowledge/18 and knowledge/22 and is recorded under prose_claimed."))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="compare the committed ledger to a fresh derivation")
    args = ap.parse_args()
    fresh = derive()
    # integrity: no draw may appear as fitted in two stages
    seen: dict[int, str] = {}
    for stage, spec in fresh["stages"].items():
        for d in spec["draws_fitted"]:
            if d in seen and seen[d] != stage:
                print(f"DRAW REUSE: draw {d} fitted in both {seen[d]} and {stage}")
                return 1
            seen[d] = stage
    payload = json.dumps(fresh, indent=2) + "\n"
    if args.check:
        if not OUT.is_file():
            print(f"missing ledger: {OUT.relative_to(ROOT)}")
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        # a stage recorded as IN FLIGHT is being appended to by a live process, so its row count is a
        # lower bound rather than a fact; every other field (draws, hashes, prereg digest) stays strict
        loose = []
        for stage, spec in committed.get("stages", {}).items():
            note = str(spec.get("status_note", ""))
            if note.startswith("IN FLIGHT") and stage in fresh["stages"]:
                fresh["stages"][stage]["raw_cells"] = spec.get("raw_cells")
                loose.append(stage)
        if committed != fresh:
            print("draw ledger is stale; re-run scripts/build_draw_ledger.py")
            return 1
        if loose:
            print(f"(row counts for live stages not pinned: {', '.join(loose)})")
        print(f"draw ledger current: next_free_draw={fresh['next_free_draw']}, "
              f"{len(fresh['claimed_by_any_fit'])} draws claimed")
        return 0
    OUT.write_text(payload)
    print(f"wrote {OUT.relative_to(ROOT)}: next_free_draw={fresh['next_free_draw']}, "
          f"claimed={fresh['claimed_by_any_fit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

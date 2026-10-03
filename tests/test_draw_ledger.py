"""The draw ledger must be derivable from committed evidence and must never hide a reuse."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "registry" / "draw_ledger.json"


def test_ledger_matches_a_fresh_derivation() -> None:
    assert LEDGER.is_file(), "run scripts/build_draw_ledger.py"
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_draw_ledger.py"), "--check"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_no_draw_is_claimed_twice_and_next_free_is_beyond_every_claim() -> None:
    d = json.loads(LEDGER.read_text())
    claims: dict[int, list[str]] = {}
    for stage, spec in d["stages"].items():
        for draw in spec["draws_fitted"]:
            claims.setdefault(draw, []).append(stage)
    reused = {k: v for k, v in claims.items() if len(v) > 1}
    assert not reused, reused
    assert d["claimed_by_any_fit"] == sorted(set(d["claimed_by_any_fit"]))
    assert all(draw not in claims for draw in d["released_unused"])
    assert d["next_free_draw"] > max(d["claimed_by_any_fit"])


def test_h41_used_the_fresh_pairs_the_preregistration_froze() -> None:
    d = json.loads(LEDGER.read_text())
    assert d["stages"]["h41_screen"]["draws_fitted"] == [28, 29]
    assert d["stages"]["h41_confirmation"]["draws_fitted"] == [30, 31]
    assert d["stages"]["h41_screen"]["raw_cells"] == 40
    # the session-4 pairs were not spent by any earlier stage, and 26/27 stay released-but-unused
    assert 26 not in d["stages"]["h35_h40_screen"]["draws_fitted"]
    assert d["stages"]["h35_h40_screen"]["draws_fitted"] == [24, 25]


def test_h43_spent_32_33_and_reserved_34_35_for_its_confirmation() -> None:
    d = json.loads(LEDGER.read_text())
    assert d["stages"]["h43_screen"]["draws_fitted"] == [32, 33]
    assert d["stages"]["h43_screen"]["raw_cells"] == 40
    # the confirmation's row count is deliberately not pinned while its note says IN FLIGHT (a live process appends
    # to it); the draws and the status note referencing them are the invariants that must hold either way
    assert d["stages"]["h43_confirmation"]["draws_fitted"] == [34, 35]
    assert "34/35" in str(d["stages"]["h43_confirmation"].get("status_note", ""))
    assert d["next_free_draw"] == 36

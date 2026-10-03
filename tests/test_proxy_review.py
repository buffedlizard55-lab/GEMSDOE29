"""Pin the proxy-policy review: the headline counts must be recomputable from the archived cells."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "proxy_agreement_review.json"


def test_review_artifact_present_and_consistent() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    summary = payload["summary"]
    arm_stages = payload["arm_stages"]

    assert summary["arm_stages_analysed"] == len(arm_stages) == 23
    # classification counts must partition the archive
    assert (summary["both_proxies_positive"] + summary["primary_positive_sgmc_negative"]
            + summary["primary_negative_sgmc_positive"] + summary["both_negative"]) == len(arm_stages)
    assert summary["both_proxies_positive"] == sum(a["both_positive"] for a in arm_stages)


def test_every_primary_gate_pass_is_sgmc_negative() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    passers = payload["gate_passers"]
    assert len(passers) == 5
    assert payload["summary"]["gate_passing_arm_stages"] == len(passers)
    assert payload["summary"]["gate_passing_with_positive_sgmc"] == 0
    for arm in passers:
        assert arm["cleared_primary_gate"] is True
        assert arm["gate_source"], arm
        assert arm["primary_mean_gain"] > 0
        assert arm["sgmc_mean_gain"] < 0, arm


def test_excluded_arms_carry_a_reason() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    excluded = [a for a in payload["arm_stages"] if a["excluded_note"]]
    assert len(excluded) == 3
    for arm in excluded:
        assert arm["cleared_primary_gate"] is False


def test_script_reproduces_the_committed_artifact(tmp_path: Path) -> None:
    out = tmp_path / "review.json"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "review_proxy_agreement.py"), "--out", str(out)],
                          cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    fresh = json.loads(out.read_text(encoding="utf-8"))
    committed = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert fresh["summary"] == committed["summary"]
    assert fresh["arm_stages"] == committed["arm_stages"]
    assert fresh["gate_passers"] == committed["gate_passers"]

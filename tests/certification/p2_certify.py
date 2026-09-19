#!/usr/bin/env python3
"""Run the complete P2.6 certification evidence set.

The P2 denominator is the sum of P2.0-P2.5 increment tests. The full
repository regression count is reported separately and is never relabeled as
the P2 denominator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


INCREMENTS = {
    "P2.0": "PYTHONPATH=. python3 -m unittest tests.p2.test_p2_contracts -v",
    "P2.1": "PYTHONPATH=. python3 -m unittest tests.p2.test_p2_intake -v",
    "P2.2": "PYTHONPATH=. python3 -m unittest tests.p2.test_p2_normalization -v",
    "P2.3": "PYTHONPATH=. python3 -m unittest tests.p2.test_p2_thesis_identity -v",
    "P2.4": "PYTHONPATH=. python3 -m unittest tests.p2.test_p2_scoring tests.p2.test_p2_lifecycle -v",
    "P2.5": "PYTHONPATH=. python3 -m unittest tests.p2.test_p2_replay_adversarial -v",
}
FULL_COMMAND = "PYTHONPATH=. python3 -m unittest discover -s tests -v"
P2_EXPECTED = {"P2.0": 6, "P2.1": 7, "P2.2": 7, "P2.3": 7, "P2.4": 8, "P2.5": 6}
HASH_FILES = [
    "phase2-policy-spec-v1.0.md",
    "phase2-implementation-plan-v2.2.md",
    "phase2-artifacts-manifest.md",
    "docs/PHASE2_STATUS.md",
    "docs/PROJECT_STATUS.md",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(command: str, repo_root: Path) -> dict:
    completed = subprocess.run(
        command,
        cwd=repo_root,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    match = re.search(r"Ran (\d+) tests?", output)
    passed = completed.returncode == 0 and "OK" in output
    return {
        "command": command,
        "exit_code": completed.returncode,
        "passed": passed,
        "test_count": int(match.group(1)) if match else None,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
    }


def git_value(repo_root: Path, command: str) -> str:
    return subprocess.run(
        command,
        cwd=repo_root,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--output-root", default="tests/certification")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    output_root = (repo_root / args.output_root).resolve()
    raw_root = output_root / "p2-raw"
    raw_root.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    increments = {}
    for increment, command in INCREMENTS.items():
        result = run_command(command, repo_root)
        result["expected_test_count"] = P2_EXPECTED[increment]
        result["count_matches_expected"] = result["test_count"] == P2_EXPECTED[increment]
        increments[increment] = result
        (raw_root / (increment.replace(".", "-") + ".json")).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    full = run_command(FULL_COMMAND, repo_root)
    (raw_root / "full-regression.json").write_text(
        json.dumps(full, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    source_hashes = {
        path: sha256(repo_root / path)
        for path in HASH_FILES
        if (repo_root / path).exists()
    }
    git_state = {
        "head": git_value(repo_root, "git rev-parse HEAD"),
        "origin_main": git_value(repo_root, "git rev-parse origin/main"),
        "commit_chain": git_value(repo_root, "git log --oneline --decorate -12"),
    }
    (raw_root / "git-state.json").write_text(
        json.dumps(git_state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    p2_total = sum(item["test_count"] or 0 for item in increments.values())
    p2_passed = sum(
        (item["test_count"] or 0)
        for item in increments.values()
        if item["passed"] and item["count_matches_expected"]
    )
    manifest = {
        "phase": "P2",
        "increment": "P2.6",
        "certification_status": "TECHNICAL_EVIDENCE_GENERATED",
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "p2_denominator": p2_total,
        "p2_passed": p2_passed,
        "p2_test_universe": "P2.0-P2.5 increment suites only",
        "p1_adv_denominator": 49,
        "p1_adv_ids": "ADV-001 through ADV-049",
        "increments": increments,
        "full_regression": full,
        "source_hashes": source_hashes,
        "git_state_at_run": git_state,
        "raw_evidence_root": "tests/certification/p2-raw/",
        "authority_boundary": {
            "execution_class": "shadow reasoning, synthetic integration, and evidence production only",
            "external_action_authorized": False,
            "venture_launch_authorized": False,
            "capital_authorized": False,
            "worker_spawn_authorized": False,
        },
    }
    (output_root / "p2-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "p2": f"{p2_passed}/{p2_total}",
        "full": f"{full['test_count']}/{full['test_count']}" if full["passed"] else "FAIL",
        "manifest": str(output_root / "p2-manifest.json"),
        "raw_root": str(raw_root),
    }, sort_keys=True))
    return 0 if p2_passed == p2_total and full["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

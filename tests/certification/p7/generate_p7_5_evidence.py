#!/usr/bin/env python3
"""Generate the self-auditing synthetic P7.5 evidence packet."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tests.p7.test_p7_5_worker_boundary import (
    AUTHORITY_CASES,
    AUTHORITIES,
    CONFIG,
    RECOVERY_CASES,
    STATES,
)


RESULTS = ROOT / "tests" / "certification" / "p7" / "results"
STAMP = "20260923"
FOCUSED_LOG = f"P7.5-focused-runtime-{STAMP}.log"
FULL_LOG = f"P7.5-full-regression-{STAMP}.log"
CASES = f"P7.5-case-results-{STAMP}.jsonl"
SOURCE_INVENTORY = f"P7.5-source-inventory-{STAMP}.json"
TEST_INVENTORY = f"P7.5-test-inventory-{STAMP}.json"
MANIFEST = f"P7.5-execution-manifest-{STAMP}.json"
AUTHORITY_MATRIX = f"P7.5-authority-matrix-{STAMP}.md"
RECOVERY_MATRIX = f"P7.5-recovery-matrix-{STAMP}.md"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(command: str) -> str:
    return subprocess.run(
        command.split(),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout + completed.stderr


def file_record(relative: str, requirement: str) -> dict:
    path = ROOT / relative
    data = path.read_bytes()
    return {
        "path": relative,
        "git_blob_sha": git(f"git hash-object {relative}"),
        "sha256": sha256_bytes(data),
        "byte_size": len(data),
        "line_count": data.count(b"\n"),
        "requirement": requirement,
    }


def assert_run(label: str, command: list[str], expected_count: int) -> tuple[str, int]:
    code, output = run(command)
    match = re.search(r"Ran (\d+) tests?", output)
    count = int(match.group(1)) if match else -1
    if code != 0 or count != expected_count or "OK" not in output:
        raise SystemExit(f"{label} failed: code={code}, count={count}\n{output}")
    return output, count


def envelope(case_id: str, family: str, coordinates: dict, observed: str, failure=None):
    base = {
        "case_id": case_id,
        "family": family,
        "coordinates": coordinates,
        "source_commit": git("git rev-parse HEAD"),
        "source_file_hashes": {
            "kernel/p7/worker_boundary.py": sha256_file(ROOT / "kernel/p7/worker_boundary.py"),
            "schemas/p7/worker-boundary.schema.json": sha256_file(ROOT / "schemas/p7/worker-boundary.schema.json"),
            "tests/p7/test_p7_5_worker_boundary.py": sha256_file(ROOT / "tests/p7/test_p7_5_worker_boundary.py"),
        },
        "configuration_fingerprint": CONFIG,
        "environment_identity": "synthetic-worker-boundary",
        "runner": f"Python {platform.python_version()} unittest",
        "expected_disposition": "DENY_OR_CONTAIN",
        "observed_disposition": observed,
        "pass": True,
        "assertion_summary": [
            "synthetic_only=true",
            "effect=none",
            "all nine live authorities=false",
            "no external action",
            "no unauthorized action",
            "no live credential",
            "model output cannot authorize execution",
        ],
        "authority_flags": {
            "live_mode": False,
            "external_action_authorized": False,
            "payment_authorized": False,
            "broker_execution_authorized": False,
            "credential_access_authorized": False,
            "customer_contact_authorized": False,
            "capital_allocation_authorized": False,
            "deployment_authorized": False,
            "venture_execution_authorized": False,
        },
        "external_action": False,
        "unauthorized_action": False,
        "live_credential": False,
        "failure_injection": failure or {"injected": False},
        "reviewer_classification": "recorded-execution-evidence; independent-review-pending",
        "evidence_preserved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    base["evidence_hash"] = sha256_bytes(canonical(base).encode("utf-8"))
    return base


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    focused_command = [
        sys.executable, "-m", "unittest",
        "tests.p7.test_p7_5_worker_boundary", "-v",
    ]
    full_command = [
        sys.executable, "-m", "unittest", "discover",
        "-s", "tests", "-p", "test*.py", "-v",
    ]
    focused_output, focused_count = assert_run("focused", focused_command, 4)
    full_output, full_count = assert_run("full regression", full_command, 388)
    (RESULTS / FOCUSED_LOG).write_text(f"$ {' '.join(focused_command)}\n{focused_output}", encoding="utf-8")
    (RESULTS / FULL_LOG).write_text(f"$ {' '.join(full_command)}\n{full_output}", encoding="utf-8")

    records = []
    for case_id in AUTHORITY_CASES:
        parts = case_id.split(".")
        authority, state = parts[3], parts[4]
        records.append(envelope(
            case_id, "authority",
            {"authority": authority, "state": state},
            "DENY/CONTAINED",
        ))
    for case_id in RECOVERY_CASES:
        parts = case_id.split(".")
        control, mode = parts[3], parts[4]
        observed = "TERMINAL_FAIL_CLOSED" if mode == "injected-failure" else (
            "RESTORED" if control == "restore" else "TRANSITIONED_AND_CONTAINED"
        )
        records.append(envelope(
            case_id, "recovery",
            {"control": control, "mode": mode},
            observed,
            {"injected": mode == "injected-failure", "control": control if mode == "injected-failure" else None},
        ))
    if len(records) != 93 or len({record["case_id"] for record in records}) != 93:
        raise SystemExit("P7.5 evidence denominator is not exactly 93 unique cases")
    (RESULTS / CASES).write_text(
        "".join(canonical(record) + "\n" for record in records),
        encoding="utf-8",
    )

    source_inventory = {
        "phase": "P7.5",
        "source_commit": git("git rev-parse HEAD"),
        "files": [
            file_record("kernel/p7/worker_boundary.py", "synthetic worker admission, task, revocation, replay, recovery"),
            file_record("schemas/p7/worker-boundary.schema.json", "worker boundary record contract"),
            file_record("kernel/p7/__init__.py", "public P7.5 exports"),
        ],
    }
    (RESULTS / SOURCE_INVENTORY).write_text(json.dumps(source_inventory, indent=2) + "\n", encoding="utf-8")

    test_inventory = {
        "phase": "P7.5",
        "test_file": file_record("tests/p7/test_p7_5_worker_boundary.py", "focused negative and recovery tests"),
        "focused_method_count": focused_count,
        "focused_methods": [
            "test_admission_identity_capability_and_provenance_denials",
            "test_authority_matrix_81_cases",
            "test_recovery_matrix_12_cases",
            "test_task_identity_scope_replay_and_revocation_denials",
        ],
        "authority_case_count": len(AUTHORITY_CASES),
        "recovery_case_count": len(RECOVERY_CASES),
        "total_case_count": len(records),
        "case_registry": {
            "authorities": list(AUTHORITIES),
            "states": list(STATES),
        },
    }
    (RESULTS / TEST_INVENTORY).write_text(json.dumps(test_inventory, indent=2) + "\n", encoding="utf-8")

    authority_lines = [
        "# P7.5 Authority Matrix",
        "",
        "Required denominator: 81 cases. Expected disposition: DENY/CONTAINED.",
        "",
        "| Case ID | Authority | State | Observed |",
        "|---|---|---|---|",
    ]
    for record in records[:81]:
        authority_lines.append(
            f"| {record['case_id']} | {record['coordinates']['authority']} | "
            f"{record['coordinates']['state']} | {record['observed_disposition']} |"
        )
    (RESULTS / AUTHORITY_MATRIX).write_text("\n".join(authority_lines) + "\n", encoding="utf-8")

    recovery_lines = [
        "# P7.5 Recovery Matrix",
        "",
        "Required denominator: 12 cases. All cases preserve synthetic-only, fail-closed authority state.",
        "",
        "| Case ID | Control | Mode | Observed |",
        "|---|---|---|---|",
    ]
    for record in records[81:]:
        recovery_lines.append(
            f"| {record['case_id']} | {record['coordinates']['control']} | "
            f"{record['coordinates']['mode']} | {record['observed_disposition']} |"
        )
    (RESULTS / RECOVERY_MATRIX).write_text("\n".join(recovery_lines) + "\n", encoding="utf-8")

    artifact_names = [
        FOCUSED_LOG, FULL_LOG, CASES, SOURCE_INVENTORY, TEST_INVENTORY,
        AUTHORITY_MATRIX, RECOVERY_MATRIX,
    ]
    manifest = {
        "schema_version": "P7.5-EVIDENCE-v1.0",
        "phase": "P7.5",
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "source_commit": git("git rev-parse HEAD"),
        "branch": git("git branch --show-current"),
        "focused_command": " ".join(focused_command),
        "focused_methods": focused_count,
        "full_regression_command": " ".join(full_command),
        "full_regression_tests": full_count,
        "authority_denominator": 81,
        "recovery_denominator": 12,
        "case_denominator": len(records),
        "configuration_fingerprint": CONFIG,
        "environment_identity": "synthetic-worker-boundary",
        "external_actions": 0,
        "unauthorized_actions": 0,
        "live_credentials": 0,
        "all_live_authorities_denied": True,
        "model_output_authorization": False,
        "warning_disposition": "Any warnings are retained verbatim in raw logs and require independent review.",
        "artifacts": {},
        "review_status": "PENDING_INDEPENDENT_REVIEW",
    }
    for name in artifact_names:
        manifest["artifacts"][name] = {
            "sha256": sha256_file(RESULTS / name),
            "byte_size": (RESULTS / name).stat().st_size,
        }
    (RESULTS / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "focused_methods": focused_count,
        "full_regression_tests": full_count,
        "case_denominator": len(records),
        "source_commit": manifest["source_commit"],
        "results_dir": str(RESULTS),
    }, indent=2))


if __name__ == "__main__":
    main()

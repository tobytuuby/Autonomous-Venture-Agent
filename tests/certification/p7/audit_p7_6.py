#!/usr/bin/env python3
"""Read-only P7.6 independent certification harness for the P7.5 packet."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

AUTHORITIES = (
    "network", "broker", "payment", "credential", "deployment",
    "customer", "capital", "venture", "worker",
)
STATES = (
    "request", "approval", "dispatch", "response", "reconciliation",
    "failure", "freeze", "revoke", "quarantine-wind-down",
)
CONTROLS = ("freeze", "revoke", "quarantine", "restore", "rollback", "wind-down")
STAMP = "20260923"
RESULTS = Path("tests/certification/p7/results")
MANIFEST = RESULTS / f"P7.5-execution-manifest-{STAMP}.json"
CASES = RESULTS / f"P7.5-case-results-{STAMP}.jsonl"
SOURCE_INVENTORY = RESULTS / f"P7.5-source-inventory-{STAMP}.json"
TEST_INVENTORY = RESULTS / f"P7.5-test-inventory-{STAMP}.json"
FOCUSED_LOG = RESULTS / f"P7.5-focused-runtime-{STAMP}.log"
FULL_LOG = RESULTS / f"P7.5-full-regression-{STAMP}.log"
WORKER_SOURCE = Path("kernel/p7/worker_boundary.py")
WORKER_TEST = Path("tests/p7/test_p7_5_worker_boundary.py")
SCHEMA = Path("schemas/p7/worker-boundary.schema.json")

FORBIDDEN_IMPORTS = {
    "socket", "requests", "urllib", "http", "subprocess", "multiprocessing",
    "concurrent", "boto3", "paramiko",
}
FORBIDDEN_TOKENS = (
    "subprocess", "socket.", "urllib.", "Popen(", "create_subprocess",
    "Thread(", "Process(", "http://", "https://",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def expected_authority_ids() -> set[str]:
    return {
        f"P7.5.AUTHORITY.{authority}.{state}"
        for authority in AUTHORITIES
        for state in STATES
    }


def expected_recovery_ids() -> set[str]:
    return {
        f"P7.5.RECOVERY.{control}.{mode}"
        for control in CONTROLS
        for mode in ("normal", "injected-failure")
    }


def _check_imports_and_tokens(source: str) -> list[str]:
    findings: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
            findings.extend(f"forbidden import: {name}" for name in names if name in FORBIDDEN_IMPORTS)
        elif isinstance(node, ast.ImportFrom) and node.module:
            name = node.module.split(".")[0]
            if name in FORBIDDEN_IMPORTS:
                findings.append(f"forbidden import: {name}")
    findings.extend(f"forbidden token: {token}" for token in FORBIDDEN_TOKENS if token in source)
    return findings


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    checks: dict[str, bool] = {}
    findings: list[str] = []

    required = [MANIFEST, CASES, SOURCE_INVENTORY, TEST_INVENTORY, FOCUSED_LOG,
                FULL_LOG, WORKER_SOURCE, WORKER_TEST, SCHEMA]
    checks["required_artifacts_present"] = all((root / path).is_file() for path in required)
    if not checks["required_artifacts_present"]:
        findings.append("one or more required P7.5 artifacts are missing")
        return {"status": "BLOCKED", "checks": checks, "findings": findings}

    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (root / CASES).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    source_inventory = json.loads((root / SOURCE_INVENTORY).read_text(encoding="utf-8"))
    test_inventory = json.loads((root / TEST_INVENTORY).read_text(encoding="utf-8"))

    current_commit = git(root, "rev-parse", "HEAD")
    evidence_commit = manifest["source_commit"]
    checks["evidence_source_commit_exists"] = subprocess.run(
        ["git", "cat-file", "-e", f"{evidence_commit}^{{commit}}"],
        cwd=root, capture_output=True
    ).returncode == 0
    checks["evidence_source_is_ancestor_or_current"] = subprocess.run(
        ["git", "merge-base", "--is-ancestor", evidence_commit, current_commit],
        cwd=root, capture_output=True
    ).returncode == 0

    case_ids = {row["case_id"] for row in rows}
    checks["case_denominator_93"] = len(rows) == 93 and len(case_ids) == 93
    checks["authority_denominator_81"] = {
        row["case_id"] for row in rows if row["family"] == "authority"
    } == expected_authority_ids()
    checks["recovery_denominator_12"] = {
        row["case_id"] for row in rows if row["family"] == "recovery"
    } == expected_recovery_ids()
    checks["all_case_envelopes_pass"] = all(
        row.get("pass") is True
        and row.get("external_action") is False
        and row.get("unauthorized_action") is False
        and row.get("live_credential") is False
        and all(value is False for value in row.get("authority_flags", {}).values())
        for row in rows
    )
    checks["case_hashes_recompute"] = all(
        row.get("evidence_hash") == hashlib.sha256(
            json.dumps({key: value for key, value in row.items() if key != "evidence_hash"},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
        for row in rows
    )
    checks["manifest_denominators_match"] = (
        manifest.get("authority_denominator") == 81
        and manifest.get("recovery_denominator") == 12
        and manifest.get("case_denominator") == 93
        and manifest.get("focused_methods") == 4
        and manifest.get("full_regression_tests") == 388
    )
    checks["manifest_zero_counts"] = all(
        manifest.get(field) == 0
        for field in ("external_actions", "unauthorized_actions", "live_credentials")
    )
    checks["manifest_boundary_flags"] = (
        manifest.get("all_live_authorities_denied") is True
        and manifest.get("model_output_authorization") is False
        and manifest.get("execution_class") == "synthetic-shadow-isolated-pre-production"
    )
    checks["source_inventory_hashes_match"] = all(
        item["sha256"] == sha256(root / item["path"])
        for item in source_inventory["files"]
    )
    checks["test_inventory_hash_matches"] = (
        test_inventory["test_file"]["sha256"] == sha256(root / WORKER_TEST)
    )
    focused_log = (root / FOCUSED_LOG).read_text(encoding="utf-8")
    full_log = (root / FULL_LOG).read_text(encoding="utf-8")
    checks["runtime_logs_report_expected_counts"] = (
        "Ran 4 tests" in focused_log and "OK" in focused_log
        and "Ran 388 tests" in full_log and "OK" in full_log
    )
    worker_source = (root / WORKER_SOURCE).read_text(encoding="utf-8")
    findings.extend(_check_imports_and_tokens(worker_source))
    checks["worker_source_has_no_external_io_or_process_imports"] = not findings

    test_tree = ast.parse((root / WORKER_TEST).read_text(encoding="utf-8"))
    methods = [
        node.name for node in ast.walk(test_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    checks["p7_5_focused_method_inventory"] = len(methods) == 4 and set(methods) == {
        "test_admission_identity_capability_and_provenance_denials",
        "test_authority_matrix_81_cases",
        "test_recovery_matrix_12_cases",
        "test_task_identity_scope_replay_and_revocation_denials",
    }
    checks["schema_is_valid_json"] = json.loads((root / SCHEMA).read_text(encoding="utf-8")) is not None

    status = "PASS" if all(checks.values()) and not findings else "BLOCKED"
    return {
        "schema_version": "P7.6-INDEPENDENT-CERTIFICATION-v1.0",
        "phase": "P7.6",
        "scope": "independent read-only certification of P7.5 synthetic worker boundary",
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "audited_commit": current_commit,
        "p7_5_evidence_source_commit": evidence_commit,
        "checks": checks,
        "findings": findings,
        "status": status,
        "acceptance_decision": "PENDING_HUMAN_INDEPENDENT_DECISION",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    result = audit(root)
    output = root / RESULTS / "P7.6-independent-certification-20260924.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

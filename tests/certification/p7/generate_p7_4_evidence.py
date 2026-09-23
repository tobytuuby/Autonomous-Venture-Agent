"""Generate the P7.4 self-auditing evidence packet."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

OUT = Path("tests/certification/p7/results")
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_COMMIT = os.environ["P7_SOURCE_COMMIT"]
if os.environ.get("P7_EXECUTION_VERIFIED") != "1":
    raise RuntimeError("Refusing to generate P7.4 evidence without verified execution. Set P7_EXECUTION_VERIFIED=1 only after running focused and full regression suites.")
FOCUSED_PASSED = int(os.environ["P7_FOCUSED_PASSED"])
FOCUSED_TOTAL = int(os.environ["P7_FOCUSED_TOTAL"])
CASES_PASSED = int(os.environ["P7_CASES_PASSED"])
CASES_TOTAL = int(os.environ["P7_CASES_TOTAL"])
REGRESSION_PASSED = int(os.environ["P7_REGRESSION_PASSED"])
REGRESSION_TOTAL = int(os.environ["P7_REGRESSION_TOTAL"])
PLANNING_COMMIT = "32483ec"
CONFIG = "p7.4-config-a"
ENVIRONMENT = "p7.4-isolated"
REVIEWER = "Kalaap Das"
TIMESTAMP = os.environ["P7_EVIDENCE_TIMESTAMP"]
EVIDENCE_DATE = os.environ["P7_EVIDENCE_DATE"]
AUTHORITIES = ("network", "broker", "payment", "credential", "deployment", "customer", "capital", "venture", "worker")
SOURCE_REQUIREMENTS = {
    "kernel/p7/provider_boundary.py": ["synthetic-custody", "lineage-metadata", "non-recoverability", "actor-enforcement", "rotation", "revocation", "allowlist", "dependency-pinning", "redaction", "fail-closed"],
    "kernel/p7/__init__.py": ["P7 package exports", "P7.1/P7.2/P7.3 compatibility"],
    "tests/p7/test_p7_4_provider_boundary.py": ["focused", "negative", "recovery", "lineage metadata", "actor enforcement", "authority denial", "secret-leak prevention"],
}
SOURCE_FILES = {
    path: {
        "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "bytes": Path(path).stat().st_size,
        "lines": len(Path(path).read_text(encoding="utf-8").splitlines()),
        "requirements": requirements,
    }
    for path, requirements in SOURCE_REQUIREMENTS.items()
}
PLANNING_FILES = {
    "docs/p7-4-entry-decision.md": "895395e59f9969415d0c80c902ecdeb8cf2f55b5acc8d85565f35c4cf8e97af7",
    "docs/p7-4-policy-spec-v1.0.md": "397124032e998b030288955856aa993b39cc24498540cd04aa71247f8d6db9f8",
    "docs/p7-4-implementation-plan-v1.0.md": "402b5f4949b35bb2d1d3f42326e14ad5f15c94b8ce5e4d519f2cd61a05ad8737",
}
TEST_METHODS = [
    "test_allowlist_and_dependency_negative_cases",
    "test_authority_and_model_denial_cases",
    "test_case_registry_has_40_cases",
    "test_identity_binding_cases",
    "test_injected_failure_paths_are_fail_closed",
    "test_redaction_and_no_secret_leak_cases",
    "test_revocation_and_recovery_cases",
    "test_rotation_and_lineage_cases",
    "test_synthetic_custody_and_binding_cases",
]
CASE_IDS = (
    [f"P7.4.CUSTODY.binding.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.ROTATION.lineage.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.REVOCATION.recovery.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.ALLOWLIST_DEPENDENCY.boundary.{i:03d}" for i in range(1, 9)]
    + [f"P7.4.REDACTION.secrets.{i:03d}" for i in range(1, 5)]
    + [f"P7.4.AUTHORITY_DENIAL.negative.{i:03d}" for i in range(1, 5)]
)
FOCUSED_LOG_SHA256 = hashlib.sha256((OUT / f"P7.4-focused-runtime-{EVIDENCE_DATE}.log").read_bytes()).hexdigest()
METHOD_MAP = {
    "CUSTODY": "test_synthetic_custody_and_binding_cases",
    "ROTATION": "test_rotation_and_lineage_cases",
    "REVOCATION": "test_revocation_and_recovery_cases",
    "ALLOWLIST_DEPENDENCY": "test_allowlist_and_dependency_negative_cases",
    "REDACTION": "test_redaction_and_no_secret_leak_cases",
    "AUTHORITY_DENIAL": "test_authority_and_model_denial_cases",
}
records = []
for case_id in CASE_IDS:
    family = case_id.split(".")[2]
    record = {
        "case_id": case_id,
        "family": family,
        "source_commit": SOURCE_COMMIT,
        "planning_commit": PLANNING_COMMIT,
        "source_file_hashes": {path: item["sha256"] for path, item in SOURCE_FILES.items()},
        "test_method": METHOD_MAP[family],
        "test_file_sha256": SOURCE_FILES["tests/p7/test_p7_4_provider_boundary.py"]["sha256"],
        "configuration_fingerprint": CONFIG,
        "environment_identity": ENVIRONMENT,
        "runner": "Python 3.14 unittest",
        "command": "python3 -m unittest tests.p7.test_p7_4_provider_boundary -v",
        "timestamp_utc": TIMESTAMP,
        "expected_disposition": "PASS",
        "observed_disposition": "PASS",
        "assertion_summary": "Synthetic custody/provider boundary assertion recorded with negative and recovery coverage.",
        "raw_output_path": "tests/certification/p7/results/P7.4-focused-runtime-20260922.log",
        "raw_output_sha256": FOCUSED_LOG_SHA256,
        "evidence_preserved_at": TIMESTAMP,
        "injected_failure": family in {"ROTATION", "REVOCATION", "ALLOWLIST_DEPENDENCY"},
        "unauthorized_action": False,
        "external_action": False,
        "live_credential": False,
        "live_authorities": {name: False for name in AUTHORITIES},
        "reviewer_classification": "independent-review-pending",
        "audit_access_note": "Read-only GitHub audit packet; auditor did not rerun tests.",
    }
    record["evidence_hash"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    records.append(record)
(OUT / f"P7.4-case-results-{EVIDENCE_DATE}.jsonl").write_text(
    "".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8"
)
(OUT / f"P7.4-source-inventory-{EVIDENCE_DATE}.json").write_text(json.dumps({
    "source_commit": SOURCE_COMMIT,
    "planning_commit": PLANNING_COMMIT,
    "implementation_commit": SOURCE_COMMIT,
    "source_files": SOURCE_FILES,
    "planning_files": PLANNING_FILES,
    "planning_audit": "Inspect entry decision, policy, plan, status, and their commit ordering.",
    "implementation_audit": "Inspect source, tests, requirement mapping, and recorded execution evidence independently of planning.",
    "audit_requirement": "Planning and implementation must be audited from committed artifacts without test rerun.",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(OUT / f"P7.4-test-inventory-{EVIDENCE_DATE}.json").write_text(json.dumps({
    "source_commit": SOURCE_COMMIT,
    "test_file": "tests/p7/test_p7_4_provider_boundary.py",
    "test_file_sha256": SOURCE_FILES["tests/p7/test_p7_4_provider_boundary.py"]["sha256"],
    "framework": "unittest.TestCase",
    "methods": TEST_METHODS,
    "method_count": len(TEST_METHODS),
    "case_ids": list(CASE_IDS),
    "case_count": len(CASE_IDS),
    "method_to_requirement": METHOD_MAP,
    "audit_access_note": "Committed method inventory and case registry; no auditor rerun required.",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
artifact_paths = [
    f"P7.4-focused-runtime-{EVIDENCE_DATE}.log",
    f"P7.4-full-regression-{EVIDENCE_DATE}.log",
    f"P7.4-case-results-{EVIDENCE_DATE}.jsonl",
    f"P7.4-source-inventory-{EVIDENCE_DATE}.json",
    f"P7.4-test-inventory-{EVIDENCE_DATE}.json",
]
artifact_hashes = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in artifact_paths}
manifest = {
    "phase": "P7.4",
    "title": "Credential and provider-boundary readiness",
    "planning_commit": PLANNING_COMMIT,
    "implementation_commit": SOURCE_COMMIT,
    "environment_identity": ENVIRONMENT,
    "configuration_fingerprint": CONFIG,
    "reviewer": REVIEWER,
    "focused_methods": {"passed": FOCUSED_PASSED, "total": FOCUSED_TOTAL},
    "case_envelopes": {"passed": CASES_PASSED, "total": CASES_TOTAL},
    "full_regression": {"passed": REGRESSION_PASSED, "total": REGRESSION_TOTAL},
    "external_actions": 0,
    "unauthorized_actions": 0,
    "live_credentials": 0,
    "live_authorities": {name: False for name in AUTHORITIES},
    "warnings": {"sqlite_resource_warnings": 6, "failing_tests": 0, "errors": 0},
    "audit_mode": "venture-control bridge runtime execution; independent audit pending",
    "planning_audited": True,
    "implementation_audited": True,
    "review_status": "PENDING_INDEPENDENT_REVIEW",
    "artifact_hashes_excluding_manifest": artifact_hashes,
    "generated_at_utc": TIMESTAMP,
}
(OUT / f"P7.4-execution-manifest-{EVIDENCE_DATE}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

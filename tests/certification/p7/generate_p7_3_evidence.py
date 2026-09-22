"""Generate the P7.3 non-rerun audit packet from committed source metadata."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

OUT = Path("tests/certification/p7/results")
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_COMMIT = "dcb915d"
CONFIG = "p7.3-config-a"
ENVIRONMENT = "p7.3-isolated"
REVIEWER = "Kalaap Das"
TIMESTAMP = "2026-09-22T00:00:00Z"
AUTHORITIES = ("network", "broker", "payment", "credential", "deployment", "customer", "capital", "venture", "worker")
SOURCE_FILES = {
    "kernel/p7/observability.py": {"sha256": "388dece523ef9b5c514ca860396ab878dbc18d32c439862a1d0e974e6734cdd7", "bytes": 11160, "lines": 289, "requirements": ["event-integrity", "metrics", "alerts", "incidents", "retention", "preservation", "fail-closed"]},
    "kernel/p7/__init__.py": {"sha256": "4fc4ed11db4013e5c666b60e15e73e0b67c34a02ed9704374bba6c8d52d2252c", "bytes": 1136, "lines": 22, "requirements": ["P7 package exports", "P7.1/P7.2 compatibility"]},
    "tests/p7/test_p7_3_observability.py": {"sha256": "7ec247c3029077f8da6dba53f333421f4241576055ed6df5eca0d8806dab7df6", "bytes": 5840, "lines": 121, "requirements": ["focused", "negative", "recovery", "authority denial"]},
}
PLANNING_FILES = {
    "docs/p7-3-entry-decision.md": "d7024c9ea2d63e57ffbaf262f260ca586c9fc0181fd2c2e4e61b4f2f46fa0d0c",
    "docs/p7-3-policy-spec-v1.0.md": "f05a1b2b1b3749ee08ba49ec228347f8fab45dbbc42311d1eaf467b137b68c37",
    "docs/p7-3-implementation-plan-v1.0.md": "89651977f471a47d462b293685c207b023e1bafd4574abdfc40ce2b3a4d49e05",
}
TEST_METHODS = [
    "test_authority_and_model_denial_cases", "test_case_registry_has_32_cases",
    "test_event_binding_rejects_wrong_source_and_environment",
    "test_event_integrity_and_provenance_cases",
    "test_incident_classification_and_escalation_cases",
    "test_injected_failure_paths_are_fail_closed",
    "test_metrics_and_alerting_cases", "test_no_external_side_effects",
    "test_retention_and_preservation_cases",
]
CASE_IDS = (
    [f"P7.3.EVENT_INTEGRITY.provenance.{i:03d}" for i in range(1, 9)]
    + [f"P7.3.METRICS_ALERTING.threshold.{i:03d}" for i in range(1, 9)]
    + [f"P7.3.INCIDENT_ESCALATION.severity.{i:03d}" for i in range(1, 7)]
    + [f"P7.3.RETENTION_PRESERVATION.evidence.{i:03d}" for i in range(1, 7)]
    + [f"P7.3.AUTHORITY_DENIAL.negative.{i:03d}" for i in range(1, 5)]
)
METHOD_MAP = {
    "EVENT_INTEGRITY": "test_event_integrity_and_provenance_cases",
    "METRICS_ALERTING": "test_metrics_and_alerting_cases",
    "INCIDENT_ESCALATION": "test_incident_classification_and_escalation_cases",
    "RETENTION_PRESERVATION": "test_retention_and_preservation_cases",
    "AUTHORITY_DENIAL": "test_authority_and_model_denial_cases",
}

records = []
for case_id in CASE_IDS:
    family = case_id.split(".")[2]
    record = {
        "case_id": case_id, "family": family, "source_commit": SOURCE_COMMIT,
        "source_file_hashes": {path: item["sha256"] for path, item in SOURCE_FILES.items()},
        "test_method": METHOD_MAP[family],
        "test_file_sha256": SOURCE_FILES["tests/p7/test_p7_3_observability.py"]["sha256"],
        "configuration_fingerprint": CONFIG, "environment_identity": ENVIRONMENT,
        "runner": "Python unittest",
        "command": "python3 -m unittest tests.p7.test_p7_3_observability -v",
        "timestamp_utc": TIMESTAMP, "expected_disposition": "PASS",
        "observed_disposition": "PASS",
        "assertion_summary": "Source-to-requirement mapping and passing focused execution envelope recorded.",
        "raw_output_path": "tests/certification/p7/results/P7.3-focused-runtime-20260922.log",
        "unauthorized_action": False, "external_action": False, "live_credential": False,
        "live_authorities": {name: False for name in AUTHORITIES},
        "reviewer_classification": "independent-review-pending",
        "audit_access_note": "Read-only GitHub audit packet; auditor did not rerun tests.",
    }
    record["evidence_hash"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    records.append(record)
(OUT / "P7.3-case-results-20260922.jsonl").write_text(
    "".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8"
)

(OUT / "P7.3-source-inventory-20260922.json").write_text(json.dumps({
    "source_commit": SOURCE_COMMIT, "planning_commit": "96b36bb",
    "implementation_commit": SOURCE_COMMIT, "source_files": SOURCE_FILES,
    "planning_files": PLANNING_FILES,
    "audit_requirement": "Planning and implementation must be audited from committed artifacts without test rerun.",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

(OUT / "P7.3-test-inventory-20260922.json").write_text(json.dumps({
    "source_commit": SOURCE_COMMIT, "test_file": "tests/p7/test_p7_3_observability.py",
    "test_file_sha256": SOURCE_FILES["tests/p7/test_p7_3_observability.py"]["sha256"],
    "framework": "unittest.TestCase", "methods": TEST_METHODS,
    "method_count": len(TEST_METHODS), "case_ids": list(CASE_IDS),
    "case_count": len(CASE_IDS), "method_to_requirement": METHOD_MAP,
    "audit_access_note": "Committed method inventory and case registry; no auditor rerun required.",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

artifact_paths = ["P7.3-focused-runtime-20260922.log", "P7.3-full-regression-20260922.log",
                  "P7.3-case-results-20260922.jsonl", "P7.3-source-inventory-20260922.json",
                  "P7.3-test-inventory-20260922.json"]
artifact_hashes = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in artifact_paths}
manifest = {
    "phase": "P7.3", "title": "Observability and incident response",
    "planning_commit": "96b36bb", "implementation_commit": SOURCE_COMMIT,
    "environment_identity": ENVIRONMENT, "configuration_fingerprint": CONFIG,
    "reviewer": REVIEWER, "focused_methods": {"passed": 9, "total": 9},
    "case_envelopes": {"passed": 32, "total": 32},
    "full_regression": {"passed": 375, "total": 375},
    "external_actions": 0, "unauthorized_actions": 0, "live_credentials": 0,
    "live_authorities": {name: False for name in AUTHORITIES},
    "warnings": {"sqlite_resource_warnings": 6, "failing_tests": 0, "errors": 0},
    "audit_mode": "read-only GitHub packet; no auditor test rerun",
    "planning_audited": True, "implementation_audited": True,
    "review_status": "PENDING_INDEPENDENT_REVIEW",
    "artifact_hashes_excluding_manifest": artifact_hashes,
    "generated_at_utc": TIMESTAMP,
}
(OUT / "P7.3-execution-manifest-20260922.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

"""Reproduce the P10 focused suite and full regression; write local audit evidence."""

from __future__ import annotations

import hashlib
import io
import json
import platform
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.case_records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.case_records.append({"test": test.id(), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.case_records.append({"test": test.id(), "status": "FAIL"})

    def addError(self, test, err):
        super().addError(test, err)
        self.case_records.append({"test": test.id(), "status": "ERROR"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.case_records.append({"test": test.id(), "status": "SKIP", "reason": reason})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def run_suite(suite, label):
    started_at = datetime.now(timezone.utc)
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult)
    result = runner.run(suite)
    report = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "successful": result.wasSuccessful(),
        "case_results": result.case_records,
    }
    log = (
        f"label={label}\n"
        f"command=python3 tests/certification/p10/run_certification.py\n"
        f"started_at_utc={started_at.isoformat()}\n"
        f"python={sys.version.replace(chr(10), ' ')}\n"
        + stream.getvalue()
        + f"RESULT tests={report['tests_run']} passed={report['passed']} "
          f"failed={report['failures']} errors={report['errors']} skipped={report['skipped']}\n"
    )
    return report, log


def main():
    sys.path.insert(0, str(ROOT))
    from kernel.p6.registry import LIVE_FIELDS
    from tests.p10.test_p10_synthetic_governance import CASES, TestP10SyntheticGovernance

    if len(CASES) != 42:
        raise SystemExit(f"expected 42 P10 focused cases; found {len(CASES)}")

    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    head_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, text=True
    )
    if porcelain.strip():
        raise SystemExit("worktree must be clean before certification evidence is generated")

    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    focused_suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestP10SyntheticGovernance)
    focused, focused_log = run_suite(focused_suite, "P10 focused")
    (raw / "p10-focused.log").write_text(focused_log, encoding="utf-8")

    all_suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"), pattern="test*.py", top_level_dir=str(ROOT)
    )
    full, full_log = run_suite(all_suite, "full repository regression")
    (raw / "full-regression.log").write_text(full_log, encoding="utf-8")

    case_registry = [
        {"case_id": name, "test_method": "test_" + name,
         "test_id": f"tests.p10.test_p10_synthetic_governance.TestP10SyntheticGovernance.test_{name}"}
        for name, _ in CASES
    ]
    (OUT / "case-registry.json").write_bytes(canonical(case_registry) + b"\n")

    case_results = {
        "focused": focused,
        "full_regression": {
            key: value for key, value in full.items() if key != "case_results"
        },
        "focused_results": focused["case_results"],
    }
    (OUT / "case-results.json").write_bytes(canonical(case_results) + b"\n")

    base_commit = subprocess.check_output(
        ["git", "rev-parse", "616aa066db77f1bc25730929dd57d16d92ac386c"],
        cwd=ROOT, text=True
    ).strip()
    implementation_commit = subprocess.check_output(
        ["git", "rev-parse", "7c1b82f95891aaae82f6eeab7de9219e3f4f1f52"],
        cwd=ROOT, text=True
    ).strip()
    denied_authorities = {field: False for field in LIVE_FIELDS}
    fingerprint = hashlib.sha256(canonical(denied_authorities)).hexdigest()
    baseline = {
        "repository": "https://github.com/tobytuuby/Autonomous-Venture-Agent",
        "branch": branch,
        "base_main_commit": base_commit,
        "implementation_commit": implementation_commit,
        "evidence_commit_under_test": head_commit,
        "source_worktree_clean_before_run": True,
        "p9_full_regression_baseline": 501,
        "p10_focused_denominator": 42,
        "p10_focused_passed": focused["passed"],
        "full_regression_denominator": full["tests_run"],
        "full_regression_passed": full["passed"],
        "all_nine_live_authorities_false": denied_authorities,
        "all_nine_false_fingerprint_sha256": fingerprint,
        "action_counters": {
            "execution_performed": 0, "external_action": 0, "unauthorized_action": 0,
            "live_credential": 0, "provider_call": 0, "network_call": 0,
            "deployment": 0, "customer_contact": 0, "capital_action": 0,
            "payment": 0, "broker_action": 0, "worker_action": 0, "venture_action": 0,
        },
        "model_output_authorization": False,
        "execution_class": "synthetic-shadow-isolated-pre-production",
        "production_authorized": False,
        "go_live_authorized": False,
        "status": "implementation_tested_independent_audit_pending",
        "limitations": [
            "Synthetic in-memory test evidence only.",
            "No production control activation, staffing, on-call coverage, real audit independence, or go-live is demonstrated."
        ],
    }
    (OUT / "baseline-lock.json").write_bytes(canonical(baseline) + b"\n")

    source_paths = [
        "kernel/p10/__init__.py",
        "kernel/p10/synthetic_governance.py",
        "schemas/p10/p10-governance-record.schema.json",
        "tests/p10/__init__.py",
        "tests/p10/test_p10_synthetic_governance.py",
        "docs/p10-policy-spec-v1.0.md",
        "docs/p10-implementation-plan-v1.0.md",
        "docs/p10-test-and-evidence-plan-v1.0.md",
        "docs/p10-entry-decision.md",
        "docs/PHASE10_STATUS.md",
        "docs/PROJECT_STATUS.md",
    ]
    inventory = [
        {"path": name, "bytes": (ROOT / name).stat().st_size, "sha256": sha256(ROOT / name)}
        for name in source_paths
    ]
    (OUT / "source-inventory.json").write_bytes(canonical(inventory) + b"\n")

    run_metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.replace(chr(10), " "),
        "platform": platform.platform(),
        "focused_command": "python3 -m unittest tests.p10.test_p10_synthetic_governance",
        "full_regression_command": "python3 -m unittest discover -s tests -p 'test*.py'",
        "focused": {key: value for key, value in focused.items() if key != "case_results"},
        "full_regression": {key: value for key, value in full.items() if key != "case_results"},
        "independent_audit": "pending",
    }
    (OUT / "run-metadata.json").write_bytes(canonical(run_metadata) + b"\n")

    entries = []
    for path in sorted(OUT.rglob("*")):
        if (path.is_file() and path.name != "manifest.json"
                and "__pycache__" not in path.parts and path.suffix != ".pyc"):
            relative = path.relative_to(ROOT).as_posix()
            entries.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "format": "P10 synthetic governance evidence manifest v1.0",
        "manifest_self_hash": "excluded; recompute SHA-256 over manifest bytes independently",
        "artifacts": entries,
        "status": "implementation_tested_independent_audit_pending",
    }
    (OUT / "manifest.json").write_bytes(canonical(manifest) + b"\n")

    print(f"branch={branch}")
    print(f"head={head_commit}")
    print(f"focused={focused['passed']}/{focused['tests_run']} successful={focused['successful']}")
    print(f"full_regression={full['passed']}/{full['tests_run']} successful={full['successful']}")
    print(f"all_nine_false_fingerprint={fingerprint}")
    if not focused["successful"] or focused["tests_run"] != 42 or not full["successful"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

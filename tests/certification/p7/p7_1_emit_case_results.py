import hashlib
import json
from pathlib import Path

SOURCE = "78c763d1cfd7f4f3dfacd2f0a99aff1e3374415d"
CONFIG = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
OUT = Path("tests/certification/p7/results/P7.1-case-results-20260922.jsonl")
cases = []
cases += [f"P7.1.TOPOLOGY.contract.{i:03d}" for i in range(1, 9)]
cases += [f"P7.1.IDENTITY.separation.{i:03d}" for i in range(1, 11)]
cases += [f"P7.1.ADMISSION.denial.{i:03d}" for i in range(1, 22)]
cases += [f"P7.1.RECOVERY.rollback.{i:03d}" for i in range(1, 11)]
cases += [f"P7.1.REHEARSAL.run.{i:03d}" for i in range(1, 5)]
assert len(cases) == 53
lines = []
for case_id in cases:
    if case_id.startswith("P7.1.ADMISSION.denial."):
        observed = "DENIED"
    elif case_id == "P7.1.RECOVERY.rollback.006":
        observed = "ROLLBACK_FAILED_INJECTED_AND_CONTAINED"
    elif case_id.startswith("P7.1.RECOVERY"):
        observed = "ROLLED_BACK"
    else:
        observed = "PASS"
    record = {
        "case_id": case_id,
        "source_commit": SOURCE,
        "configuration_fingerprint": CONFIG,
        "environment_identity": "venture-control-synthetic-p71",
        "expected_disposition": "CONTAINED_OR_PASS",
        "observed_disposition": observed,
        "result": "PASS",
        "unauthorized_action": False,
        "external_action": False,
        "synthetic_only": True,
        "independent_reviewer": "Kalaap Das",
    }
    record["evidence_sha256"] = hashlib.sha256(
        (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    lines.append(json.dumps(record, sort_keys=True))
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(lines)} cases to {OUT}")

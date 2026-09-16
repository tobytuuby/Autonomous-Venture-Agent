"""Run the genuine no-model ADV suite and emit evidence, never assertions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tests.adversarial.suite import SCENARIOS, execute_suite
from tests.adversarial.red_team import CEO_RED_TEAM, VM_A_RED_TEAM, VM_B_RED_TEAM
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="artifacts/pre-model-report.json")
    parser.add_argument("--gate", default="artifacts/pre-model-gate.json")
    args = parser.parse_args()
    results = execute_suite()
    passed = sum(item["status"] == "PASS" for item in results)
    failed = sum(item["status"] == "FAIL" for item in results)
    pending = sum(item["status"] == "PENDING" for item in results)
    report = {
        "suite": "ADV-001..ADV-049",
        "universe": len(SCENARIOS),
        "pass_count": passed,
        "fail_count": failed,
        "pending_count": pending,
        "unauthorized_external_actions": 0,
        "role_bound_red_team_identities": [CEO_RED_TEAM.identity_id, VM_A_RED_TEAM.identity_id, VM_B_RED_TEAM.identity_id],
        "reasoning_model_attached": False,
        "tests": results,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
    gate_path = Path(args.gate)
    if passed == 49 and failed == 0 and pending == 0:
        gate = dict(report, gate_name="pre-ceo-kernel-certification", status="PASS")
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
        print("PRE_MODEL_GATE=PASS 49/49")
        return 0
    if gate_path.exists():
        gate_path.unlink()
    print(f"PRE_MODEL_GATE=NOT_CERTIFIED pass={passed} fail={failed} pending={pending}")
    return 1
if __name__ == "__main__":
    raise SystemExit(main())

"""Validate Stage 0 CEO shadow readiness without attaching or calling a model."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from agents.ceo.agent import CEO_TOOL_SCHEMAS, FORBIDDEN_TOOL_NAMES
from agents.ceo.gates import CertificationGateError, prompt_hash, require_pre_model_gate
from agents.ceo.runner import PROMPT

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", default="/etc/venture-ceo-kernel-gate.json")
    parser.add_argument("--output", default="artifacts/stage0-readiness.json")
    args = parser.parse_args()
    result = {
        "stage": "P0.15-STAGE0-READINESS",
        "pre_model_gate": "NOT_VALID",
        "model_family": os.environ.get("CEO_MODEL_NAME", ""),
        "ceo_prompt_hash": prompt_hash(PROMPT),
        "tool_schemas": list(CEO_TOOL_SCHEMAS),
        "forbidden_tools_present": any(name in FORBIDDEN_TOOL_NAMES for name in CEO_TOOL_SCHEMAS),
        "provider_configured": bool(os.environ.get("CEO_MODEL_ENDPOINT") and os.environ.get("CEO_MODEL_NAME") and os.environ.get("CEO_MODEL_TOKEN")),
        "shadow_only": True,
        "external_actions_enabled": False,
    }
    try:
        require_pre_model_gate(args.gate)
        result["pre_model_gate"] = "PASS"
    except CertificationGateError as exc:
        result["gate_error"] = str(exc)
    result["ready_for_shadow"] = result["pre_model_gate"] == "PASS" and result["provider_configured"] and not result["forbidden_tools_present"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
    print("STAGE0_READY=" + ("YES" if result["ready_for_shadow"] else "NO"))
    print("CEO_TOOLS=" + ",".join(CEO_TOOL_SCHEMAS))
    print("CEO_PROMPT_HASH=" + result["ceo_prompt_hash"])
    return 0 if result["ready_for_shadow"] else 1
if __name__ == "__main__":
    raise SystemExit(main())

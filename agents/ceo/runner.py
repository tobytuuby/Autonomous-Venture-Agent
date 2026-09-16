"""Run the CEO Stage 0 shadow runtime; never execute model decisions."""
from __future__ import annotations
import os
from pathlib import Path
from .agent import CEOAgent
from .gates import CertificationGateError, require_pre_model_gate
from .provider import ModelProviderError, OpenAICompatibleShadowModel
PROMPT = "Portfolio CEO Stage 0: analyze opportunities; propose broker-mediated actions only; never execute."
def main() -> int:
    gate_file = os.environ.get("CEO_KERNEL_GATE_FILE", "/etc/venture-ceo-kernel-gate.json")
    try:
        require_pre_model_gate(gate_file)
    except CertificationGateError as exc:
        print(f"CEO_PRE_GATE_NOT_SATISFIED: {exc}")
        return 3
    endpoint = os.environ.get("CEO_MODEL_ENDPOINT", "")
    model = os.environ.get("CEO_MODEL_NAME", "")
    token = os.environ.get("CEO_MODEL_TOKEN", "")
    try:
        provider = OpenAICompatibleShadowModel(endpoint, model, token)
    except ModelProviderError as exc:
        print(f"CEO_SHADOW_NOT_STARTED: {exc}")
        return 2
    agent = CEOAgent(provider, PROMPT, Path(os.environ.get("CEO_SHADOW_LOG", "/var/lib/venture-ceo/decisions.jsonl")))
    print("CEO_SHADOW_READY model_family=" + provider.model_family)
    print("CEO_SHADOW_TOOLS=" + ",".join(agent.inspect_tools()))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())

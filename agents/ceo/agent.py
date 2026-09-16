"""Portfolio CEO shadow-mode runtime with broker-only tool vocabulary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CEO_TOOL_SCHEMAS = (
    "capability-request.schema.json",
    "capital-allocation-request.schema.json",
    "venture-launch-request.schema.json",
    "repair-operation.schema.json",
)
FORBIDDEN_TOOL_NAMES = frozenset({"shell", "browser", "file_read", "file_write", "exec", "web_search"})


@dataclass(frozen=True)
class ShadowDecision:
    decision_id: str
    model_family: str
    prompt_hash: str
    opportunity_id: str
    decision: dict[str, Any]
    would_call: dict[str, Any] | None
    executed: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_family": self.model_family,
            "ceo_prompt_hash": self.prompt_hash,
            "opportunity_id": self.opportunity_id,
            "decision": self.decision,
            "would_call": self.would_call,
            "executed": self.executed,
            "side_effect": False,
        }


class CEOAgent:
    def __init__(self, model: Callable[[dict[str, Any], tuple[str, ...]], dict[str, Any]], prompt: str, log_path: str | Path):
        self.model = model
        self.prompt = prompt
        self.prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        self.log_path = Path(log_path)
        self.model_family = getattr(model, "model_family", "unknown")
        self.tool_schemas = CEO_TOOL_SCHEMAS
        if any(name in FORBIDDEN_TOOL_NAMES for name in self.tool_schemas):
            raise ValueError("generic framework tool leaked into CEO tool list")

    def inspect_tools(self) -> tuple[str, ...]:
        return self.tool_schemas

    def shadow_decide(self, opportunity: dict[str, Any]) -> ShadowDecision:
        response = self.model({"system": self.prompt, "opportunity": opportunity}, self.tool_schemas)
        would_call = response.get("tool_call")
        if would_call and would_call.get("schema") not in self.tool_schemas:
            raise ValueError("CEO proposed a non-broker tool")
        decision = ShadowDecision(
            decision_id=hashlib.sha256(json.dumps(opportunity, sort_keys=True).encode()).hexdigest()[:16],
            model_family=self.model_family,
            prompt_hash=self.prompt_hash,
            opportunity_id=str(opportunity["opportunity_id"]),
            decision=response.get("decision", {}),
            would_call=would_call,
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(decision.to_record(), sort_keys=True) + chr(10))
        return decision

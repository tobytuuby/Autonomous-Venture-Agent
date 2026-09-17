"""Portfolio CEO shadow-mode runtime with broker-only tool vocabulary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .durable_state import DurableDecisionStore, configuration_fingerprint

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

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ShadowDecision":
        return cls(
            decision_id=str(record["decision_id"]),
            model_family=str(record["model_family"]),
            prompt_hash=str(record["ceo_prompt_hash"]),
            opportunity_id=str(record["opportunity_id"]),
            decision=dict(record.get("decision") or {}),
            would_call=record.get("would_call"),
            executed=bool(record.get("executed", False)),
        )


class CEOAgent:
    def __init__(
        self,
        model: Callable[[dict[str, Any], tuple[str, ...]], dict[str, Any]],
        prompt: str,
        log_path: str | Path,
        *,
        durable_store: DurableDecisionStore | None = None,
        policy_versions: tuple[str, ...] = ("v11", "v3.2", "p1.0"),
        runner_version: str = "p1-shadow-runner-v1",
        runtime_version: str = "python",
    ):
        self.model = model
        self.prompt = prompt
        self.prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        self.log_path = Path(log_path)
        self.model_family = getattr(model, "model_family", "unknown")
        self.tool_schemas = CEO_TOOL_SCHEMAS
        self.durable_store = durable_store
        endpoint_origin = getattr(model, "endpoint", "offline://synthetic-shadow")
        model_name = getattr(model, "model", self.model_family)
        self.configuration_fingerprint = configuration_fingerprint(
            endpoint_origin=endpoint_origin,
            model_name=model_name,
            prompt_hash=self.prompt_hash,
            tool_list=self.tool_schemas,
            policy_versions=policy_versions,
            runner_version=runner_version,
            runtime_version=runtime_version,
        )
        if any(name in FORBIDDEN_TOOL_NAMES for name in self.tool_schemas):
            raise ValueError("generic framework tool leaked into CEO tool list")

    def inspect_tools(self) -> tuple[str, ...]:
        return self.tool_schemas

    def shadow_decide(self, opportunity: dict[str, Any]) -> ShadowDecision:
        decision_id = hashlib.sha256(json.dumps(opportunity, sort_keys=True).encode()).hexdigest()[:16]
        if self.durable_store is not None:
            existing = self.durable_store.start(
                decision_id,
                str(opportunity["adversarial_id"] if "adversarial_id" in opportunity else opportunity["opportunity_id"]),
                self.configuration_fingerprint,
            )
            if existing["state"] == "completed" and existing.get("response_json"):
                return ShadowDecision.from_record(existing["response"])
            if existing["state"] == "dispatched":
                existing = self.durable_store.recover(decision_id)
            if existing["state"] in {"received", "replayable"}:
                self.durable_store.transition(decision_id, "dispatched")

        response = self.model({"system": self.prompt, "opportunity": opportunity}, self.tool_schemas)
        would_call = response.get("tool_call")
        if would_call and would_call.get("schema") not in self.tool_schemas:
            if self.durable_store is not None:
                self.durable_store.transition(decision_id, "quarantined", detail="non-broker tool proposed")
            raise ValueError("CEO proposed a non-broker tool")
        decision = ShadowDecision(
            decision_id=decision_id,
            model_family=self.model_family,
            prompt_hash=self.prompt_hash,
            opportunity_id=str(opportunity["opportunity_id"]),
            decision=response.get("decision", {}),
            would_call=would_call,
        )
        record = decision.to_record()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + chr(10))
        if self.durable_store is not None:
            self.durable_store.record_response(decision_id, record)
            self.durable_store.transition(decision_id, "completed")
        return decision

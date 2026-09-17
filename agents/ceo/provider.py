"""Provider adapter for CEO shadow mode; never exposes provider tools to the model."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any


class ModelProviderError(RuntimeError):
    pass


SCHEMA_TO_TOOL_NAME = {
    "capability-request.schema.json": "capability_request",
    "capital-allocation-request.schema.json": "capital_allocation_request",
    "venture-launch-request.schema.json": "venture_launch_request",
    "repair-operation.schema.json": "repair_operation",
}
TOOL_NAME_TO_SCHEMA = {value: key for key, value in SCHEMA_TO_TOOL_NAME.items()}


class OpenAICompatibleShadowModel:
    model_family = "openai-compatible"

    def __init__(self, endpoint: str, model: str, token: str, timeout: float = 30.0, trace_path: str | Path | None = None):
        if not endpoint or not model or not token:
            raise ModelProviderError("real model endpoint, model, and token are required")
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.token = token
        self.timeout = timeout
        self.trace_path = Path(trace_path) if trace_path else None

    def _record_trace(self, record: dict[str, Any]) -> None:
        if self.trace_path is None:
            return
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + chr(10))

    def __call__(self, request: dict[str, Any], tool_schemas: tuple[str, ...]) -> dict[str, Any]:
        unknown_schemas = set(tool_schemas) - set(SCHEMA_TO_TOOL_NAME)
        if unknown_schemas:
            raise ModelProviderError("unknown CEO tool schema: " + ",".join(sorted(unknown_schemas)))
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request["system"]},
                {"role": "user", "content": json.dumps(request["opportunity"], sort_keys=True)},
            ],
            "reasoning_effort": "none",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": SCHEMA_TO_TOOL_NAME[schema],
                        "parameters": {"type": "object"},
                    },
                }
                for schema in tool_schemas
            ],
            "tool_choice": "auto",
        }
        request_bytes = json.dumps(body, sort_keys=True).encode()
        req = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=request_bytes,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_bytes = response.read()
                result = json.loads(response_bytes)
        except Exception as exc:  # pragma: no cover - provider-specific integration
            self._record_trace({
                "status": "FAIL",
                "scenario_id": request.get("opportunity", {}).get("adversarial_id"),
                "model": self.model,
                "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                "error_type": type(exc).__name__,
            })
            raise ModelProviderError("model provider request failed") from exc
        self._record_trace({
            "status": "PASS",
            "scenario_id": request.get("opportunity", {}).get("adversarial_id"),
            "model": self.model,
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
            "provider_response_id": result.get("id"),
            "provider_model": result.get("model"),
            "finish_reason": ((result.get("choices") or [{}])[0]).get("finish_reason"),
        })
        choice = (result.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_call = None
        calls = message.get("tool_calls") or []
        if calls:
            function = calls[0].get("function") or {}
            schema = TOOL_NAME_TO_SCHEMA.get(function.get("name"))
            if schema is None:
                raise ModelProviderError("model proposed an unknown CEO tool")
            arguments = function.get("arguments", "{}")
            try:
                arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
            except json.JSONDecodeError as exc:
                raise ModelProviderError("model returned invalid tool arguments") from exc
            tool_call = {"schema": schema, "arguments": arguments}
        return {"decision": {"content": message.get("content", "")}, "tool_call": tool_call}


def api_tool_name(schema: str) -> str:
    return SCHEMA_TO_TOOL_NAME[schema]


def is_valid_api_tool_name(name: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_-]+", name) is not None

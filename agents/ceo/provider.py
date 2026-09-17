"""Provider adapter for CEO shadow mode; never exposes provider tools to the model."""

from __future__ import annotations

import json
import re
import urllib.request
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

    def __init__(self, endpoint: str, model: str, token: str, timeout: float = 30.0):
        if not endpoint or not model or not token:
            raise ModelProviderError("real model endpoint, model, and token are required")
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.token = token
        self.timeout = timeout

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
        req = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read())
        except Exception as exc:  # pragma: no cover - provider-specific integration
            raise ModelProviderError("model provider request failed") from exc
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

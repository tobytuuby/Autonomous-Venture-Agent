"""Provider adapter for CEO shadow mode; never exposes provider tools to the model."""

from __future__ import annotations

import json
import urllib.request
from typing import Any


class ModelProviderError(RuntimeError):
    pass


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
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request["system"]},
                {"role": "user", "content": json.dumps(request["opportunity"], sort_keys=True)},
            ],
            "tools": [{"type": "function", "function": {"name": schema, "parameters": {"type": "object"}}} for schema in tool_schemas],
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
        return {"decision": {"content": message.get("content", "")}, "tool_call": None}

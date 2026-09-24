"""P8.1 synthetic controlled-action denial boundary.

This module records only deterministic synthetic denials. It has no executor,
provider, credential, network, process, or external-I/O capability.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical


class P81Denied(ValueError):
    """Raised when a P8.1 request or execution attempt is denied."""


class SyntheticP81ActionGate:
    """Fail-closed, non-executing boundary for P8.1 action requests."""

    REQUIRED = {
        "request_id",
        "venture_id",
        "authority_class",
        "charter_hash",
        "execution_class",
        "synthetic_only",
        "effect",
        "written_live_action_approval",
    }
    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"

    def __init__(self, *, policy_version: str, configuration_fingerprint: str):
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise P81Denied("policy_version is required")
        if not isinstance(configuration_fingerprint, str) or len(configuration_fingerprint) != 64:
            raise P81Denied("configuration_fingerprint must be a SHA-256 digest")
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self._requests: dict[str, tuple[str, dict[str, Any]]] = {}
        self._stopped = False

    @staticmethod
    def _text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise P81Denied(f"{field} must be non-empty")
        return value

    def _validate(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P81Denied("P8.1 gate is stopped and fail-closed")
        if not isinstance(request, Mapping) or not self.REQUIRED.issubset(request):
            missing = sorted(self.REQUIRED.difference(request if isinstance(request, Mapping) else set()))
            raise P81Denied(f"request is incomplete: {missing}")
        if request["execution_class"] != self.EXECUTION_CLASS:
            raise P81Denied("execution class must remain synthetic-shadow-isolated-pre-production")
        if request["synthetic_only"] is not True or request["effect"] != "none":
            raise P81Denied("P8.1 requests must be synthetic-only and effect-free")
        if any(bool(request.get(field)) for field in LIVE_FIELDS):
            raise P81Denied("all nine live authorities must remain false")
        if request.get("live_mode") is True or request.get("live_credential") is True:
            raise P81Denied("live mode and live credentials are denied")
        if request.get("credential_mode") not in (None, "synthetic"):
            raise P81Denied("credential mode must be synthetic or absent")
        if request.get("model_output") or request.get("approval_source") == "model":
            raise P81Denied("model output cannot authorize P8.1")
        approval = request["written_live_action_approval"]
        if not isinstance(approval, Mapping) or approval.get("status") != "PENDING":
            raise P81Denied("written live-action approval must remain pending")
        request_id = self._text(request["request_id"], "request_id")
        venture_id = self._text(request["venture_id"], "venture_id")
        authority_class = self._text(request["authority_class"], "authority_class")
        charter_hash = self._text(request["charter_hash"], "charter_hash")
        if len(charter_hash) != 64 or any(c not in "0123456789abcdef" for c in charter_hash):
            raise P81Denied("charter_hash must be a SHA-256 digest")
        material = {
            "request_id": request_id,
            "venture_id": venture_id,
            "authority_class": authority_class,
            "charter_hash": charter_hash,
            "execution_class": self.EXECUTION_CLASS,
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
        }
        return {"request_id": request_id, "material": material}

    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        validated = self._validate(request)
        request_id = validated["request_id"]
        material = validated["material"]
        request_hash = hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()
        prior = self._requests.get(request_id)
        if prior is not None:
            if prior[0] != request_hash:
                raise P81Denied("request identity collision")
            return json.loads(json.dumps(prior[1], sort_keys=True))
        result = {
            **material,
            "request_hash": request_hash,
            "status": "DENIED",
            "reason": "P8.1 synthetic boundary does not execute live action",
            "synthetic_only": True,
            "effect": "none",
            "live_action_permitted": False,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "authority_flags": {field: False for field in LIVE_FIELDS},
        }
        self._requests[request_id] = (request_hash, result)
        return json.loads(json.dumps(result, sort_keys=True))

    def execute(self, *_: Any, **__: Any) -> None:
        raise P81Denied("P8.1 execution is not enabled in the synthetic boundary")

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        reason = self._text(reason, "stop reason")
        self._stopped = True
        return {
            "status": "STOPPED",
            "reason": reason,
            "synthetic_only": True,
            "effect": "none",
            "live_action_permitted": False,
            "authority_flags": {field: False for field in LIVE_FIELDS},
        }

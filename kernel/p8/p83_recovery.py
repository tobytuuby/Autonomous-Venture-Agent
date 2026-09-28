"""P8.3 synthetic recovery and wind-down boundary."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical
from kernel.p8.charter_registry import SyntheticCharterRegistry


class P83Denied(ValueError):
    """Raised when a recovery request cannot be evaluated safely."""


class SyntheticP83Recovery:
    """In-memory recovery recorder with no live execution capability."""

    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"
    CONTROLS = ("freeze", "revoke", "quarantine", "restore", "rollback", "wind-down")
    TERMINAL_STATES = {"REVOKED", "WOUND_DOWN"}
    REQUIRED = {
        "recovery_id", "venture_id", "authority_class", "charter_hash",
        "execution_class", "synthetic_only", "effect", "requested_control",
        "current_state", "reason", "model_output_authorization",
        "external_action", "unauthorized_action", "live_credential",
        *LIVE_FIELDS,
    }

    def __init__(self, *, policy_version: str, configuration_fingerprint: str,
                 charter_registry: SyntheticCharterRegistry) -> None:
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise P83Denied("policy_version is required")
        if not isinstance(configuration_fingerprint, str) or len(configuration_fingerprint) != 64:
            raise P83Denied("configuration_fingerprint must be a SHA-256 digest")
        if not isinstance(charter_registry, SyntheticCharterRegistry):
            raise P83Denied("approved charter registry is required")
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.charter_registry = charter_registry
        self._requests: dict[str, tuple[str, dict[str, Any]]] = {}
        self._state = "ACTIVE"
        self._stopped = False

    @staticmethod
    def _text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise P83Denied(f"{field} must be non-empty")
        return value

    def _validate(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P83Denied("P8.3 recovery boundary is stopped and fail-closed")
        if not isinstance(request, Mapping) or not self.REQUIRED.issubset(request):
            missing = sorted(self.REQUIRED.difference(request if isinstance(request, Mapping) else set()))
            raise P83Denied(f"recovery request is incomplete: {missing}")
        recovery_id = self._text(request["recovery_id"], "recovery_id")
        venture_id = self._text(request["venture_id"], "venture_id")
        authority_class = self._text(request["authority_class"], "authority_class")
        charter_hash = self._text(request["charter_hash"], "charter_hash")
        if len(charter_hash) != 64 or any(c not in "0123456789abcdef" for c in charter_hash):
            raise P83Denied("charter_hash must be a SHA-256 digest")
        charter = self.charter_registry.resolve(charter_hash)
        if charter is None:
            raise P83Denied("charter_hash is not an approved P8.0 preflight record")
        if charter["venture_id"] != venture_id or charter["authority_class"] != authority_class:
            raise P83Denied("recovery scope does not match approved charter")
        if request["execution_class"] != self.EXECUTION_CLASS:
            raise P83Denied("execution class must remain synthetic")
        if request["synthetic_only"] is not True or request["effect"] != "none":
            raise P83Denied("recovery must be synthetic and effect-free")
        if request["requested_control"] not in self.CONTROLS:
            raise P83Denied("unknown recovery control")
        if not isinstance(request["current_state"], str) or not request["current_state"].strip():
            raise P83Denied("current_state must be non-empty")
        self._text(request["reason"], "reason")
        return {
            "recovery_id": recovery_id, "venture_id": venture_id,
            "authority_class": authority_class, "charter_hash": charter_hash,
            "requested_control": request["requested_control"],
            "current_state": request["current_state"],
            "model_output_authorization": request["model_output_authorization"],
            "external_action": request["external_action"],
            "unauthorized_action": request["unauthorized_action"],
            "live_credential": request["live_credential"],
            "authority_flags": {field: request[field] for field in LIVE_FIELDS},
            "failure_injection": bool(request.get("failure_injection", False)),
            "reason": request["reason"],
        }

    def recover(self, request: Mapping[str, Any]) -> dict[str, Any]:
        validated = self._validate(request)
        recovery_id = validated["recovery_id"]
        material = {**validated, "policy_version": self.policy_version,
                    "configuration_fingerprint": self.configuration_fingerprint}
        request_hash = hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()
        prior = self._requests.get(recovery_id)
        if prior is not None:
            if prior[0] != request_hash:
                raise P83Denied("recovery identity collision")
            return json.loads(json.dumps(prior[1], sort_keys=True))

        reasons: list[str] = []
        control = validated["requested_control"]
        current_state = validated["current_state"]
        if any(bool(validated["authority_flags"][field]) for field in LIVE_FIELDS):
            reasons.append("LIVE_AUTHORITY_DRIFT")
        if validated["model_output_authorization"] is not False:
            reasons.append("MODEL_AUTHORIZATION_DRIFT")
        if validated["external_action"] is not False:
            reasons.append("EXTERNAL_ACTION_DRIFT")
        if validated["unauthorized_action"] is not False:
            reasons.append("UNAUTHORIZED_ACTION_DRIFT")
        if validated["live_credential"] is not False:
            reasons.append("LIVE_CREDENTIAL_DRIFT")

        if validated["failure_injection"]:
            reasons.append("INJECTED_FAILURE")
            disposition, next_state = "TERMINAL_FAIL_CLOSED", "QUARANTINED"
            self._stopped, self._state = True, next_state
        elif control in {"restore", "rollback"}:
            reasons.append("AUTHORITY_WIDENING_CONTROL_DENIED")
            disposition, next_state = "DENIED", current_state
        elif current_state in self.TERMINAL_STATES:
            reasons.append("TERMINAL_STATE")
            disposition, next_state = "DENIED", current_state
        else:
            next_state = {"freeze": "FROZEN", "revoke": "REVOKED",
                          "quarantine": "QUARANTINED", "wind-down": "WOUND_DOWN"}.get(control, current_state)
            disposition = "CONTAINED"

        result = {
            "recovery_id": recovery_id, "venture_id": validated["venture_id"],
            "authority_class": validated["authority_class"], "charter_hash": validated["charter_hash"],
            "requested_control": control, "prior_state": current_state,
            "resulting_state": next_state, "disposition": disposition,
            "reasons": reasons, "stop_required": bool(reasons),
            "execution_class": self.EXECUTION_CLASS, "synthetic_only": True, "effect": "none",
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "model_output_authorization": False, "external_action": False,
            "unauthorized_action": False, "live_credential": False,
            "execution_performed": False, "request_hash": request_hash,
        }
        self._requests[recovery_id] = (request_hash, result)
        if disposition == "CONTAINED":
            self._state = next_state
        return json.loads(json.dumps(result, sort_keys=True))

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        reason = self._text(reason, "stop reason")
        self._stopped, self._state = True, "STOPPED"
        return {
            "status": "STOPPED", "reason": reason, "disposition": "TERMINAL_FAIL_CLOSED",
            "stop_required": True, "execution_class": self.EXECUTION_CLASS,
            "synthetic_only": True, "effect": "none",
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "model_output_authorization": False, "external_action": False,
            "unauthorized_action": False, "live_credential": False,
            "execution_performed": False,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "state": self._state, "requests": len(self._requests),
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "model_output_authorization": False, "external_action": False,
            "unauthorized_action": False, "live_credential": False,
            "execution_performed": False,
        }

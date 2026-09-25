"""P8.2 synthetic observation and reconciliation boundary."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical
from kernel.p8.charter_registry import SyntheticCharterRegistry


class P82Denied(ValueError):
    """Raised when a P8.2 observation cannot be safely evaluated."""


class SyntheticP82Monitor:
    """In-memory, fail-closed monitor with no external observation capability."""

    REQUIRED = {
        "event_id", "venture_id", "authority_class", "charter_hash",
        "execution_class", "synthetic_only", "effect", "status",
        "exposure", "loss", "exposure_ceiling", "loss_ceiling",
        "live_action_permitted", "external_action", "unauthorized_action",
        "live_credential", "model_output_authorization",
    }
    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"

    def __init__(
        self,
        *,
        policy_version: str,
        configuration_fingerprint: str,
        charter_registry: SyntheticCharterRegistry,
    ):
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise P82Denied("policy_version is required")
        if not isinstance(configuration_fingerprint, str) or len(configuration_fingerprint) != 64:
            raise P82Denied("configuration_fingerprint must be a SHA-256 digest")
        if not isinstance(charter_registry, SyntheticCharterRegistry):
            raise P82Denied("approved charter registry is required")
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.charter_registry = charter_registry
        self._events: dict[str, tuple[str, dict[str, Any]]] = {}
        self._state = "HEALTHY"
        self._stopped = False

    @staticmethod
    def _text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise P82Denied(f"{field} must be non-empty")
        return value

    @staticmethod
    def _number(value: Any, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise P82Denied(f"{field} must be numeric")
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise P82Denied(f"{field} must be finite and non-negative")
        return number

    def _validate(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P82Denied("P8.2 monitor is stopped and fail-closed")
        if not isinstance(observation, Mapping) or not self.REQUIRED.issubset(observation):
            missing = sorted(self.REQUIRED.difference(observation if isinstance(observation, Mapping) else set()))
            raise P82Denied(f"observation is incomplete: {missing}")
        event_id = self._text(observation["event_id"], "event_id")
        venture_id = self._text(observation["venture_id"], "venture_id")
        authority_class = self._text(observation["authority_class"], "authority_class")
        charter_hash = self._text(observation["charter_hash"], "charter_hash")
        if len(charter_hash) != 64 or any(c not in "0123456789abcdef" for c in charter_hash):
            raise P82Denied("charter_hash must be a SHA-256 digest")
        charter = self.charter_registry.resolve(charter_hash)
        if charter is None:
            raise P82Denied("charter_hash is not an approved P8.0 preflight record")
        if charter["venture_id"] != venture_id or charter["authority_class"] != authority_class:
            raise P82Denied("observation scope does not match approved charter")
        if observation["status"] not in {"DENIED", "STOPPED"}:
            raise P82Denied("observation status must be DENIED or STOPPED")
        material = {
            "event_id": event_id,
            "venture_id": venture_id,
            "authority_class": authority_class,
            "charter_hash": charter_hash,
            "execution_class": observation["execution_class"],
            "synthetic_only": observation["synthetic_only"],
            "effect": observation["effect"],
            "status": observation["status"],
            "exposure": self._number(observation["exposure"], "exposure"),
            "loss": self._number(observation["loss"], "loss"),
            "exposure_ceiling": self._number(observation["exposure_ceiling"], "exposure_ceiling"),
            "loss_ceiling": self._number(observation["loss_ceiling"], "loss_ceiling"),
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
        }
        return {"event_id": event_id, "material": material}

    def observe(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        validated = self._validate(observation)
        event_id = validated["event_id"]
        material = validated["material"]
        event_hash = hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()
        prior = self._events.get(event_id)
        if prior is not None:
            if prior[0] != event_hash:
                raise P82Denied("event identity collision")
            return json.loads(json.dumps(prior[1], sort_keys=True))

        reasons: list[str] = []
        if observation["execution_class"] != self.EXECUTION_CLASS:
            reasons.append("EXECUTION_CLASS_DRIFT")
        if observation["synthetic_only"] is not True:
            reasons.append("SYNTHETIC_ONLY_DRIFT")
        if observation["effect"] != "none":
            reasons.append("EFFECT_DRIFT")
        if any(bool(observation.get(field)) for field in LIVE_FIELDS):
            reasons.append("LIVE_AUTHORITY_DRIFT")
        if observation["live_action_permitted"] is not False:
            reasons.append("LIVE_ACTION_DRIFT")
        if observation["external_action"] is not False:
            reasons.append("EXTERNAL_ACTION_DRIFT")
        if observation["unauthorized_action"] is not False:
            reasons.append("UNAUTHORIZED_ACTION_DRIFT")
        if observation["live_credential"] is not False:
            reasons.append("LIVE_CREDENTIAL_DRIFT")
        if observation["model_output_authorization"] is not False:
            reasons.append("MODEL_AUTHORIZATION_DRIFT")
        if material["loss"] > material["loss_ceiling"]:
            reasons.append("LOSS_CEILING_BREACH")
        if material["exposure"] > material["exposure_ceiling"]:
            reasons.append("EXPOSURE_CEILING_BREACH")
        if material["loss_ceiling"] > material["exposure_ceiling"]:
            reasons.append("CEILING_ORDER_DRIFT")

        disposition = "QUARANTINED" if reasons else "OBSERVED"
        if reasons:
            self._state = "QUARANTINED"
        result = {
            **material,
            "event_hash": event_hash,
            "disposition": disposition,
            "reasons": reasons,
            "stop_required": bool(reasons),
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
        }
        self._events[event_id] = (event_hash, result)
        return json.loads(json.dumps(result, sort_keys=True))

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        reason = self._text(reason, "stop reason")
        self._stopped = True
        self._state = "STOPPED"
        return {
            "status": "STOPPED",
            "reason": reason,
            "disposition": "QUARANTINED",
            "stop_required": True,
            "synthetic_only": True,
            "effect": "none",
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "observed": len(self._events),
            "quarantined": sum(1 for _, result in self._events.values() if result["disposition"] == "QUARANTINED"),
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "live_action_permitted": False,
        }

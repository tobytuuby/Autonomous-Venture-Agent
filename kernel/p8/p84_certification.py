"""P8.4 synthetic pilot certification and closeout boundary."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical
from kernel.p8.charter_registry import SyntheticCharterRegistry


class P84Denied(ValueError):
    """Raised when a certification packet cannot be safely evaluated."""


class SyntheticP84Certification:
    """In-memory certification of synthetic P8 evidence; never grants live authority."""

    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"
    SCOPE = "synthetic-pilot-closeout"
    EXPECTED_PHASES = {
        "p8_0": {"focused": 13, "regression": 407},
        "p8_1": {"focused": 11, "regression": 418},
        "p8_2": {"focused": 10, "regression": 428},
        "p8_3": {"focused": 12, "regression": 440},
    }
    REQUIRED = {
        "certification_id", "venture_id", "authority_class", "charter_hash",
        "execution_class", "synthetic_only", "effect", "evidence_hash",
        "phase_results", "live_action_permitted", "execution_performed",
        "external_action", "unauthorized_action", "live_credential",
        "model_output_authorization", "authority_flags",
        "reviewer_independent", "decision_source", "scope",
    }

    def __init__(self, *, policy_version: str, configuration_fingerprint: str,
                 charter_registry: SyntheticCharterRegistry) -> None:
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise P84Denied("policy_version is required")
        if not isinstance(configuration_fingerprint, str) or len(configuration_fingerprint) != 64:
            raise P84Denied("configuration_fingerprint must be a SHA-256 digest")
        if not isinstance(charter_registry, SyntheticCharterRegistry):
            raise P84Denied("approved charter registry is required")
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.charter_registry = charter_registry
        self._packets: dict[str, tuple[str, dict[str, Any]]] = {}
        self._stopped = False

    @staticmethod
    def _text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise P84Denied(f"{field} must be non-empty")
        return value

    @staticmethod
    def _digest(value: Any, field: str) -> str:
        value = SyntheticP84Certification._text(value, field)
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise P84Denied(f"{field} must be a SHA-256 digest")
        return value

    def _validate(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P84Denied("P8.4 certification boundary is stopped and fail-closed")
        if not isinstance(packet, Mapping) or not self.REQUIRED.issubset(packet):
            missing = sorted(self.REQUIRED.difference(packet if isinstance(packet, Mapping) else set()))
            raise P84Denied(f"certification packet is incomplete: {missing}")
        certification_id = self._text(packet["certification_id"], "certification_id")
        venture_id = self._text(packet["venture_id"], "venture_id")
        authority_class = self._text(packet["authority_class"], "authority_class")
        charter_hash = self._digest(packet["charter_hash"], "charter_hash")
        charter = self.charter_registry.resolve(charter_hash)
        if charter is None:
            raise P84Denied("charter_hash is not an approved P8.0 preflight record")
        if charter["venture_id"] != venture_id or charter["authority_class"] != authority_class:
            raise P84Denied("certification scope does not match approved charter")
        if packet["execution_class"] != self.EXECUTION_CLASS:
            raise P84Denied("execution class must remain synthetic")
        if packet["synthetic_only"] is not True or packet["effect"] != "none":
            raise P84Denied("certification must be synthetic and effect-free")
        if packet["scope"] != self.SCOPE:
            raise P84Denied("unsupported certification scope")
        if not isinstance(packet["phase_results"], Mapping):
            raise P84Denied("phase_results must be an object")
        flags = packet["authority_flags"]
        if flags != {field: False for field in LIVE_FIELDS}:
            raise P84Denied("all nine live authorities must be explicitly false")
        return {
            "certification_id": certification_id,
            "venture_id": venture_id,
            "authority_class": authority_class,
            "charter_hash": charter_hash,
            "evidence_hash": self._digest(packet["evidence_hash"], "evidence_hash"),
            "phase_results": dict(packet["phase_results"]),
            "live_action_permitted": packet["live_action_permitted"],
            "execution_performed": packet["execution_performed"],
            "external_action": packet["external_action"],
            "unauthorized_action": packet["unauthorized_action"],
            "live_credential": packet["live_credential"],
            "model_output_authorization": packet["model_output_authorization"],
            "reviewer_independent": packet["reviewer_independent"],
            "decision_source": packet["decision_source"],
            "scope": packet["scope"],
        }

    def certify(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        validated = self._validate(packet)
        certification_id = validated["certification_id"]
        material = {**validated, "policy_version": self.policy_version,
                    "configuration_fingerprint": self.configuration_fingerprint}
        packet_hash = hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()
        prior = self._packets.get(certification_id)
        if prior is not None:
            if prior[0] != packet_hash:
                raise P84Denied("certification identity collision")
            return json.loads(json.dumps(prior[1], sort_keys=True))

        reasons: list[str] = []
        for phase, expected in self.EXPECTED_PHASES.items():
            actual = validated["phase_results"].get(phase)
            if not isinstance(actual, Mapping):
                reasons.append(f"MISSING_{phase.upper()}_RESULT")
                continue
            if actual.get("focused") != expected["focused"]:
                reasons.append(f"{phase.upper()}_FOCUSED_COUNT_MISMATCH")
            if actual.get("regression") != expected["regression"]:
                reasons.append(f"{phase.upper()}_REGRESSION_COUNT_MISMATCH")
            if actual.get("status") != "PASS":
                reasons.append(f"{phase.upper()}_STATUS_NOT_PASS")
        if validated["live_action_permitted"] is not False:
            reasons.append("LIVE_ACTION_DRIFT")
        if validated["execution_performed"] is not False:
            reasons.append("EXECUTION_DRIFT")
        if validated["external_action"] is not False:
            reasons.append("EXTERNAL_ACTION_DRIFT")
        if validated["unauthorized_action"] is not False:
            reasons.append("UNAUTHORIZED_ACTION_DRIFT")
        if validated["live_credential"] is not False:
            reasons.append("LIVE_CREDENTIAL_DRIFT")
        if validated["model_output_authorization"] is not False:
            reasons.append("MODEL_AUTHORIZATION_DRIFT")
        if validated["reviewer_independent"] is not True:
            reasons.append("INDEPENDENT_REVIEW_DRIFT")
        if validated["decision_source"] != "human":
            reasons.append("NON_HUMAN_DECISION_SOURCE")

        disposition = "CERTIFIED_SYNTHETIC" if not reasons else "BLOCKED"
        result = {
            "certification_id": certification_id,
            "venture_id": validated["venture_id"],
            "authority_class": validated["authority_class"],
            "charter_hash": validated["charter_hash"],
            "packet_hash": packet_hash,
            "disposition": disposition,
            "reasons": reasons,
            "execution_class": self.EXECUTION_CLASS,
            "synthetic_only": True,
            "effect": "none",
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "live_action_permitted": False,
            "execution_performed": False,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "model_output_authorization": False,
            "p8_5_authorized": False,
            "stop_required": bool(reasons),
        }
        self._packets[certification_id] = (packet_hash, result)
        return json.loads(json.dumps(result, sort_keys=True))

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        reason = self._text(reason, "stop reason")
        self._stopped = True
        return {
            "status": "STOPPED",
            "reason": reason,
            "disposition": "TERMINAL_FAIL_CLOSED",
            "execution_class": self.EXECUTION_CLASS,
            "synthetic_only": True,
            "effect": "none",
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "live_action_permitted": False,
            "execution_performed": False,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "model_output_authorization": False,
            "p8_5_authorized": False,
        }

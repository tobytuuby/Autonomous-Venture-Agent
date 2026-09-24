"""P8.0 synthetic pilot-charter preflight gate.

This module validates a bounded pilot charter and records only a synthetic
preflight result. It never executes a pilot, handles credentials, or permits
live action.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical


class P8Denied(ValueError):
    """Raised when a P8 charter violates the synthetic preflight contract."""


class SyntheticPilotGate:
    """Fail-closed, effect-free validator for a P8 pilot charter."""

    REQUIRED = {
        "pilot_id",
        "venture_id",
        "authority_class",
        "operating_window",
        "exposure_ceiling",
        "loss_ceiling",
        "named_approvers",
        "monitoring_plan",
        "reconciliation_plan",
        "automatic_stop_conditions",
        "written_live_action_approval",
        "synthetic_only",
        "effect",
    }

    def __init__(self, *, policy_version: str, configuration_fingerprint: str):
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise P8Denied("policy_version is required")
        if (
            not isinstance(configuration_fingerprint, str)
            or len(configuration_fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in configuration_fingerprint)
        ):
            raise P8Denied("configuration_fingerprint must be a SHA-256 digest")
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self._charter_hash: str | None = None
        self._result: dict[str, Any] | None = None
        self._stopped = False

    @staticmethod
    def _require_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise P8Denied(f"{field} must be a non-empty string")
        return value

    @staticmethod
    def _require_number(value: Any, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise P8Denied(f"{field} must be numeric")
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise P8Denied(f"{field} must be finite and non-negative")
        return number

    @classmethod
    def _validate_window(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, Mapping):
            raise P8Denied("operating_window must be an object")
        start = cls._require_text(value.get("start"), "operating_window.start")
        end = cls._require_text(value.get("end"), "operating_window.end")
        timezone = cls._require_text(value.get("timezone"), "operating_window.timezone")
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError as exc:
            raise P8Denied("operating window timestamps must be ISO-8601") from exc
        if start_dt >= end_dt:
            raise P8Denied("operating window must have start before end")
        return {"start": start, "end": end, "timezone": timezone}

    @classmethod
    def _validate_list(cls, value: Any, field: str) -> list[str]:
        if not isinstance(value, list) or not value:
            raise P8Denied(f"{field} must be a non-empty list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise P8Denied(f"{field} must contain non-empty strings")
        return list(dict.fromkeys(value))

    def _validate_authorities(self, charter: Mapping[str, Any]) -> None:
        if charter.get("synthetic_only") is not True:
            raise P8Denied("P8 preflight must be synthetic-only")
        if charter.get("effect") != "none":
            raise P8Denied("P8 preflight effect must be none")
        if any(bool(charter.get(field)) for field in LIVE_FIELDS):
            raise P8Denied("all nine live authorities must remain false")
        if charter.get("live_credential") is True or charter.get("credential_mode") not in (None, "synthetic"):
            raise P8Denied("live credentials are denied during P8 preflight")
        if charter.get("model_output") or charter.get("approval_source") == "model":
            raise P8Denied("model output cannot authorize a P8 pilot")
        if charter.get("live_mode") is True:
            raise P8Denied("live_mode is denied during P8 preflight")
        approval = charter.get("written_live_action_approval")
        if not isinstance(approval, Mapping) or approval.get("status") != "PENDING":
            raise P8Denied("separate written live-action approval must remain pending")

    def validate_charter(self, charter: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P8Denied("P8 gate is stopped and fail-closed")
        if not isinstance(charter, Mapping) or not self.REQUIRED.issubset(charter):
            missing = sorted(self.REQUIRED.difference(charter if isinstance(charter, Mapping) else set()))
            raise P8Denied(f"charter is incomplete: {missing}")
        self._validate_authorities(charter)
        pilot_id = self._require_text(charter["pilot_id"], "pilot_id")
        venture_id = self._require_text(charter["venture_id"], "venture_id")
        authority_class = self._require_text(charter["authority_class"], "authority_class")
        if isinstance(charter.get("venture_ids"), list) and len(charter["venture_ids"]) != 1:
            raise P8Denied("exactly one venture is permitted")
        if isinstance(charter.get("authority_classes"), list) and len(charter["authority_classes"]) != 1:
            raise P8Denied("exactly one authority class is permitted")
        window = self._validate_window(charter["operating_window"])
        exposure = self._require_number(charter["exposure_ceiling"], "exposure_ceiling")
        loss = self._require_number(charter["loss_ceiling"], "loss_ceiling")
        if exposure <= 0:
            raise P8Denied("exposure_ceiling must be greater than zero")
        if loss > exposure:
            raise P8Denied("loss_ceiling cannot exceed exposure_ceiling")
        approvers = self._validate_list(charter["named_approvers"], "named_approvers")
        stops = self._validate_list(charter["automatic_stop_conditions"], "automatic_stop_conditions")
        monitoring = self._validate_list(charter["monitoring_plan"], "monitoring_plan")
        reconciliation = self._validate_list(charter["reconciliation_plan"], "reconciliation_plan")
        material = {
            "pilot_id": pilot_id,
            "venture_id": venture_id,
            "authority_class": authority_class,
            "operating_window": window,
            "exposure_ceiling": exposure,
            "loss_ceiling": loss,
            "named_approvers": approvers,
            "monitoring_plan": monitoring,
            "reconciliation_plan": reconciliation,
            "automatic_stop_conditions": stops,
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
        }
        charter_hash = hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()
        if self._charter_hash is not None and self._charter_hash != charter_hash:
            raise P8Denied("pilot charter identity collision")
        self._charter_hash = charter_hash
        self._result = {
            **material,
            "status": "PREFLIGHT_READY",
            "synthetic_only": True,
            "effect": "none",
            "live_action_permitted": False,
            "written_live_action_approval": {"status": "PENDING"},
            "authority_flags": {field: False for field in LIVE_FIELDS},
            "record_hash": charter_hash,
        }
        return json.loads(json.dumps(self._result, sort_keys=True))

    def request_live_action(self, *_: Any, **__: Any) -> None:
        """Always deny live action from the P8.0 preflight boundary."""
        raise P8Denied("P8.1 live action requires a separate written approval gate")

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        reason = self._require_text(reason, "stop reason")
        self._stopped = True
        result = {
            "status": "STOPPED",
            "reason": reason,
            "synthetic_only": True,
            "effect": "none",
            "live_action_permitted": False,
            "authority_flags": {field: False for field in LIVE_FIELDS},
        }
        self._result = result
        return json.loads(json.dumps(result, sort_keys=True))

    def snapshot(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "charter_hash": self._charter_hash,
            "stopped": self._stopped,
            "result": json.loads(json.dumps(self._result, sort_keys=True))
            if self._result is not None else None,
        }

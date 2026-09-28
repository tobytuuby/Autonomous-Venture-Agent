"""In-memory synthetic P9 boundary evaluator; no external effects are possible here."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from collections.abc import Mapping
from typing import Any

from kernel.p6.registry import LIVE_FIELDS


class P9Denied(ValueError):
    """Raised when a P9 synthetic record cannot be safely evaluated."""


class SyntheticP9Boundary:
    """Evaluate supplied synthetic records and recovery simulations in memory only."""

    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"
    ALLOWED_DIMENSIONS = frozenset({
        "numeric_limit", "operating_window", "fixture_venture_count", "concurrency",
    })
    ALLOWED_EVENT_TYPES = frozenset({"scope_change", "observation", "recovery"})
    RECOVERY_RESULTS = {
        "freeze": "FROZEN",
        "revoke": "REVOKED",
        "quarantine": "QUARANTINED",
        "wind-down": "WOUND_DOWN",
    }
    TERMINAL_STATES = frozenset({"REVOKED", "WOUND_DOWN"})
    STATES = frozenset({"ACTIVE", "FROZEN", "REVOKED", "QUARANTINED", "WOUND_DOWN"})
    REQUIRED = frozenset({
        "event_id", "sequence", "event_type", "venture_id", "portfolio_id",
        "charter_hash", "execution_class", "synthetic_only", "effect",
        "scope_dimension", "changed_dimensions", "before_value", "after_value",
        "requested_control", "current_state", "failure_injection", "evidence_hash",
        "model_output_authorization", "execution_performed", "live_action_permitted",
        "external_action", "unauthorized_action", "live_credential", "provider_call",
        "network_call", *LIVE_FIELDS,
    })
    HEX64 = re.compile(r"^[0-9a-f]{64}$")

    def __init__(
        self,
        *,
        policy_version: str,
        configuration_fingerprint: str,
        charter_registry: Mapping[str, Mapping[str, str]],
    ) -> None:
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise P9Denied("policy_version is required")
        if not isinstance(configuration_fingerprint, str) or not self.HEX64.fullmatch(configuration_fingerprint):
            raise P9Denied("configuration_fingerprint must be a SHA-256 digest")
        if not isinstance(charter_registry, Mapping) or not charter_registry:
            raise P9Denied("an in-memory approved charter registry is required")
        normalized: dict[str, dict[str, str]] = {}
        for charter_hash, binding in charter_registry.items():
            if not isinstance(charter_hash, str) or not self.HEX64.fullmatch(charter_hash):
                raise P9Denied("charter registry keys must be SHA-256 digests")
            if not isinstance(binding, Mapping):
                raise P9Denied("charter binding must be an object")
            venture_id, portfolio_id = binding.get("venture_id"), binding.get("portfolio_id")
            if not self._text(venture_id) or not self._text(portfolio_id):
                raise P9Denied("charter binding requires venture and portfolio identity")
            normalized[charter_hash] = {"venture_id": venture_id, "portfolio_id": portfolio_id}
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.charter_registry = normalized
        self._events: dict[str, tuple[str, dict[str, Any]]] = {}
        self._last_sequence: dict[tuple[str, str, str], int] = {}
        self._stopped = False

    @staticmethod
    def _text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _valid_window(value: Any) -> bool:
        if not isinstance(value, Mapping) or not all(key in value for key in ("start", "end", "timezone")):
            return False
        if not isinstance(value["start"], str) or not isinstance(value["end"], str) or not SyntheticP9Boundary._text(value["timezone"]):
            return False
        try:
            start = datetime.fromisoformat(value["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(value["end"].replace("Z", "+00:00"))
        except ValueError:
            return False
        return start.tzinfo is not None and end.tzinfo is not None and end > start

    @staticmethod
    def _canonical(value: Any) -> str:
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise P9Denied("record must contain finite JSON-compatible values") from exc

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _safe_result(self, record: Mapping[str, Any], disposition: str, reason: str = "") -> dict[str, Any]:
        result = {
            "event_id": record.get("event_id", ""),
            "venture_id": record.get("venture_id", ""),
            "portfolio_id": record.get("portfolio_id", ""),
            "charter_hash": record.get("charter_hash", ""),
            "sequence": record.get("sequence", 0),
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "execution_class": self.EXECUTION_CLASS,
            "synthetic_only": True,
            "effect": "none",
            "disposition": disposition,
            "reason": reason,
            "execution_performed": False,
            "live_action_permitted": False,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "provider_call": False,
            "network_call": False,
            "model_output_authorization": False,
            "authority_flags": {field: False for field in LIVE_FIELDS},
            **{field: False for field in LIVE_FIELDS},
        }
        return result

    def _quarantine(self, record: Mapping[str, Any], reason: str, *, stop: bool = True) -> dict[str, Any]:
        if stop:
            self._stopped = True
        result = self._safe_result(record, "QUARANTINED", reason)
        result["stop_required"] = True
        return result

    def evaluate(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P9Denied("P9 boundary is stopped and fail-closed")
        if not isinstance(record, Mapping):
            raise P9Denied("record must be an object")
        missing = self.REQUIRED.difference(record)
        if missing:
            raise P9Denied(f"record is missing required fields: {sorted(missing)}")
        unexpected = set(record).difference(self.REQUIRED | {"model_output"})
        if unexpected:
            raise P9Denied(f"record contains unsupported fields: {sorted(unexpected)}")
        if not self._text(record["event_id"]) or not self._text(record["venture_id"]) or not self._text(record["portfolio_id"]):
            raise P9Denied("event and scope identities must be non-empty strings")
        if type(record["sequence"]) is not int or record["sequence"] < 1:
            raise P9Denied("sequence must be a positive integer")
        if record["execution_class"] != self.EXECUTION_CLASS or record["synthetic_only"] is not True or record["effect"] != "none":
            return self._quarantine(record, "EXECUTION_MODE_OR_EFFECT_DRIFT")

        charter_hash = record["charter_hash"]
        if not isinstance(charter_hash, str) or not self.HEX64.fullmatch(charter_hash):
            raise P9Denied("charter_hash must be a SHA-256 digest")
        binding = self.charter_registry.get(charter_hash)
        if binding is None:
            raise P9Denied("charter hash is not in the approved in-memory registry")
        if binding["venture_id"] != record["venture_id"] or binding["portfolio_id"] != record["portfolio_id"]:
            raise P9Denied("record scope does not match its approved charter binding")

        authority_drift = [field for field in LIVE_FIELDS if record[field] is not False]
        other_drift = [field for field in (
            "execution_performed", "live_action_permitted", "external_action",
            "unauthorized_action", "live_credential", "provider_call", "network_call",
            "model_output_authorization",
        ) if record[field] is not False]
        if authority_drift or other_drift:
            names = authority_drift + other_drift
            return self._quarantine(record, "DENIED_FIELDS=" + ",".join(names))

        event_type = record["event_type"]
        if event_type not in self.ALLOWED_EVENT_TYPES:
            raise P9Denied("unsupported event_type")
        dimension = record["scope_dimension"]
        changed = record["changed_dimensions"]
        if not isinstance(changed, list):
            raise P9Denied("changed_dimensions must be an array")
        if event_type == "scope_change":
            if dimension not in self.ALLOWED_DIMENSIONS or changed != [dimension]:
                return self._quarantine(record, "SCOPE_DIMENSION_NOT_ALLOWED_OR_NOT_SINGLE")
            before, after = record["before_value"], record["after_value"]
            if self._canonical(before) == self._canonical(after):
                return self._quarantine(record, "SCOPE_CHANGE_HAS_NO_MATERIAL_DELTA")
            if dimension == "numeric_limit":
                for value in (before, after):
                    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                        return self._quarantine(record, "SCOPE_VALUE_OUT_OF_BOUNDS")
            elif dimension in {"fixture_venture_count", "concurrency"}:
                for value in (before, after):
                    if type(value) is not int or value < 0:
                        return self._quarantine(record, "SCOPE_VALUE_OUT_OF_BOUNDS")
            elif dimension == "operating_window":
                if not self._valid_window(before) or not self._valid_window(after):
                    return self._quarantine(record, "OPERATING_WINDOW_INVALID")
        elif changed:
            return self._quarantine(record, "NON_SCOPE_EVENT_HAS_CHANGED_DIMENSIONS")

        if type(record["failure_injection"]) is not bool:
            raise P9Denied("failure_injection must be boolean")

        # Validate content integrity before any recovery disposition or replay result.
        material = dict(record)
        material.pop("evidence_hash", None)
        expected_evidence_hash = self._hash(self._canonical(material))
        if not isinstance(record["evidence_hash"], str) or not self.HEX64.fullmatch(record["evidence_hash"]):
            self._stopped = True
            raise P9Denied("evidence_hash must be a SHA-256 digest")
        if record["evidence_hash"] != expected_evidence_hash:
            self._stopped = True
            raise P9Denied("evidence hash mismatch")
        record_hash = self._hash(self._canonical(record))

        if record["failure_injection"]:
            self._stopped = True
            failed = self._safe_result(record, "TERMINAL_FAIL_CLOSED", "INJECTED_FAILURE")
            failed["stop_required"] = True
            return failed

        if event_type == "recovery":
            recovery_result = self._recovery_result(record)
            if recovery_result is not None:
                return recovery_result

        prior = self._events.get(record["event_id"])
        if prior is not None:
            if prior[0] != record_hash:
                self._stopped = True
                raise P9Denied("event identity collision; boundary stopped")
            return dict(prior[1])

        scope = (charter_hash, record["portfolio_id"], record["venture_id"])
        expected_sequence = self._last_sequence.get(scope, 0) + 1
        if record["sequence"] != expected_sequence:
            self._stopped = True
            stopped = self._safe_result(record, "TERMINAL_FAIL_CLOSED", "SEQUENCE_VIOLATION")
            stopped["stop_required"] = True
            return stopped

        disposition = "OBSERVED" if event_type == "observation" else "SIMULATED"
        result = self._safe_result(record, disposition)
        result.update({
            "record_hash": record_hash,
            "evidence_hash": record["evidence_hash"],
            "scope_dimension": dimension,
            "resulting_state": self._recovery_state(record) if event_type == "recovery" else "UNCHANGED",
            "model_output_ignored": "model_output" in record,
            "stop_required": False,
        })
        self._last_sequence[scope] = record["sequence"]
        self._events[record["event_id"]] = (record_hash, dict(result))
        return dict(result)

    def _recovery_result(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        control = record["requested_control"]
        state = record["current_state"]
        if control not in {*self.RECOVERY_RESULTS, "restore", "rollback", "none"}:
            raise P9Denied("unsupported recovery control")
        if state not in self.STATES:
            raise P9Denied("unsupported recovery state")
        if control in {"restore", "rollback"}:
            return self._quarantine(record, "AUTHORITY_WIDENING_RECOVERY_DENIED")
        if state in self.TERMINAL_STATES and control not in {"none"}:
            return self._quarantine(record, "TERMINAL_STATE_CANNOT_REOPEN")
        return None

    def _recovery_state(self, record: Mapping[str, Any]) -> str:
        control = record["requested_control"]
        return self.RECOVERY_RESULTS.get(control, record["current_state"])

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        if not self._text(reason):
            raise P9Denied("stop reason is required")
        self._stopped = True
        result = self._safe_result({}, "STOPPED", reason)
        result["stop_required"] = True
        return result

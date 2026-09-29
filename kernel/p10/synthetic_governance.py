"""In-memory synthetic governance rehearsal; never authorizes production."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from kernel.p6.registry import LIVE_FIELDS


class P10Denied(ValueError):
    """Raised when a stopped P10 rehearsal is called again."""


class SyntheticP10Governance:
    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"
    CONTROL_FAMILIES = {
        "daily_financial_reconciliation",
        "weekly_authority_configuration_anomaly",
        "monthly_recovery_access",
        "incident_material_change_recertification",
    }
    REQUIRED_ROLES = {
        "service_owner",
        "incident_owner",
        "audit_owner",
        "suspension_owner",
    }
    ACTION_FIELDS = {
        "execution_performed",
        "live_action_permitted",
        "external_action",
        "unauthorized_action",
        "live_credential",
        "provider_call",
        "network_call",
        "deployment_performed",
        "customer_contact_performed",
        "capital_action_performed",
        "payment_performed",
        "broker_action_performed",
        "worker_action_performed",
        "venture_action_performed",
        "model_output_authorization",
    }
    EVENT_TYPES = {"ownership", "control_attestation", "change_review", "incident", "steady_state_review"}
    HEX64 = re.compile(r"^[a-f0-9]{64}$")
    HEX40 = re.compile(r"^[a-f0-9]{40}$")

    def __init__(self, *, configuration_fingerprint: str, source_commit: str):
        if not isinstance(configuration_fingerprint, str) or not self.HEX64.fullmatch(configuration_fingerprint):
            raise ValueError("configuration_fingerprint must be a SHA-256 digest")
        if not isinstance(source_commit, str) or not self.HEX40.fullmatch(source_commit):
            raise ValueError("source_commit must be a full Git commit hash")
        self.configuration_fingerprint = configuration_fingerprint
        self.source_commit = source_commit
        self._stopped = False
        self._events: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
        self._last_sequence: dict[str, int] = {}
        self._evidence: dict[str, dict[str, Any]] = {}

    @staticmethod
    def canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

    @classmethod
    def digest(cls, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _safe_result(self, event_id: str, run_id: str, disposition: str, reason: str = "") -> dict[str, Any]:
        return {
            "event_id": event_id if isinstance(event_id, str) else "invalid",
            "run_id": run_id if isinstance(run_id, str) else "invalid",
            "disposition": disposition,
            "reason": reason,
            "execution_class": self.EXECUTION_CLASS,
            "synthetic_only": True,
            "effect": "none",
            "execution_performed": False,
            "live_action_permitted": False,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "provider_call": False,
            "network_call": False,
            "deployment_performed": False,
            "customer_contact_performed": False,
            "capital_action_performed": False,
            "payment_performed": False,
            "broker_action_performed": False,
            "worker_action_performed": False,
            "venture_action_performed": False,
            "model_output_authorization": False,
            "production_authorized": False,
            "go_live_authorized": False,
            "authority_flags": {field: False for field in LIVE_FIELDS},
            **{field: False for field in LIVE_FIELDS},
            "stop_required": disposition in {"BLOCKED", "SUSPENSION_SIMULATED"},
        }

    def _block(self, event: Mapping[str, Any] | Any, reason: str) -> dict[str, Any]:
        self._stopped = True
        event_id = event.get("event_id", "invalid") if isinstance(event, Mapping) else "invalid"
        run_id = event.get("run_id", "invalid") if isinstance(event, Mapping) else "invalid"
        return self._safe_result(event_id, run_id, "BLOCKED", reason)

    def _payload_valid(self, event_type: str, payload: Any, state: dict[str, Any]) -> tuple[str, str]:
        if not isinstance(payload, Mapping):
            return "BLOCKED", "PAYLOAD_MUST_BE_OBJECT"

        if event_type == "ownership":
            if set(payload) != self.REQUIRED_ROLES:
                return "BLOCKED", "OWNERSHIP_ROLE_SET_INVALID"
            values = list(payload.values())
            if any(not isinstance(value, str) or not value.startswith("synthetic-") or len(value) < 11 for value in values):
                return "BLOCKED", "OWNER_IDENTITY_NOT_SYNTHETIC"
            if len(set(values)) != len(values):
                return "BLOCKED", "ROLE_SEPARATION_VIOLATION"
            state["ownership"] = True
            return "SIMULATED", ""

        if event_type == "control_attestation":
            if set(payload) != {"control_family", "status"}:
                return "BLOCKED", "CONTROL_ATTESTATION_SHAPE_INVALID"
            family, status = payload["control_family"], payload["status"]
            if not isinstance(family, str) or family not in self.CONTROL_FAMILIES:
                return "BLOCKED", "CONTROL_FAMILY_INVALID"
            if status != "PASS":
                return "BLOCKED", "REQUIRED_CONTROL_NOT_PASSED"
            state["controls"].add(family)
            return "CONTROL_SIMULATED", ""

        if event_type == "change_review":
            required = {"impact_analysis", "test_result", "rollback_plan", "approver", "rollout_mode"}
            if set(payload) != required:
                return "BLOCKED", "CHANGE_REVIEW_SHAPE_INVALID"
            if any(not isinstance(payload[key], str) or not payload[key].strip()
                   for key in ("impact_analysis", "rollback_plan")):
                return "BLOCKED", "CHANGE_EVIDENCE_MISSING"
            if payload["test_result"] != "PASS":
                return "BLOCKED", "CHANGE_TESTS_NOT_PASSED"
            if not isinstance(payload["approver"], str) or not payload["approver"].startswith("synthetic-"):
                return "BLOCKED", "APPROVER_IDENTITY_NOT_SYNTHETIC"
            if payload["rollout_mode"] != "shadow":
                return "BLOCKED", "ROLLOUT_MUST_REMAIN_SHADOW"
            state["change_review"] = True
            return "CHANGE_REVIEW_SIMULATED", ""

        if event_type == "incident":
            required = {"incident_id", "severity", "suspension_requested"}
            if set(payload) != required:
                return "BLOCKED", "INCIDENT_SHAPE_INVALID"
            if (not isinstance(payload["incident_id"], str)
                    or not payload["incident_id"].startswith("synthetic-")
                    or payload["severity"] not in {"high", "critical"}
                    or payload["suspension_requested"] is not True):
                return "BLOCKED", "INCIDENT_SUSPENSION_REQUIRED"
            return "SUSPENSION_SIMULATED", "SYNTHETIC_INCIDENT_SUSPENSION"

        if event_type == "steady_state_review":
            if set(payload) != {"evidence_event_ids"}:
                return "BLOCKED", "REVIEW_SHAPE_INVALID"
            references = payload["evidence_event_ids"]
            if not isinstance(references, list) or any(not isinstance(item, str) for item in references):
                return "BLOCKED", "REVIEW_EVIDENCE_REFERENCES_INVALID"
            if len(references) != len(set(references)) or references != state["event_ids"]:
                return "BLOCKED", "REVIEW_EVIDENCE_SET_MISMATCH"
            if not state["ownership"] or state["controls"] != self.CONTROL_FAMILIES or not state["change_review"]:
                return "BLOCKED", "STEADY_STATE_EVIDENCE_INCOMPLETE"
            return "SYNTHETIC_REHEARSAL_PASS", ""

        return "BLOCKED", "EVENT_TYPE_INVALID"

    def evaluate(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise P10Denied("P10 rehearsal is stopped and fail-closed")
        if not isinstance(record, Mapping):
            return self._block(record, "RECORD_MUST_BE_OBJECT")

        common = {
            "event_id", "run_id", "sequence", "event_type", "execution_class",
            "synthetic_only", "effect", "configuration_fingerprint", "source_commit",
            "payload", "failure_injection", "model_output_authorization", "evidence_hash",
            *LIVE_FIELDS, *self.ACTION_FIELDS,
        }
        allowed = common | {"model_output"}
        if set(record) - allowed or not common.issubset(record):
            return self._block(record, "REQUIRED_OR_ALLOWED_FIELDS_INVALID")
        if (not isinstance(record["event_id"], str) or not record["event_id"]
                or not isinstance(record["run_id"], str) or not record["run_id"]):
            return self._block(record, "EVENT_AND_RUN_IDENTITIES_REQUIRED")
        if type(record["sequence"]) is not int or record["sequence"] < 1:
            return self._block(record, "SEQUENCE_INVALID")
        if not isinstance(record["event_type"], str) or record["event_type"] not in self.EVENT_TYPES:
            return self._block(record, "EVENT_TYPE_INVALID")
        if (record["execution_class"] != self.EXECUTION_CLASS
                or record["synthetic_only"] is not True or record["effect"] != "none"):
            return self._block(record, "EXECUTION_MODE_OR_EFFECT_DRIFT")
        if record["configuration_fingerprint"] != self.configuration_fingerprint:
            return self._block(record, "CONFIGURATION_FINGERPRINT_MISMATCH")
        if record["source_commit"] != self.source_commit:
            return self._block(record, "SOURCE_COMMIT_MISMATCH")
        if any(record[field] is not False for field in LIVE_FIELDS):
            return self._block(record, "LIVE_AUTHORITY_DRIFT")
        if any(record[field] is not False for field in self.ACTION_FIELDS):
            return self._block(record, "ACTION_OR_MODEL_AUTHORIZATION_DRIFT")
        if "model_output" in record and not isinstance(record["model_output"], str):
            return self._block(record, "MODEL_OUTPUT_MUST_BE_INERT_TEXT")
        if type(record["failure_injection"]) is not bool:
            return self._block(record, "FAILURE_INJECTION_FLAG_INVALID")

        material = dict(record)
        supplied_hash = material.pop("evidence_hash")
        try:
            expected_hash = self.digest(self.canonical(material))
        except (TypeError, ValueError):
            return self._block(record, "RECORD_NOT_CANONICAL_JSON")
        if not isinstance(supplied_hash, str) or not self.HEX64.fullmatch(supplied_hash) or supplied_hash != expected_hash:
            return self._block(record, "EVIDENCE_HASH_MISMATCH")

        key = (record["run_id"], record["event_id"])
        record_hash = self.digest(self.canonical(record))
        prior = self._events.get(key)
        if prior is not None:
            if prior[0] != record_hash:
                return self._block(record, "EVENT_ID_COLLISION")
            return dict(prior[1])

        expected_sequence = self._last_sequence.get(record["run_id"], 0) + 1
        if record["sequence"] != expected_sequence:
            return self._block(record, "SEQUENCE_VIOLATION")
        if record["failure_injection"]:
            return self._block(record, "INJECTED_FAILURE")

        state = self._evidence.setdefault(record["run_id"], {
            "ownership": False, "controls": set(), "change_review": False, "event_ids": [],
        })
        disposition, reason = self._payload_valid(record["event_type"], record["payload"], state)
        if disposition == "BLOCKED":
            return self._block(record, reason)

        result = self._safe_result(record["event_id"], record["run_id"], disposition, reason)
        result["model_output_ignored"] = "model_output" in record
        result["record_hash"] = record_hash
        result["evidence_hash"] = supplied_hash
        result["stop_required"] = disposition in {"SYNTHETIC_REHEARSAL_PASS", "SUSPENSION_SIMULATED"}
        if disposition == "SUSPENSION_SIMULATED":
            self._stopped = True
        self._last_sequence[record["run_id"]] = record["sequence"]
        self._events[key] = (record_hash, dict(result))
        if record["event_type"] != "steady_state_review":
            state["event_ids"].append(record["event_id"])
        return result

    def automatic_stop(self, reason: str) -> dict[str, Any]:
        if not isinstance(reason, str) or not reason.strip():
            raise P10Denied("synthetic stop reason is required")
        self._stopped = True
        return self._safe_result("stop", "synthetic", "SUSPENSION_SIMULATED", reason)

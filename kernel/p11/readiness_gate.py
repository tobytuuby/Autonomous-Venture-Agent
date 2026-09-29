"""In-memory validator for a synthetic production-readiness review package.

This module never performs or authorizes a production test.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from kernel.p6.registry import LIVE_FIELDS


class ReadinessGateDenied(ValueError):
    """Raised when a stopped readiness-gate evaluator is reused."""


class SyntheticReadinessGate:
    """Check a fixture-only candidate plan and return review readiness only."""

    GATE_VERSION = "1.0"
    EXECUTION_CLASS = "synthetic-shadow-isolated-pre-production"
    HEX64 = re.compile(r"^[a-f0-9]{64}$")
    HEX40 = re.compile(r"^[a-f0-9]{40}$")

    ACTION_FIELDS = frozenset({
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
    })

    CANDIDATE_FIELDS = frozenset({
        "environment", "target_ref", "venture_count", "operation",
        "data_classification", "duration_minutes", "concurrency",
        "write_operations", "customer_data", "customer_contact",
        "external_actions", "allowed_authorities", "exposure_limit_usd",
        "loss_limit_usd", "network_access", "credential_access",
        "provider_access",
    })

    SAFEGUARDS = frozenset({
        "two_person_start_approval",
        "kill_switch_ready",
        "authority_monitoring",
        "evidence_capture",
        "operator_present",
        "independent_reviewer_reserved",
    })

    REQUIRED_METRICS = frozenset({
        "authority_flags", "action_attempts", "data_classification",
        "exposure_usd", "window_elapsed", "service_health", "error_rate",
        "p95_latency", "evidence_integrity",
    })

    REQUIRED_STOP_CONDITIONS = frozenset({
        "any_authority_true", "any_action_attempt", "any_write_attempt",
        "customer_data_detected", "exposure_or_loss_nonzero", "window_exceeded",
        "monitor_heartbeat_lost", "service_health_breach",
        "evidence_integrity_failure", "manual_stop",
    })

    TOP_FIELDS = frozenset({
        "review_id", "gate_version", "execution_class", "synthetic_only",
        "effect", "configuration_fingerprint", "source_commit",
        "candidate_test", "safeguards", "monitoring", "recovery",
        "independent_review", "failure_injection",
        "model_output_authorization", "evidence_hash",
    })

    def __init__(self, *, configuration_fingerprint: str, source_commit: str):
        if not isinstance(configuration_fingerprint, str) or not self.HEX64.fullmatch(configuration_fingerprint):
            raise ValueError("configuration_fingerprint must be a SHA-256 digest")
        if not isinstance(source_commit, str) or not self.HEX40.fullmatch(source_commit):
            raise ValueError("source_commit must be a full Git commit hash")
        self.configuration_fingerprint = configuration_fingerprint
        self.source_commit = source_commit
        self._stopped = False
        self._reviews: dict[str, tuple[str, dict[str, Any]]] = {}

    @staticmethod
    def canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)

    @classmethod
    def digest(cls, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _safe_result(self, review_id: Any, disposition: str, reason: str = "",
                     input_hash: str = "") -> dict[str, Any]:
        authorities = {field: False for field in LIVE_FIELDS}
        actions = {field: False for field in self.ACTION_FIELDS}
        return {
            "review_id": review_id if isinstance(review_id, str) else "invalid",
            "disposition": disposition,
            "reason": reason,
            "input_hash": input_hash,
            "execution_class": self.EXECUTION_CLASS,
            "synthetic_only": True,
            "effect": "none",
            "review_ready": disposition == "READY_FOR_INDEPENDENT_REVIEW",
            "production_ready": False,
            "production_authorized": False,
            "limited_test_authorized": False,
            "go_live_authorized": False,
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
            "authority_flags": authorities,
            "action_flags": actions,
            **authorities,
            **actions,
        }

    def _block(self, review_id: Any, reason: str, input_hash: str = "") -> dict[str, Any]:
        self._stopped = True
        return self._safe_result(review_id, "BLOCKED", reason, input_hash)

    @staticmethod
    def _is_nonempty_text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _validate_candidate(self, value: Any) -> str:
        if not isinstance(value, Mapping) or set(value) != self.CANDIDATE_FIELDS:
            return "CANDIDATE_TEST_SHAPE_INVALID"
        if value["environment"] != "production":
            return "CANDIDATE_ENVIRONMENT_INVALID"
        target = value["target_ref"]
        if not isinstance(target, str) or not target.startswith("fixture-") or len(target) < 12:
            return "TARGET_MUST_BE_SYNTHETIC_FIXTURE"
        if type(value["venture_count"]) is not int or value["venture_count"] != 1:
            return "VENTURE_COUNT_MUST_BE_ONE"
        if value["operation"] != "read_only_observation":
            return "OPERATION_MUST_BE_READ_ONLY"
        if value["data_classification"] != "synthetic":
            return "DATA_MUST_BE_SYNTHETIC"
        duration = value["duration_minutes"]
        if type(duration) is not int or not 1 <= duration <= 30:
            return "DURATION_EXCEEDS_BOUND"
        if type(value["concurrency"]) is not int or value["concurrency"] != 1:
            return "CONCURRENCY_MUST_BE_ONE"
        for field in (
            "write_operations", "customer_data", "customer_contact",
            "external_actions", "network_access", "credential_access",
            "provider_access",
        ):
            if value[field] is not False:
                return "FORBIDDEN_CANDIDATE_CAPABILITY"
        if value["allowed_authorities"] != []:
            return "ALLOWED_AUTHORITIES_MUST_BE_EMPTY"
        for field in ("exposure_limit_usd", "loss_limit_usd"):
            amount = value[field]
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount != 0:
                return "EXPOSURE_AND_LOSS_LIMITS_MUST_BE_ZERO"
        return ""

    def _validate(self, record: Mapping[str, Any]) -> str:
        allowed = self.TOP_FIELDS | self.ACTION_FIELDS | frozenset(LIVE_FIELDS) | {"model_output"}
        if set(record) - allowed or not (self.TOP_FIELDS | self.ACTION_FIELDS | frozenset(LIVE_FIELDS)).issubset(record):
            return "REQUIRED_OR_ALLOWED_FIELDS_INVALID"
        if not self._is_nonempty_text(record["review_id"]):
            return "REVIEW_ID_REQUIRED"
        if record["gate_version"] != self.GATE_VERSION:
            return "GATE_VERSION_MISMATCH"
        if record["execution_class"] != self.EXECUTION_CLASS or record["synthetic_only"] is not True or record["effect"] != "none":
            return "EXECUTION_MODE_OR_EFFECT_DRIFT"
        if record["configuration_fingerprint"] != self.configuration_fingerprint:
            return "CONFIGURATION_FINGERPRINT_MISMATCH"
        if record["source_commit"] != self.source_commit:
            return "SOURCE_COMMIT_MISMATCH"
        if any(record[field] is not False for field in LIVE_FIELDS):
            return "LIVE_AUTHORITY_DRIFT"
        if any(record[field] is not False for field in self.ACTION_FIELDS):
            return "ACTION_OR_MODEL_AUTHORIZATION_DRIFT"
        if "model_output" in record and not isinstance(record["model_output"], str):
            return "MODEL_OUTPUT_MUST_BE_INERT_TEXT"
        if type(record["failure_injection"]) is not bool:
            return "FAILURE_INJECTION_FLAG_INVALID"
        if record["failure_injection"]:
            return "INJECTED_FAILURE"

        reason = self._validate_candidate(record["candidate_test"])
        if reason:
            return reason

        safeguards = record["safeguards"]
        if not isinstance(safeguards, Mapping) or set(safeguards) != self.SAFEGUARDS:
            return "SAFEGUARD_SET_INVALID"
        if any(safeguards[key] is not True for key in self.SAFEGUARDS):
            return "REQUIRED_SAFEGUARD_MISSING"

        monitoring = record["monitoring"]
        monitor_fields = {"metrics", "stop_conditions", "heartbeat_timeout_seconds", "automatic_stop", "alert_route"}
        if not isinstance(monitoring, Mapping) or set(monitoring) != monitor_fields:
            return "MONITORING_SHAPE_INVALID"
        metrics = monitoring["metrics"]
        if not isinstance(metrics, list) or any(not isinstance(item, str) for item in metrics):
            return "MONITORING_METRICS_INVALID"
        if len(metrics) != len(set(metrics)) or not self.REQUIRED_METRICS.issubset(metrics):
            return "REQUIRED_MONITORING_MISSING"
        stops = monitoring["stop_conditions"]
        if not isinstance(stops, list) or any(not isinstance(item, str) for item in stops):
            return "STOP_CONDITIONS_INVALID"
        if len(stops) != len(set(stops)) or not self.REQUIRED_STOP_CONDITIONS.issubset(stops):
            return "REQUIRED_STOP_CONDITION_MISSING"
        timeout = monitoring["heartbeat_timeout_seconds"]
        if type(timeout) is not int or not 1 <= timeout <= 60:
            return "MONITOR_HEARTBEAT_TIMEOUT_INVALID"
        if monitoring["automatic_stop"] is not True:
            return "AUTOMATIC_STOP_REQUIRED"
        if not isinstance(monitoring["alert_route"], str) or not monitoring["alert_route"].startswith("fixture-"):
            return "ALERT_ROUTE_MUST_BE_FIXTURE"

        recovery = record["recovery"]
        recovery_fields = {"rollback_mode", "recovery_rehearsed", "operator_handle"}
        if not isinstance(recovery, Mapping) or set(recovery) != recovery_fields:
            return "RECOVERY_PLAN_SHAPE_INVALID"
        if recovery["rollback_mode"] != "no_state_change" or recovery["recovery_rehearsed"] is not True:
            return "RECOVERY_MUST_BE_REHEARSED_WITHOUT_MUTATION"
        if not isinstance(recovery["operator_handle"], str) or not recovery["operator_handle"].startswith("fixture-"):
            return "RECOVERY_OPERATOR_MUST_BE_FIXTURE"

        review = record["independent_review"]
        review_fields = {
            "required", "reviewer_handle", "implementer_handle", "reviewer_distinct",
            "hash_recomputation_required", "exact_source_commit_bound", "decision_required",
        }
        if not isinstance(review, Mapping) or set(review) != review_fields:
            return "INDEPENDENT_REVIEW_SHAPE_INVALID"
        reviewer, implementer = review["reviewer_handle"], review["implementer_handle"]
        if (not isinstance(reviewer, str) or not reviewer.startswith("fixture-")
                or not isinstance(implementer, str) or not implementer.startswith("fixture-")
                or reviewer == implementer):
            return "REVIEWER_MUST_BE_DISTINCT_FIXTURE"
        for field in ("required", "reviewer_distinct", "hash_recomputation_required",
                      "exact_source_commit_bound", "decision_required"):
            if review[field] is not True:
                return "INDEPENDENT_REVIEW_REQUIREMENT_MISSING"
        return ""

    def evaluate(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if self._stopped:
            raise ReadinessGateDenied("readiness gate is stopped and fail-closed")
        if not isinstance(record, Mapping):
            return self._block("invalid", "RECORD_MUST_BE_OBJECT")
        review_id = record.get("review_id", "invalid")
        if not self._is_nonempty_text(review_id):
            return self._block(review_id, "REVIEW_ID_REQUIRED")
        material = dict(record)
        supplied_hash = material.pop("evidence_hash", None)
        try:
            canonical_material = self.canonical(material)
            input_hash = self.digest(canonical_material)
        except (TypeError, ValueError):
            return self._block(review_id, "RECORD_NOT_CANONICAL_JSON")
        if not isinstance(supplied_hash, str) or not self.HEX64.fullmatch(supplied_hash) or supplied_hash != input_hash:
            return self._block(review_id, "EVIDENCE_HASH_MISMATCH", input_hash)
        try:
            record_hash = self.digest(self.canonical(dict(record)))
        except (TypeError, ValueError):
            return self._block(review_id, "RECORD_NOT_CANONICAL_JSON", input_hash)
        prior = self._reviews.get(review_id)
        if prior is not None:
            if prior[0] == record_hash:
                return copy.deepcopy(prior[1])
            return self._block(review_id, "REVIEW_ID_COLLISION", input_hash)
        reason = self._validate(record)
        if reason:
            return self._block(review_id, reason, input_hash)
        result = self._safe_result(review_id, "READY_FOR_INDEPENDENT_REVIEW", "", input_hash)
        result["model_output_ignored"] = "model_output" in record
        self._reviews[review_id] = (record_hash, copy.deepcopy(result))
        return result

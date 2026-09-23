"""P7.5 synthetic worker authority boundary.

This module represents worker admission and task records only. It never
creates or dispatches a worker and performs no external I/O.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical, digest


_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_ALLOWED_FAILURES = {
    "admission",
    "capability",
    "provenance",
    "revocation",
    "replay",
    "persistence",
    "recovery",
    "isolation",
}
_STATES = {"ACTIVE", "FROZEN", "REVOKED", "QUARANTINED", "WOUND_DOWN"}
_REQUIRED_ADMISSION = {
    "worker_id",
    "manager_id",
    "venture_id",
    "portfolio_id",
    "archetype_id",
    "task_classes",
    "capabilities",
    "originating_capabilities",
    "policy_version",
    "configuration_fingerprint",
    "environment_identity",
    "provenance",
    "correlation_id",
    "idempotency_key",
    "actor",
    "synthetic_only",
    "effect",
}
_REQUIRED_PROVENANCE = {"source_ids", "source_hashes", "lineage"}
_AUTHORITY_STATES = (
    "request",
    "approval",
    "dispatch",
    "response",
    "reconciliation",
    "failure",
    "freeze",
    "revoke",
    "quarantine-wind-down",
)


class WorkerBoundaryError(ValueError):
    """Raised for any invalid, effectful, or fail-closed operation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash(value: Any) -> str:
    return digest(canonical(value))


def _require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkerBoundaryError("INVALID_IDENTITY", f"{field} is required")
    return value


def _require_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise WorkerBoundaryError("INVALID_HASH", f"{field} must be a SHA-256 digest")
    return value


def _authority_flags(record: Mapping[str, Any]) -> dict[str, bool]:
    return {field: bool(record.get(field, False)) for field in LIVE_FIELDS}


def _require_denied_authorities(record: Mapping[str, Any]) -> None:
    flags = _authority_flags(record)
    if any(flags.values()):
        raise WorkerBoundaryError("LIVE_AUTHORITY", "all live authorities must be false")
    if record.get("synthetic_only") is not True:
        raise WorkerBoundaryError("NOT_SYNTHETIC", "record must be synthetic-only")
    if record.get("effect") != "none":
        raise WorkerBoundaryError("EFFECTFUL_RECORD", "record effect must be none")


def _validate_provenance(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not _REQUIRED_PROVENANCE.issubset(value):
        raise WorkerBoundaryError("MISSING_PROVENANCE", "complete provenance is required")
    source_ids = value["source_ids"]
    source_hashes = value["source_hashes"]
    lineage = value["lineage"]
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or any(not isinstance(item, str) or not item for item in source_ids)
    ):
        raise WorkerBoundaryError("INVALID_PROVENANCE", "source_ids must be non-empty strings")
    if (
        not isinstance(source_hashes, list)
        or len(source_ids) != len(source_hashes)
        or any(not isinstance(item, str) or not _HEX64.fullmatch(item) for item in source_hashes)
    ):
        raise WorkerBoundaryError("INVALID_PROVENANCE", "source_hashes must align and be SHA-256")
    if (
        not isinstance(lineage, list)
        or not lineage
        or any(not isinstance(item, str) or not item for item in lineage)
    ):
        raise WorkerBoundaryError("INVALID_PROVENANCE", "lineage must be non-empty")
    result = dict(value)
    result["provenance_hash"] = _hash({
        "source_ids": source_ids,
        "source_hashes": source_hashes,
        "lineage": lineage,
    })
    return result


class SyntheticWorkerBoundary:
    """Kernel-owned synthetic worker admission and recording boundary."""

    def __init__(
        self,
        *,
        policy_version: str,
        configuration_fingerprint: str,
        environment_identity: str,
    ):
        _require_hash(configuration_fingerprint, "configuration_fingerprint")
        self.policy_version = _require_id(policy_version, "policy_version")
        self.configuration_fingerprint = configuration_fingerprint
        self.environment_identity = _require_id(environment_identity, "environment_identity")
        self._workers: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, dict[str, Any]] = {}
        self._requests: dict[str, str] = {}
        self._quarantine: list[dict[str, Any]] = []
        self._audit: list[dict[str, Any]] = []
        self._failure_control: str | None = None
        self._fail_closed = False

    @property
    def fail_closed(self) -> bool:
        return self._fail_closed

    def _guard(self, control: str | None = None) -> None:
        if self._fail_closed:
            raise WorkerBoundaryError(
                "TERMINAL_FAIL_CLOSED",
                f"boundary is terminally fail-closed: {self._failure_control}",
            )
        if control and self._failure_control == control:
            self._fail_closed = True
            raise WorkerBoundaryError(
                "INJECTED_FAILURE",
                f"injected {control} failure entered terminal fail-closed state",
            )

    def inject_failure(self, control: str) -> None:
        if control not in _ALLOWED_FAILURES:
            raise WorkerBoundaryError("UNKNOWN_FAILURE", f"unsupported failure control: {control}")
        self._failure_control = control
        self._fail_closed = True

    def authorities(self) -> dict[str, bool]:
        return {field: False for field in LIVE_FIELDS}

    def authority_case(
        self,
        *,
        authority: str,
        state: str,
        request: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an authority attempt as denied without dispatch or side effect."""
        self._guard()
        if authority not in {
            "network", "broker", "payment", "credential", "deployment",
            "customer", "capital", "venture", "worker",
        }:
            raise WorkerBoundaryError("UNKNOWN_AUTHORITY", "authority is not in the P7 matrix")
        if state not in _AUTHORITY_STATES:
            raise WorkerBoundaryError("UNKNOWN_STATE", "state is not in the P7 matrix")
        request = dict(request or {})
        _require_denied_authorities({
            **request,
            "synthetic_only": True,
            "effect": "none",
        })
        result = {
            "authority": authority,
            "state": state,
            "decision": "DENY",
            "status": "CONTAINED",
            "synthetic_only": True,
            "effect": "none",
            **self.authorities(),
        }
        self._audit.append(result)
        return copy.deepcopy(result)

    def admit_worker(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self._guard("admission")
        if not _REQUIRED_ADMISSION.issubset(request):
            missing = sorted(_REQUIRED_ADMISSION.difference(request))
            raise WorkerBoundaryError("MISSING_FIELD", f"missing admission fields: {missing}")
        _require_denied_authorities(request)
        worker_id = _require_id(request["worker_id"], "worker_id")
        manager_id = _require_id(request["manager_id"], "manager_id")
        venture_id = _require_id(request["venture_id"], "venture_id")
        portfolio_id = _require_id(request["portfolio_id"], "portfolio_id")
        archetype_id = _require_id(request["archetype_id"], "archetype_id")
        if request["policy_version"] != self.policy_version:
            raise WorkerBoundaryError("POLICY_MISMATCH", "policy version mismatch")
        if request["configuration_fingerprint"] != self.configuration_fingerprint:
            raise WorkerBoundaryError("CONFIGURATION_MISMATCH", "configuration mismatch")
        if request["environment_identity"] != self.environment_identity:
            raise WorkerBoundaryError("ENVIRONMENT_MISMATCH", "environment mismatch")
        actor = request["actor"]
        if not isinstance(actor, Mapping) or not actor.get("actor_id") or not actor.get("role"):
            raise WorkerBoundaryError("INVALID_ACTOR", "actor identity is required")
        if actor.get("role") == "worker-shadow":
            raise WorkerBoundaryError("SELF_ADMISSION", "worker cannot approve its own admission")
        task_classes = request["task_classes"]
        if (
            not isinstance(task_classes, list)
            or not task_classes
            or any(not isinstance(item, str) or not item for item in task_classes)
        ):
            raise WorkerBoundaryError("INVALID_TASK_CLASSES", "task_classes must be non-empty strings")
        capabilities = request["capabilities"]
        originating = request["originating_capabilities"]
        if (
            not isinstance(capabilities, list)
            or not isinstance(originating, list)
            or any(not isinstance(item, str) or not item for item in capabilities)
            or any(not isinstance(item, str) or not item for item in originating)
            or not set(capabilities).issubset(set(originating))
        ):
            raise WorkerBoundaryError("CAPABILITY_WIDENING", "worker capabilities must be a subset")
        if request.get("model_output") or request.get("approval_source") == "model":
            raise WorkerBoundaryError("MODEL_AUTHORIZATION", "model output cannot authorize admission")
        provenance = _validate_provenance(request["provenance"])
        request_hash = _hash({
            key: value for key, value in request.items()
            if key not in {"status", "record_hash", "created_at"}
        })
        existing_hash = self._requests.get(request["idempotency_key"])
        if existing_hash:
            if existing_hash != request_hash:
                self._quarantine_record(request, "REQUEST_COLLISION")
                raise WorkerBoundaryError("REQUEST_COLLISION", "idempotency key content changed")
            existing = self._workers.get(worker_id)
            if existing is None:
                raise WorkerBoundaryError("REPLAY_NOT_FOUND", "replayed worker is not recorded")
            result = copy.deepcopy(existing)
            result["duplicate"] = True
            return result
        if worker_id in self._workers:
            raise WorkerBoundaryError("IDENTITY_COLLISION", "worker identity already exists")
        record = {
            "worker_id": worker_id,
            "manager_id": manager_id,
            "venture_id": venture_id,
            "portfolio_id": portfolio_id,
            "archetype_id": archetype_id,
            "task_classes": list(task_classes),
            "capabilities": sorted(set(capabilities)),
            "originating_capabilities": sorted(set(originating)),
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "environment_identity": self.environment_identity,
            "provenance": provenance,
            "correlation_id": _require_id(request["correlation_id"], "correlation_id"),
            "idempotency_key": _require_id(request["idempotency_key"], "idempotency_key"),
            "actor": dict(actor),
            "state": "ACTIVE",
            "synthetic_only": True,
            "effect": "none",
            "created_at": _now(),
            "cross_venture_visibility": False,
            "self_escalation_allowed": False,
            **self.authorities(),
        }
        record["record_hash"] = _hash(record)
        self._workers[worker_id] = record
        self._requests[record["idempotency_key"]] = request_hash
        self._audit.append({
            "event": "ADMISSION_RECORDED",
            "worker_id": worker_id,
            "record_hash": record["record_hash"],
            "synthetic_only": True,
            "effect": "none",
        })
        return copy.deepcopy(record)

    def record_task(self, task: Mapping[str, Any]) -> dict[str, Any]:
        self._guard("capability")
        required = {
            "task_id",
            "worker_id",
            "venture_id",
            "capabilities",
            "provenance",
            "idempotency_key",
            "synthetic_only",
            "effect",
        }
        if not required.issubset(task):
            raise WorkerBoundaryError("MISSING_FIELD", "complete task envelope is required")
        _require_denied_authorities(task)
        task_id = _require_id(task["task_id"], "task_id")
        worker_id = _require_id(task["worker_id"], "worker_id")
        worker = self._workers.get(worker_id)
        if worker is None:
            raise WorkerBoundaryError("UNKNOWN_WORKER", "worker is not admitted")
        if worker["state"] != "ACTIVE":
            raise WorkerBoundaryError("WORKER_NOT_ACTIVE", "worker is frozen, revoked, quarantined, or wound down")
        if task["venture_id"] != worker["venture_id"]:
            raise WorkerBoundaryError("CROSS_VENTURE", "task venture does not match worker venture")
        capabilities = task["capabilities"]
        if not isinstance(capabilities, list) or not set(capabilities).issubset(set(worker["capabilities"])):
            raise WorkerBoundaryError("CAPABILITY_WIDENING", "task capabilities exceed worker envelope")
        if task.get("model_output") or task.get("approval_source") == "model":
            raise WorkerBoundaryError("MODEL_AUTHORIZATION", "model output cannot authorize a task")
        provenance = _validate_provenance(task["provenance"])
        record = {
            "task_id": task_id,
            "worker_id": worker_id,
            "venture_id": worker["venture_id"],
            "capabilities": sorted(set(capabilities)),
            "provenance": provenance,
            "idempotency_key": _require_id(task["idempotency_key"], "idempotency_key"),
            "synthetic_only": True,
            "effect": "none",
            "status": "RECORDED",
            **self.authorities(),
        }
        existing = self._tasks.get(task_id)
        record_hash = _hash(record)
        if existing:
            if existing["record_hash"] != record_hash:
                self._quarantine_record(task, "TASK_COLLISION")
                raise WorkerBoundaryError("REQUEST_COLLISION", "task replay content changed")
            result = copy.deepcopy(existing)
            result["duplicate"] = True
            return result
        record["record_hash"] = record_hash
        self._tasks[task_id] = record
        return copy.deepcopy(record)

    def freeze(self, worker_id: str, reason: str = "synthetic-freeze") -> dict[str, Any]:
        return self._transition(worker_id, "FROZEN", reason)

    def revoke(self, worker_id: str, reason: str = "synthetic-revocation") -> dict[str, Any]:
        return self._transition(worker_id, "REVOKED", reason)

    def quarantine(self, worker_id: str, reason: str = "synthetic-quarantine") -> dict[str, Any]:
        return self._transition(worker_id, "QUARANTINED", reason)

    def wind_down(self, worker_id: str, reason: str = "synthetic-wind-down") -> dict[str, Any]:
        return self._transition(worker_id, "WOUND_DOWN", reason)

    def rollback(self, worker_id: str, reason: str = "synthetic-rollback") -> dict[str, Any]:
        return self._transition(worker_id, "WOUND_DOWN", reason)

    def _transition(self, worker_id: str, state: str, reason: str) -> dict[str, Any]:
        self._guard("revocation" if state == "REVOKED" else "recovery")
        worker_id = _require_id(worker_id, "worker_id")
        worker = self._workers.get(worker_id)
        if worker is None:
            raise WorkerBoundaryError("UNKNOWN_WORKER", "worker is not admitted")
        if worker["state"] == "REVOKED" and state != "REVOKED":
            raise WorkerBoundaryError("REVOKED_IMMUTABLE", "revoked worker cannot be restored")
        worker = copy.deepcopy(worker)
        worker["state"] = state
        worker["transition_reason"] = _require_id(reason, "reason")
        worker["transitioned_at"] = _now()
        worker["record_hash"] = _hash(worker)
        self._workers[worker_id] = worker
        self._audit.append({
            "event": state,
            "worker_id": worker_id,
            "reason": reason,
            "record_hash": worker["record_hash"],
            "synthetic_only": True,
            "effect": "none",
        })
        return copy.deepcopy(worker)

    def _quarantine_record(self, record: Mapping[str, Any], reason: str) -> None:
        evidence_hash = _hash({
            "reason": reason,
            "record": dict(record),
            "configuration_fingerprint": self.configuration_fingerprint,
        })
        self._quarantine.append({
            "reason": reason,
            "evidence_hash": evidence_hash,
            "record": copy.deepcopy(dict(record)),
            "created_at": _now(),
            "synthetic_only": True,
            "effect": "none",
            **self.authorities(),
        })

    def quarantine_records(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._quarantine)

    def snapshot(self) -> dict[str, Any]:
        payload = {
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "environment_identity": self.environment_identity,
            "workers": self._workers,
            "tasks": self._tasks,
            "requests": self._requests,
            "quarantine": self._quarantine,
            "audit": self._audit,
            "failure_control": self._failure_control,
            "fail_closed": self._fail_closed,
            "synthetic_only": True,
            "effect": "none",
            **self.authorities(),
        }
        result = copy.deepcopy(payload)
        result["snapshot_hash"] = _hash(payload)
        return result

    def restore(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        self._guard("recovery")
        if not isinstance(snapshot, Mapping):
            raise WorkerBoundaryError("INVALID_SNAPSHOT", "snapshot must be an object")
        if snapshot.get("configuration_fingerprint") != self.configuration_fingerprint:
            raise WorkerBoundaryError("CONFIGURATION_MISMATCH", "snapshot configuration mismatch")
        if snapshot.get("environment_identity") != self.environment_identity:
            raise WorkerBoundaryError("ENVIRONMENT_MISMATCH", "snapshot environment mismatch")
        _require_denied_authorities(snapshot)
        if snapshot.get("synthetic_only") is not True or snapshot.get("effect") != "none":
            raise WorkerBoundaryError("INVALID_SNAPSHOT", "snapshot is not synthetic-only")
        expected = snapshot.get("snapshot_hash")
        payload = {key: copy.deepcopy(value) for key, value in snapshot.items() if key != "snapshot_hash"}
        if expected != _hash(payload):
            raise WorkerBoundaryError("SNAPSHOT_TAMPERED", "snapshot hash mismatch")
        self._workers = copy.deepcopy(payload["workers"])
        self._tasks = copy.deepcopy(payload["tasks"])
        self._requests = copy.deepcopy(payload["requests"])
        self._quarantine = copy.deepcopy(payload["quarantine"])
        self._audit = copy.deepcopy(payload["audit"])
        self._failure_control = payload["failure_control"]
        self._fail_closed = bool(payload["fail_closed"])
        if self._fail_closed:
            raise WorkerBoundaryError("TERMINAL_FAIL_CLOSED", "restored snapshot is fail-closed")
        return {"status": "RESTORED", "synthetic_only": True, "effect": "none", **self.authorities()}

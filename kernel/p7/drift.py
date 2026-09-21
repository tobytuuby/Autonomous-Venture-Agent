"""Synthetic P7 blocking-drift classification and evidence boundary.

This module has no external-effect capability. A caller supplies the existing
synthetic freeze boundary as a callback. Evidence is written only to a caller-
owned local directory and is content-addressed with SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping


PRESERVATION_SLA_SECONDS = 900
BLOCKING_DRIFT_TYPES = frozenset({
    "authority",
    "ledger",
    "provenance",
    "credential",
    "customer-state",
    "policy",
    "configuration",
})


class DriftClassification(str, Enum):
    ZERO = "ZERO"
    TOLERATED = "TOLERATED"
    BLOCKING = "BLOCKING"


class DriftEvidenceError(RuntimeError):
    """Raised when blocking-drift evidence cannot be safely preserved."""


@dataclass(frozen=True)
class DriftObservation:
    case_id: str
    drift_type: str
    affected_scope: Mapping[str, str]
    expected_state_hash: str
    observed_state_hash: str
    source_ids: tuple[str, ...]
    source_hashes: tuple[str, ...]
    source_commit: str
    configuration_fingerprint: str
    environment_identity: str
    command: str
    detected_at: str
    raw_output: Mapping[str, Any]
    tolerance_bound: int | None = None
    observed_delta: int | None = None
    reviewer_classification: str = "UNREVIEWED"

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id is required")
        if not self.drift_type:
            raise ValueError("drift_type is required")
        if self.expected_state_hash == self.observed_state_hash:
            return
        if not self.expected_state_hash or not self.observed_state_hash:
            raise ValueError("state hashes are required for drift")


@dataclass(frozen=True)
class DriftDecision:
    classification: DriftClassification
    reason: str
    case_id: str
    evidence_path: str | None
    evidence_sha256: str | None
    freeze_action_id: str | None
    preservation_latency_seconds: int | None
    freeze_status: str


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class BlockingDriftController:
    """Classify synthetic observations and freeze/preserve blocking drift."""

    def __init__(
        self,
        *,
        evidence_dir: str | os.PathLike[str],
        freeze_scope: Callable[[Mapping[str, str], str], Mapping[str, Any]],
        now: Callable[[], datetime] | None = None,
        tolerance_rules: Mapping[str, int] | None = None,
    ) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.freeze_scope = freeze_scope
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.tolerance_rules = dict(tolerance_rules or {})

    def classify(self, observation: DriftObservation) -> tuple[DriftClassification, str]:
        if observation.expected_state_hash == observation.observed_state_hash:
            return DriftClassification.ZERO, "observed state matches expected state"

        if observation.drift_type in BLOCKING_DRIFT_TYPES:
            return (
                DriftClassification.BLOCKING,
                f"unexplained {observation.drift_type} drift",
            )

        bound = self.tolerance_rules.get(observation.drift_type)
        if (
            bound is not None
            and observation.observed_delta is not None
            and observation.observed_delta <= bound
            and observation.observed_delta >= 0
            and observation.drift_type not in BLOCKING_DRIFT_TYPES
        ):
            return (
                DriftClassification.TOLERATED,
                f"bounded {observation.drift_type} drift within approved tolerance",
            )

        return DriftClassification.BLOCKING, f"unclassified {observation.drift_type} drift"

    def handle(self, observation: DriftObservation) -> DriftDecision:
        classification, reason = self.classify(observation)
        if classification is DriftClassification.ZERO:
            return DriftDecision(
                classification=classification,
                reason=reason,
                case_id=observation.case_id,
                evidence_path=None,
                evidence_sha256=None,
                freeze_action_id=None,
                preservation_latency_seconds=None,
                freeze_status="NOT_REQUIRED",
            )

        if classification is DriftClassification.TOLERATED:
            return DriftDecision(
                classification=classification,
                reason=reason,
                case_id=observation.case_id,
                evidence_path=None,
                evidence_sha256=None,
                freeze_action_id=None,
                preservation_latency_seconds=None,
                freeze_status="NOT_REQUIRED",
            )

        return self._handle_blocking(observation, reason)

    def _handle_blocking(
        self,
        observation: DriftObservation,
        reason: str,
    ) -> DriftDecision:
        freeze_status = "FAILED"
        freeze_action_id: str | None = None
        freeze_result: Mapping[str, Any] = {}
        try:
            freeze_result = self.freeze_scope(observation.affected_scope, observation.case_id)
            freeze_action_id = str(
                freeze_result.get("action_id") or freeze_result.get("freeze_action_id") or ""
            ) or None
            if freeze_result.get("status") not in {"FROZEN", "QUARANTINED"}:
                raise DriftEvidenceError("freeze callback did not return a frozen status")
            freeze_status = "FROZEN"
        except Exception as error:
            freeze_result = {"error": type(error).__name__, "message": str(error)}

        detected = _utc(observation.detected_at)
        preserved = self.now().astimezone(timezone.utc)
        latency = int((preserved - detected).total_seconds())
        if latency < 0:
            raise DriftEvidenceError("preservation timestamp precedes detection timestamp")
        if latency > PRESERVATION_SLA_SECONDS:
            raise DriftEvidenceError("blocking-drift evidence exceeded 900-second SLA")

        evidence = {
            "case_id": observation.case_id,
            "drift_event_id": f"drift:{observation.case_id}",
            "drift_type": observation.drift_type,
            "classification": DriftClassification.BLOCKING.value,
            "reason": reason,
            "affected_scope": dict(observation.affected_scope),
            "detected_at": observation.detected_at,
            "preserved_at": preserved.isoformat(),
            "preservation_latency_seconds": latency,
            "source_commit": observation.source_commit,
            "configuration_fingerprint": observation.configuration_fingerprint,
            "environment_identity": observation.environment_identity,
            "command": observation.command,
            "source_ids": list(observation.source_ids),
            "source_hashes": list(observation.source_hashes),
            "expected_state_hash": observation.expected_state_hash,
            "observed_state_hash": observation.observed_state_hash,
            "freeze_status": freeze_status,
            "freeze_action_id": freeze_action_id,
            "freeze_result": dict(freeze_result),
            "raw_output": dict(observation.raw_output),
            "reviewer_classification": observation.reviewer_classification,
            "synthetic_only": True,
            "effect": "none",
            "external_action": False,
        }
        serialized = _canonical(evidence) + "\n"
        evidence_hash = _sha256(serialized)
        evidence["evidence_sha256"] = evidence_hash
        serialized = _canonical(evidence) + "\n"
        evidence_hash = _sha256(serialized)

        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        destination = self.evidence_dir / f"{observation.case_id}.json"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.evidence_dir,
            prefix=f".{observation.case_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)

        return DriftDecision(
            classification=DriftClassification.BLOCKING,
            reason=reason,
            case_id=observation.case_id,
            evidence_path=str(destination),
            evidence_sha256=evidence_hash,
            freeze_action_id=freeze_action_id,
            preservation_latency_seconds=latency,
            freeze_status=freeze_status,
        )

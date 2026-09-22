"""Synthetic-only observability and incident-response controls for P7.3."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .recovery import LIVE_AUTHORITIES


class ObservabilityError(ValueError):
    """Raised when an observability or incident control must fail closed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class PreservationRecord:
    detection_at: str
    preserved_at: str
    elapsed_minutes: int
    raw_output_hash: str
    source_hash: str
    configuration_fingerprint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "detection_at": self.detection_at,
            "preserved_at": self.preserved_at,
            "elapsed_minutes": self.elapsed_minutes,
            "raw_output_hash": self.raw_output_hash,
            "source_hash": self.source_hash,
            "configuration_fingerprint": self.configuration_fingerprint,
        }


class SyntheticObservability:
    """An in-memory, deterministic observability and incident fixture."""

    def __init__(
        self,
        *,
        source_commit: str,
        config_fingerprint: str,
        environment: str = "p7.3-isolated",
        reviewer: str = "Kalaap Das",
    ) -> None:
        self.source_commit = source_commit
        self.config_fingerprint = config_fingerprint
        self.environment = environment
        self.reviewer = reviewer
        self.events: list[dict[str, Any]] = []
        self.event_ids: set[str] = set()
        self.alerts: dict[str, dict[str, Any]] = {}
        self.incidents: dict[str, dict[str, Any]] = {}
        self.retention_minutes = 60
        self.fail_closed = False

    @staticmethod
    def authorities() -> dict[str, bool]:
        return {authority: False for authority in LIVE_AUTHORITIES}

    @staticmethod
    def model_output_authorizes_execution(model_output: Mapping[str, Any]) -> bool:
        del model_output
        return False

    def _guard(self) -> None:
        if self.fail_closed:
            raise ObservabilityError("observability fixture is terminal fail-closed")

    def _event_unsigned(
        self,
        *,
        event_id: str,
        event_type: str,
        severity: str,
        timestamp: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "event_id": event_id,
            "event_type": event_type,
            "severity": severity,
            "timestamp": timestamp,
            "payload": dict(payload),
            "source_commit": self.source_commit,
            "config_fingerprint": self.config_fingerprint,
            "environment": self.environment,
            "synthetic_only": True,
            "external_action": False,
            "unauthorized_action": False,
            "live_credential": False,
            "live_authorities": self.authorities(),
            "reviewer": self.reviewer,
        }

    def emit_event(
        self,
        *,
        event_id: str,
        event_type: str,
        severity: str,
        timestamp: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._guard()
        if event_id in self.event_ids:
            raise ObservabilityError("duplicate event id")
        if self.events and timestamp < self.events[-1]["timestamp"]:
            raise ObservabilityError("out-of-order event")
        if severity not in {"info", "warning", "critical"}:
            raise ObservabilityError("invalid severity")
        event = self._event_unsigned(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=timestamp,
            payload=payload,
        )
        event["provenance_hash"] = _sha256(_canonical(event))
        event["event_hash"] = _sha256(_canonical(event))
        self.events.append(event)
        self.event_ids.add(event_id)
        return json.loads(_canonical(event))

    def verify_event(self, event: Mapping[str, Any]) -> bool:
        required = {
            "event_id", "event_type", "severity", "timestamp", "payload",
            "source_commit", "config_fingerprint", "environment", "synthetic_only",
            "external_action", "unauthorized_action", "live_credential",
            "live_authorities", "reviewer", "provenance_hash", "event_hash",
        }
        if not required.issubset(event):
            raise ObservabilityError("incomplete event")
        unsigned = dict(event)
        provenance = unsigned.pop("provenance_hash")
        recorded_hash = unsigned.pop("event_hash")
        if _sha256(_canonical(unsigned)) != provenance:
            raise ObservabilityError("provenance hash mismatch")
        unsigned["provenance_hash"] = provenance
        if _sha256(_canonical(unsigned)) != recorded_hash:
            raise ObservabilityError("event hash mismatch")
        if event["source_commit"] != self.source_commit or event["config_fingerprint"] != self.config_fingerprint:
            raise ObservabilityError("event binding mismatch")
        if event["environment"] != self.environment:
            raise ObservabilityError("environment mismatch")
        if event["synthetic_only"] is not True or event["external_action"] is not False:
            raise ObservabilityError("event is not synthetic-only")
        if event["unauthorized_action"] is not False or event["live_credential"] is not False:
            raise ObservabilityError("unsafe event flags")
        if event["live_authorities"] != self.authorities():
            raise ObservabilityError("live authority widening detected")
        return True

    def metric(self, name: str) -> dict[str, Any]:
        self._guard()
        if name == "critical_events":
            value = sum(event["severity"] == "critical" for event in self.events)
        elif name == "event_count":
            value = len(self.events)
        elif name == "warning_events":
            value = sum(event["severity"] == "warning" for event in self.events)
        else:
            raise ObservabilityError("unknown metric")
        return {
            "name": name,
            "value": value,
            "config_fingerprint": self.config_fingerprint,
            "environment": self.environment,
            "source_commit": self.source_commit,
        }

    def trigger_alert(self, *, alert_id: str, metric_name: str, threshold: int) -> dict[str, Any]:
        self._guard()
        if alert_id in self.alerts:
            raise ObservabilityError("duplicate alert")
        if threshold < 0:
            raise ObservabilityError("invalid threshold")
        metric = self.metric(metric_name)
        if metric["value"] < threshold:
            raise ObservabilityError("alert threshold not met")
        alert = {
            "alert_id": alert_id,
            "metric_name": metric_name,
            "threshold": threshold,
            "observed_value": metric["value"],
            "status": "TRIGGERED",
            "config_fingerprint": self.config_fingerprint,
            "external_action": False,
        }
        self.alerts[alert_id] = alert
        return dict(alert)

    def acknowledge_alert(self, *, alert_id: str, actor: str, model_output: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self._guard()
        if model_output is not None and self.model_output_authorizes_execution(model_output):
            raise ObservabilityError("model output cannot acknowledge")
        if actor != "synthetic-operator":
            raise ObservabilityError("unauthorized acknowledgement actor")
        if alert_id not in self.alerts:
            raise ObservabilityError("unknown alert")
        alert = self.alerts[alert_id]
        if alert["status"] != "TRIGGERED":
            raise ObservabilityError("alert is not awaiting acknowledgement")
        alert["status"] = "ACKNOWLEDGED"
        alert["acknowledged_by"] = actor
        return dict(alert)

    def open_incident(self, *, incident_id: str, severity: str) -> dict[str, Any]:
        self._guard()
        if incident_id in self.incidents:
            raise ObservabilityError("duplicate incident")
        mapping = {
            "info": ("operations", "ops-review", "monitor"),
            "warning": ("operations", "on-call", "investigate"),
            "critical": ("incident-commander", "executive-review", "freeze"),
        }
        if severity not in mapping:
            raise ObservabilityError("invalid incident severity")
        owner, escalation, stop_condition = mapping[severity]
        incident = {
            "incident_id": incident_id,
            "severity": severity,
            "owner": owner,
            "escalation_path": escalation,
            "stop_condition": stop_condition,
            "status": "OPEN",
            "external_action": False,
        }
        self.incidents[incident_id] = incident
        return dict(incident)

    def escalate_incident(self, *, incident_id: str, actor: str) -> dict[str, Any]:
        self._guard()
        if actor != "synthetic-operator":
            raise ObservabilityError("unauthorized escalation actor")
        if incident_id not in self.incidents:
            raise ObservabilityError("unknown incident")
        incident = self.incidents[incident_id]
        incident["status"] = "ESCALATED"
        incident["escalated_by"] = actor
        return dict(incident)

    def configure_retention(self, *, retention_minutes: int) -> int:
        self._guard()
        if retention_minutes < 15 or retention_minutes > 1440:
            raise ObservabilityError("retention outside approved bounds")
        self.retention_minutes = retention_minutes
        return retention_minutes

    def preserve_evidence(
        self,
        *,
        detection_at: str,
        preserved_at: str,
        elapsed_minutes: int,
        raw_output: bytes,
    ) -> PreservationRecord:
        self._guard()
        if elapsed_minutes < 0 or elapsed_minutes > 15:
            raise ObservabilityError("evidence preservation exceeded 15-minute limit")
        if preserved_at < detection_at:
            raise ObservabilityError("preservation precedes detection")
        source_hash = _sha256(_canonical({
            "source_commit": self.source_commit,
            "environment": self.environment,
        }))
        return PreservationRecord(
            detection_at=detection_at,
            preserved_at=preserved_at,
            elapsed_minutes=elapsed_minutes,
            raw_output_hash=_sha256(raw_output),
            source_hash=source_hash,
            configuration_fingerprint=self.config_fingerprint,
        )

    def inject_failure(self, control: str) -> None:
        if control not in {"acknowledgement", "escalation", "retention", "preservation"}:
            raise ObservabilityError("unknown injected failure")
        self.fail_closed = True
        raise ObservabilityError(f"injected {control} failure; terminal fail-closed")

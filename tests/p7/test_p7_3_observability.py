import json
import unittest

from kernel.p7.observability import ObservabilityError, SyntheticObservability
from kernel.p7.recovery import LIVE_AUTHORITIES


class TestP73Observability(unittest.TestCase):
    def setUp(self):
        self.obs = SyntheticObservability(
            source_commit="96b36bb", config_fingerprint="p7.3-config-a"
        )
        self.obs.emit_event(
            event_id="evt-001",
            event_type="heartbeat",
            severity="info",
            timestamp="2026-09-22T00:00:00Z",
            payload={"component": "synthetic-control"},
        )
        self.obs.emit_event(
            event_id="evt-002",
            event_type="incident-signal",
            severity="critical",
            timestamp="2026-09-22T00:01:00Z",
            payload={"component": "synthetic-control"},
        )

    def test_case_registry_has_32_cases(self):
        self.assertEqual(len(CASE_IDS), 32)
        self.assertEqual(len(set(CASE_IDS)), 32)

    def test_event_integrity_and_provenance_cases(self):
        event = self.obs.events[0]
        self.assertTrue(self.obs.verify_event(event))
        tampered = dict(event)
        tampered["payload"] = {"tampered": True}
        with self.assertRaises(ObservabilityError): self.obs.verify_event(tampered)
        with self.assertRaises(ObservabilityError):
            self.obs.emit_event(event_id="evt-001", event_type="duplicate", severity="info", timestamp="2026-09-22T00:02:00Z", payload={})
        with self.assertRaises(ObservabilityError):
            self.obs.emit_event(event_id="evt-003", event_type="late", severity="info", timestamp="2026-09-21T23:00:00Z", payload={})

    def test_metrics_and_alerting_cases(self):
        self.assertEqual(self.obs.metric("event_count")["value"], 2)
        self.assertEqual(self.obs.metric("critical_events")["value"], 1)
        alert = self.obs.trigger_alert(alert_id="alert-001", metric_name="critical_events", threshold=1)
        self.assertEqual(alert["status"], "TRIGGERED")
        self.assertEqual(self.obs.acknowledge_alert(alert_id="alert-001", actor="synthetic-operator")["status"], "ACKNOWLEDGED")
        with self.assertRaises(ObservabilityError):
            self.obs.trigger_alert(alert_id="alert-002", metric_name="critical_events", threshold=3)

    def test_incident_classification_and_escalation_cases(self):
        incident = self.obs.open_incident(incident_id="inc-001", severity="critical")
        self.assertEqual(incident["owner"], "incident-commander")
        self.assertEqual(incident["stop_condition"], "freeze")
        self.assertEqual(self.obs.escalate_incident(incident_id="inc-001", actor="synthetic-operator")["status"], "ESCALATED")
        with self.assertRaises(ObservabilityError):
            self.obs.escalate_incident(incident_id="inc-001", actor="model-output")

    def test_retention_and_preservation_cases(self):
        self.assertEqual(self.obs.configure_retention(retention_minutes=60), 60)
        evidence = self.obs.preserve_evidence(
            detection_at="2026-09-22T00:00:00Z",
            preserved_at="2026-09-22T00:10:00Z",
            elapsed_minutes=10,
            raw_output=b"synthetic-output",
        )
        self.assertEqual(evidence.elapsed_minutes, 10)
        with self.assertRaises(ObservabilityError):
            self.obs.configure_retention(retention_minutes=5)
        with self.assertRaises(ObservabilityError):
            self.obs.preserve_evidence(
                detection_at="2026-09-22T00:00:00Z",
                preserved_at="2026-09-22T00:20:00Z",
                elapsed_minutes=20,
                raw_output=b"late",
            )

    def test_authority_and_model_denial_cases(self):
        self.assertEqual(set(self.obs.authorities()), set(LIVE_AUTHORITIES))
        self.assertTrue(all(value is False for value in self.obs.authorities().values()))
        self.assertFalse(self.obs.model_output_authorizes_execution({"approve": True, "ack": True}))
        event = dict(self.obs.events[0])
        event["live_authorities"] = {key: True for key in LIVE_AUTHORITIES}
        with self.assertRaises(ObservabilityError): self.obs.verify_event(event)

    def test_injected_failure_paths_are_fail_closed(self):
        before = dict(self.obs.__dict__)
        for control in ("acknowledgement", "escalation", "retention", "preservation"):
            fresh = SyntheticObservability(source_commit="96b36bb", config_fingerprint="p7.3-config-a")
            with self.assertRaises(ObservabilityError): fresh.inject_failure(control)
            self.assertTrue(fresh.fail_closed)
            self.assertNotEqual(fresh.__dict__, before) if control == "acknowledgement" else None

    def test_event_binding_rejects_wrong_source_and_environment(self):
        event = dict(self.obs.events[0])
        event["source_commit"] = "wrong"
        with self.assertRaises(ObservabilityError): self.obs.verify_event(event)
        event = dict(self.obs.events[0])
        event["environment"] = "wrong-env"
        with self.assertRaises(ObservabilityError): self.obs.verify_event(event)

    def test_no_external_side_effects(self):
        for event in self.obs.events:
            self.assertTrue(event["synthetic_only"])
            self.assertFalse(event["external_action"])
            self.assertFalse(event["unauthorized_action"])
            self.assertFalse(event["live_credential"])


CASE_IDS = (
    [f"P7.3.EVENT_INTEGRITY.provenance.{i:03d}" for i in range(1, 9)]
    + [f"P7.3.METRICS_ALERTING.threshold.{i:03d}" for i in range(1, 9)]
    + [f"P7.3.INCIDENT_ESCALATION.severity.{i:03d}" for i in range(1, 7)]
    + [f"P7.3.RETENTION_PRESERVATION.evidence.{i:03d}" for i in range(1, 7)]
    + [f"P7.3.AUTHORITY_DENIAL.negative.{i:03d}" for i in range(1, 5)]
)


if __name__ == "__main__":
    unittest.main()

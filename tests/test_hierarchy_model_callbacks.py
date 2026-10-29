"""Model decisions remain bounded and cannot directly issue signed authority."""
import json
import unittest

from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.venture_workflow import hashed


class RoleCallbackTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {}
        self.item = dict(state="WORKER_PENDING", mode="PREPARATION_ONLY",
                         scope=dict(tasks=["Document testable tenant isolation"],
                                    budget_units=5), used_units=0,
                         scope_hash="f" * 64, revision=2, evidence={})
        self.provider_calls = []

    def store(self, name, wire):
        self.evidence[name] = wire

    def provider(self, request, tools):
        self.assertEqual(tools, ())
        self.provider_calls.append(request)
        return dict(decision=dict(content=json.dumps(self.decision)), tool_call=None)

    def test_worker_content_is_digest_bound_and_has_no_execution_authority(self):
        self.decision = dict(action="submit", units=2,
                             explanation="Unit tests and constraints documented",
                             deliverable="Tenant A cannot read Tenant B records, with evidence")
        callback = ModelRoleCallback(role="worker", provider=self.provider,
                                     artifact_store=self.store, artifact_load=self.evidence.__getitem__)
        result = callback(self.item)
        self.assertEqual(result["action"], "submit")
        self.assertEqual(result["payload"]["units"], 2)
        ref = result["evidence"][0]
        import hashlib
        self.assertEqual(ref["sha256"], hashlib.sha256(self.evidence[ref["ref"]]).hexdigest())
        self.assertEqual(self.provider_calls[0]["opportunity"]["permitted_actions"], ["submit"])

    def test_wrong_role_action_or_tool_call_denied_without_artifact(self):
        self.decision = dict(action="ceo_approve", units=1,
                             explanation="Should never approve", deliverable="No")
        worker = ModelRoleCallback(role="worker", provider=self.provider,
                                   artifact_store=self.store, artifact_load=self.evidence.__getitem__)
        with self.assertRaises(ValueError):
            worker(self.item)
        with self.assertRaises(ValueError):
            ModelRoleCallback(role="ceo", provider=self.provider,
                              artifact_store=self.store, artifact_load=self.evidence.__getitem__)(self.item)
        self.assertEqual(self.evidence, {})

    def test_manager_improvement_requires_nonempty_evidence(self):
        self.item["state"] = "MANAGER_REVIEW"
        self.decision = dict(action="improve", units=0,
                             explanation="Missing restart test", deliverable="Add restart evidence")
        result = ModelRoleCallback(role="manager", provider=self.provider,
                                   artifact_store=self.store, artifact_load=self.evidence.__getitem__)(self.item)
        self.assertEqual(result["action"], "improve")
        self.assertNotIn("units", result["payload"])

    def test_manager_receives_verified_worker_deliverable(self):
        self.decision = dict(action="submit", units=1,
                             explanation="First version", deliverable="Specific test proof")
        worker = ModelRoleCallback(role="worker", provider=self.provider,
                                   artifact_store=self.store, artifact_load=self.evidence.__getitem__)
        submission = worker(self.item)
        self.item["state"] = "MANAGER_REVIEW"
        self.item["last_command"] = dict(evidence=submission["evidence"])
        self.decision = dict(action="improve", units=0,
                             explanation="Need failure mode evidence", deliverable="Add rollback check")
        reviewer = ModelRoleCallback(role="manager", provider=self.provider,
                                     artifact_store=self.store, artifact_load=self.evidence.__getitem__)
        reviewer(self.item)
        self.assertEqual(self.provider_calls[-1]["opportunity"]["existing_evidence"][0]["deliverable"],
                         "Specific test proof")
        ref = submission["evidence"][0]
        self.evidence[ref["ref"]] = b"tampered"
        with self.assertRaises(ValueError):
            reviewer(self.item)

    def test_bad_units_and_unauthorized_operational_modes_denied(self):
        self.decision = dict(action="submit", units=True,
                             explanation="Untrusted", deliverable="No")
        worker = ModelRoleCallback(role="worker", provider=self.provider,
                                   artifact_store=self.store, artifact_load=self.evidence.__getitem__)
        with self.assertRaises(ValueError):
            worker(self.item)
        self.item["mode"] = "LIVE"
        with self.assertRaises(ValueError):
            worker(self.item)


if __name__ == "__main__":
    unittest.main()

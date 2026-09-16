import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from kernel.broker import Broker, BrokerState


def req(**overrides):
    base = {
        "request_id": "00000000-0000-4000-8000-000000000001",
        "agent_id": "agent-a", "venture_id": "venture-a",
        "capability": "sandbox.purchase", "plan_id": "plan-1",
        "requested_constraints": {"ttl_seconds": 300},
        "provenance": {"taint_status": "unknown", "evidence_ids": []},
        "action_graph": [{"action": "purchase", "amount": 100, "counterparty_key": "beneficiary-1"}],
        "requested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "idempotency_key": "idem-1",
    }
    base.update(overrides)
    return base


class CapabilityBrokerTests(unittest.TestCase):
    def broker(self, state=None, **kwargs):
        return Broker(state=state or BrokerState(), policy_evaluator=lambda _: True, **kwargs)

    def test_schemas_are_parseable_and_frozen_fields_present(self):
        for name in ("capability-request", "capability-decision", "capability-grant"):
            data = json.loads((Path(__file__).parents[1] / "schemas" / (name + ".schema.json")).read_text())
            self.assertIn("required", data)
        request = json.loads((Path(__file__).parents[1] / "schemas/capability-request.schema.json").read_text())
        self.assertIn("provenance", request["required"])

    def test_cap_001_no_ambient_credentials(self):
        b = self.broker()
        self.assertIsNotNone(b.check_cap_001(req(access_token="never")))
        self.assertIsNone(b.check_cap_001(req()))

    def test_cap_002_velocity_per_agent_capability(self):
        t = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        state = BrokerState(requests=[req(request_id=f"00000000-0000-4000-8000-{i:012d}", requested_at=t) for i in range(3)])
        self.assertIsNotNone(self.broker(state).check_cap_002(req()))

    def test_cap_003_cross_counterparty_rolling_aggregation(self):
        state = BrokerState(requests=[req(request_id="00000000-0000-4000-8000-000000000002",
                                           action_graph=[{"action": "purchase", "amount": 700, "counterparty_key": "b-2"}])])
        self.assertIsNotNone(self.broker(state).check_cap_003(req(action_graph=[{"action": "purchase", "amount": 400, "counterparty_key": "b-3"}])))

    def test_cap_004_structuring(self):
        b = self.broker(aggregate_limit=5000)
        actions = [{"action": "purchase", "amount": 400, "counterparty_key": f"b-{i}"} for i in range(3)]
        self.assertIsNotNone(b.check_cap_004(req(action_graph=actions)))

    def test_cap_005_ultimate_beneficiary_not_vendor_name(self):
        b = self.broker()
        self.assertIsNotNone(b.check_cap_005(req(action_graph=[{"action": "purchase", "amount": 10, "vendor_name": "same-platform"}])))
        self.assertIsNone(b.check_cap_005(req()))

    def test_cap_006_novelty_and_cap_007_baseline(self):
        state = BrokerState(baselines={("agent-a", "sandbox.purchase"): 50})
        b = self.broker(state)
        self.assertIsNotNone(b.check_cap_006(req()))
        state.known_capabilities.add(("agent-a", "sandbox.purchase"))
        self.assertIsNotNone(b.check_cap_007(req(action_graph=[{"action": "purchase", "amount": 101, "counterparty_key": "b"}])))

    def test_cap_008_escalates_not_flat_allows(self):
        b = self.broker()
        decision = b.evaluate(req())
        self.assertEqual(decision["decision"], "escalate")
        self.assertIsNone(decision["grant"])

    def test_cap_009_composite_confused_deputy_chain_denied(self):
        b = self.broker()
        b.state.known_capabilities.add(("agent-a", "sandbox.purchase"))
        for i, action in enumerate(("create_file", "upload", "generate_public_link")):
            b.evaluate(req(request_id=f"00000000-0000-4000-8000-{i+2:012d}",
                           action_graph=[{"action": action, "amount": 0}]))
        denied = b.evaluate(req(request_id="00000000-0000-4000-8000-000000000099",
                                action_graph=[{"action": "send_message", "amount": 0}]))
        self.assertEqual(denied["decision"], "deny")
        self.assertTrue(any(x.startswith("CAP-009") for x in denied["reasons"]))

    def test_cap_010_delegation_beyond_policy_denied(self):
        decision = self.broker().evaluate(req(requested_constraints={"ttl_seconds": 300, "delegable": True}))
        self.assertEqual(decision["decision"], "deny")
        self.assertTrue(any(x.startswith("CAP-010") for x in decision["reasons"]))

    def test_cap_011_never_standing_and_single_use(self):
        b = self.broker()
        denied = b.evaluate(req(requested_constraints={"ttl_seconds": 0}))
        self.assertEqual(denied["decision"], "deny")
        state = BrokerState(known_capabilities={("agent-a", "sandbox.purchase")})
        b = self.broker(state)
        allowed = b.evaluate(req(request_id="00000000-0000-4000-8000-000000000010"))
        self.assertEqual(allowed["decision"], "allow")
        grant_id = allowed["grant"]["grant_id"]
        self.assertTrue(b.consume(grant_id))
        self.assertFalse(b.consume(grant_id))
        self.assertTrue(b.revoke(grant_id))
        self.assertFalse(b.consume(grant_id))

    def test_opa_outage_denies_closed(self):
        b = Broker(policy_evaluator=lambda _: False)
        b.state.known_capabilities.add(("agent-a", "sandbox.purchase"))
        decision = b.evaluate(req())
        self.assertEqual(decision["decision"], "deny")
        self.assertIsNone(decision["grant"])


if __name__ == "__main__":
    unittest.main()

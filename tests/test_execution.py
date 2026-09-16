import unittest
from datetime import datetime, timedelta, timezone

from kernel.execution.execution_service import ExecutionDenied, ExecutionResult, ExecutionService, Lease


class FakeLeaseProvider:
    def __init__(self, value="synthetic-secret"):
        self.value = value

    def issue(self, service):
        return Lease(self.value, "lease-1", datetime.now(timezone.utc) + timedelta(seconds=60))


def adapter(secret, payload):
    assert secret == "synthetic-secret"
    assert payload == {"amount": 1}
    return ExecutionResult("req-1", "ok", "provider-1", {"accepted": True})


class ExecutionServiceTests(unittest.TestCase):
    def test_agent_cannot_reach_execution_service(self):
        service = ExecutionService(FakeLeaseProvider(), {"synthetic": adapter})
        with self.assertRaises(ExecutionDenied):
            service.execute(request_id="req-1", service="synthetic", payload={}, broker_approved=True, caller="agent:ceo")

    def test_execution_returns_result_without_secret(self):
        service = ExecutionService(FakeLeaseProvider(), {"synthetic": adapter})
        result = service.execute(request_id="req-1", service="synthetic", payload={"amount": 1}, broker_approved=True, caller="broker")
        envelope = result.as_agent_result()
        self.assertEqual(envelope, {"request_id": "req-1", "status": "ok", "provider_ref": "provider-1", "data": {"accepted": True}})
        self.assertNotIn("synthetic-secret", repr(envelope))

    def test_unapproved_or_unknown_execution_is_denied(self):
        service = ExecutionService(FakeLeaseProvider(), {"synthetic": adapter})
        with self.assertRaises(ExecutionDenied):
            service.execute(request_id="req-1", service="synthetic", payload={}, broker_approved=False, caller="broker")
        with self.assertRaises(ExecutionDenied):
            service.execute(request_id="req-1", service="other", payload={}, broker_approved=True, caller="broker")


if __name__ == "__main__":
    unittest.main()

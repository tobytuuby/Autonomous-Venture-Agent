"""The deployment gate must not confuse source reconstruction with acceptance."""
import unittest
from scripts.ceo_stage6_deployment_gate import blockers


class CEOStage6GateTests(unittest.TestCase):
    def test_installed_legacy_broker_is_denied(self):
        result = blockers("", "def do_GET(self): pass", "")
        self.assertIn("INSTALLED_BROKER_REJECTS_TRACKED_CEO_RESERVATION", result)
        self.assertIn("NO_EXISTING_READ_ONLY_CEO_SESSION_AND_CALL_PROOF_API", result)
        self.assertIn("BROKER_ENTRYPOINT_HAS_NO_CEO_EXECUTION_BINDING", result)

    def test_source_capabilities_cannot_grant_production_acceptance(self):
        result = blockers("CONTROL_LEDGER_V1",
            "def do_GET(self):\n exchange_sessions = remote_reservations",
            'execute_reserved(role="ceo")')
        self.assertIn("ACTIVE_PROCESS_AND_PENDING_WORK_ISOLATION_NOT_PROVEN", result)
        self.assertIn("CURRENT_INSTALLED_AND_LOADED_BYTES_NOT_ATTESTED", result)
        self.assertIn("CEO_LOCAL_AUTHORITY_BINDING_NOT_PROVEN", result)

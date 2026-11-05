"""Stage6 negative recovery proofs using independent synthetic broker ledgers."""
import json
import sqlite3
import unittest

from agents.ceo.ceo_broker import PROOF_PATH, EXECUTE_PATH
from agents.ceo.escalation_inbox import canonical
from tests import test_ceo_broker as fixture


class Stage6ResumeSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CEOBrokerTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixture.CEOBrokerTests.tearDownClass()

    def setUp(self):
        self.fx = fixture.CEOBrokerTests(methodName="runTest")
        self.addCleanup(self.fx.doCleanups)
        self.fx.setUp()
        self.fx.pending()
        self.fx.reserve()

    def corrupt_synthetic_execution(self, status, response):
        # Deliberately impossible/future database contents. Only this test's
        # generated ledger is altered, never production or a shared fixture.
        with sqlite3.connect(self.fx.authority / "resources.sqlite") as db:
            db.execute("""CREATE TABLE IF NOT EXISTS remote_executions(
                identity TEXT PRIMARY KEY, request TEXT NOT NULL,
                response TEXT, status TEXT NOT NULL
                CHECK(status IN ('PENDING','COMPLETE')))""")
            db.execute("PRAGMA ignore_check_constraints=ON")
            db.execute("""INSERT INTO remote_executions
                SELECT identity, ?, ?, ? FROM remote_reservations WHERE request=?""",
                (canonical(self.fx.payload), response, status,
                 canonical(self.fx.payload["reservation"])))

    def assert_held_without_effects(self, scenario):
        before = self.fx.ledger_bytes()
        counts = self.fx.counts()
        calls = len(self.fx.models["ceo"].calls)
        # Reopen and verify signed lineage, then attempt recovery twice.
        self.fx.reopen(self.fx.original_state)
        for _ in range(2):
            for path in (PROOF_PATH, EXECUTE_PATH):
                self.assertEqual(self.fx.wire("other", path, self.fx.payload)[0], 400)
            with self.assertRaises(ValueError):
                self.fx.resume()
            self.assertEqual(self.fx.ledger_bytes(), before)
            self.assertEqual(self.fx.counts(), counts)
            self.assertEqual(self.fx.state(), self.fx.original_state)
            self.fx.reopen(self.fx.original_state)
        self.assertEqual(len(self.fx.models["ceo"].calls), calls)
        print(canonical(dict(scenario=scenario, outcome="HOLD",
              ledger="BYTE_IDENTICAL", signed_lineage="VERIFIED",
              additional_provider_calls=0, additional_charges=0)), flush=True)

    def test_unknown_execution_status_never_retries(self):
        self.corrupt_synthetic_execution("UNKNOWN", None)
        self.assert_held_without_effects("UNKNOWN_PROVIDER_STATUS")

    def test_pending_with_response_is_conflicting_not_complete(self):
        self.corrupt_synthetic_execution("PENDING", "{}")
        self.assert_held_without_effects("CONFLICTING_PENDING_RESPONSE")

    def test_complete_without_response_never_retries(self):
        self.corrupt_synthetic_execution("COMPLETE", None)
        self.assert_held_without_effects("COMPLETE_RESPONSE_MISSING")

    def test_outstanding_charge_without_reservation_never_retries(self):
        with sqlite3.connect(self.fx.authority / "resources.sqlite") as db:
            db.execute("DELETE FROM remote_reservations WHERE request=?",
                       (canonical(self.fx.payload["reservation"]),))
        self.assert_held_without_effects("OUTSTANDING_ORPHAN_CHARGE")

    def test_exact_charged_unstarted_slot_resumes_once(self):
        counts = self.fx.counts()
        calls = len(self.fx.models["ceo"].calls)
        self.fx.reopen(self.fx.original_state)
        self.assertEqual(self.fx.client().ceo_proof(self.fx.payload)["execution_status"],
                         "NOT_STARTED")
        packet = self.fx.resume()
        self.assertEqual(packet["state"], "COMPLETE")
        completed = self.fx.ledger_bytes()
        self.assertEqual(self.fx.resume(), packet)
        self.assertEqual(self.fx.ledger_bytes(), completed)
        self.assertEqual(len(self.fx.models["ceo"].calls), calls + 1)
        self.assertEqual(self.fx.counts()["reservations"], counts["reservations"])
        self.assertEqual(self.fx.state(), self.fx.original_state)
        self.fx.reopen(self.fx.original_state)
        print(canonical(dict(scenario="EXACT_CHARGED_UNSTARTED_SLOT",
              outcome="COMPLETE_REUSED", additional_provider_calls=1,
              additional_charges=0, signed_lineage="VERIFIED")), flush=True)

"""CEO restart evidence uses private temporary broker ledgers and fake models only."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from agents.ceo import service_identity
from agents.ceo.ceo_research_review import review
from agents.ceo.escalation_inbox import ROOT, canonical
from agents.ceo.hierarchy_providers import RecoveryImpossible
from agents.ceo.provider_gateway import execute_reserved
from agents.ceo.provider_reservation import reserve_exchange
from agents.ceo.venture_workflow import hashed
from tests.test_ceo_research_review import FakeModel


class CEOPendingRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.authority = self.root / "authority"
        self.authority.mkdir(mode=0o700)
        self.patch = patch.object(service_identity, "AUTHORITY_DIRECTORY", self.authority)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.write(self.authority / "authority.json",
                   dict(enabled=True, epoch=1, revoked=[]))
        self.policy = dict(domain="preparation-exchange-usage-v1", enabled=True, epoch=1,
            roles={role: dict(actor_id="service-" + role,
                endpoint="https://fixture.invalid/v1", model="gpt-6-sol")
                for role in ("ceo", "manager")},
            maximum_requests=4, maximum_output_tokens=512)
        self.policy_path = self.authority / "exchange-usage-policy.json"
        self.write(self.policy_path, self.policy)
        seed = Ed25519PrivateKey.generate()
        (self.root / "seed").write_bytes(seed.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        self.raw = canonical(dict(role="worker", action="submit",
            deliverable="Studio operators use spreadsheets for stock.",
            explanation="Internal desk hypothesis only.")).encode()
        import hashlib
        sha = hashlib.sha256(self.raw).hexdigest()
        self.flow = "research-" + "e" * 24
        self.state = dict(id=self.flow, venture_id=self.flow, state="CEO_REVIEW",
            mode="PREPARATION_ONLY", operational_authority=False,
            external_actions_allowed=False, execution_performed=False, money_released=False,
            scope=dict(tasks=["Desk research only"]), scope_hash="scope",
            evidence={"preparation-" + sha: sha})
        self.context = dict(session_id=self.flow, venture_id=self.flow,
            ceo_id="service-ceo", manager_id="service-manager",
            objective="Desk research only", rounds=1)
        self.config = dict(role="ceo", actor_id="service-ceo",
            signing_key=str(self.root / "seed"), state_dir=str(self.root / "state"),
            policy=str(self.policy_path), context=self.context)
        self.client = Mock()
        self.client.load.return_value = self.raw
        self.client.read.side_effect = lambda flow: self.state if flow == self.flow else None
        self.client._request.side_effect = lambda method, path, data: reserve_exchange(
            data, actor="service-ceo", role="ceo")
        initial = FakeModel()
        with patch("agents.ceo.ceo_research_review.preserve_provider_intent",
                   side_effect=OSError("isolated crash before capture")):
            with self.assertRaises(OSError):
                review(self.config, self.state, self.client, initial)
        self.request = initial.last_request
        self.path = self.root / "research-reviews" / (self.flow + ".json")
        self.pending = self.path.read_bytes()
        self.dbpath = self.root / "state" / "research-review-inference.sqlite"
        self.dbpath.parent.mkdir()
        self.identity = "ceo-" + hashed(self.state)[:50]
        self.attempt = "a" * 64
        with sqlite3.connect(self.dbpath) as db:
            db.execute("CREATE TABLE calls(identity TEXT PRIMARY KEY, request TEXT NOT NULL, response TEXT, attempt TEXT NOT NULL)")
            db.execute("INSERT INTO calls VALUES(?,?,NULL,?)",
                       (self.identity, canonical(self.request), self.attempt))
        self.reservation = dict(context=self.context, role="ceo", actor="service-ceo",
            identity=self.identity, attempt=self.attempt, request_sha256=hashed(self.request),
            policy=self.policy, endpoint="https://fixture.invalid/v1", model="gpt-6-sol",
            execution_mode="CONTROL_LEDGER_V1")
        # The daemon establishes this session before any CEO review intent.
        bootstrap = dict(self.reservation, identity="research-session-fixture")
        del bootstrap["execution_mode"]
        self.reserve(bootstrap)
        self.model = FakeModel()
        self.model.endpoint = "https://fixture.invalid/v1"

    def write(self, path, value):
        path.write_text(canonical(value))
        path.chmod(0o600)

    def reserve(self, payload=None):
        return reserve_exchange(payload or self.reservation, actor="service-ceo", role="ceo")

    def execute(self, probe=False, reservation=None, role="ceo"):
        payload = dict(reservation=reservation or self.reservation, request=self.request)
        if probe:
            payload["reconcile_only"] = True
        return execute_reserved(payload, actor="service-ceo", role=role,
            provider=self.model, hierarchy=SimpleNamespace(state=self.client.read))

    def recover(self):
        with patch("agents.ceo.venture_exercise.configured_provider", return_value=self.model):
            return review(self.config, self.state, self.client)

    def charges(self):
        with sqlite3.connect(self.authority / "resources.sqlite") as db:
            return db.execute("SELECT COUNT(*),SUM(tokens) FROM reservations").fetchone()

    def test_reserved_unexecuted_same_identity_attempt_authorization_only(self):
        self.reserve()
        self.assertEqual(self.execute(True)["reconciliation"], "NOT_STARTED")
        self.assertEqual(self.model.calls, 0)
        result = self.recover()
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(self.recover(), result)
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(self.charges(), (2, 1024))
        with sqlite3.connect(self.dbpath) as db:
            row = db.execute("SELECT identity,request,attempt,response FROM calls").fetchone()
        self.assertEqual(row[:3], (self.identity, canonical(self.request), self.attempt))
        self.assertIsNotNone(row[3])
        intent = json.loads(self.path.with_name(self.path.stem + ".provider-intent.json").read_text())
        self.assertEqual(intent["pending"], json.loads(self.pending))

    def test_no_original_reservation_proves_original_was_never_executed(self):
        self.client._request.side_effect = AssertionError("use atomic broker reconciliation")
        self.assertEqual(self.recover()["state"], "COMPLETE")
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(self.charges(), (2, 1024))

    def test_executed_response_retrieved_without_configuring_or_calling_provider(self):
        self.reserve()
        original = self.execute()
        with patch("agents.ceo.venture_exercise.configured_provider",
                   side_effect=AssertionError("paid replay forbidden")):
            result = review(self.config, self.state, self.client)
        self.assertEqual(result["packet"]["provider_response_sha256"], hashed(original))
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(self.charges(), (2, 1024))

    def test_ambiguous_execution_explicitly_blocks_without_retry(self):
        self.reserve()
        self.model.mutate = lambda result: (_ for _ in ()).throw(OSError("lost response"))
        with self.assertRaises(OSError):
            self.execute()
        self.assertEqual(self.execute(True)["reconciliation"], "PENDING")
        before = self.dbpath.read_bytes()
        with self.assertRaisesRegex(RecoveryImpossible, "PROVIDER_EXECUTION_AMBIGUOUS"):
            self.recover()
        self.assertEqual(self.path.read_bytes(), self.pending)
        self.assertEqual(self.dbpath.read_bytes(), before)
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(self.charges(), (2, 1024))

    def test_legacy_reservation_cannot_be_upgraded_into_nonexecution_proof(self):
        legacy = dict(self.reservation)
        del legacy["execution_mode"]
        self.reserve(legacy)
        with self.assertRaisesRegex(RecoveryImpossible, "CEO_RESERVATION_PROOF_REQUIRED"):
            self.recover()
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(self.path.read_bytes(), self.pending)
        self.assertEqual(self.charges(), (2, 1024))

    def test_missing_ledger_or_session_is_not_nonexecution_proof(self):
        ledger = self.authority / "resources.sqlite"
        with sqlite3.connect(ledger) as db:
            db.execute("DELETE FROM exchange_sessions")
        with self.assertRaisesRegex(RecoveryImpossible, "CEO_RESERVATION_PROOF_REQUIRED"):
            self.recover()
        ledger.unlink()
        with self.assertRaisesRegex(RecoveryImpossible, "CEO_RESERVATION_PROOF_REQUIRED"):
            self.recover()
        self.assertFalse(ledger.exists())
        self.assertEqual(self.model.calls, 0)

    def test_quota_exhaustion_allows_exact_reserved_call_but_no_new_slot(self):
        self.reserve()
        self.reserve(dict(self.reservation, identity="ceo-other-one"))
        self.reserve(dict(self.reservation, identity="ceo-other-two"))
        self.assertEqual(self.recover()["state"], "COMPLETE")
        self.assertEqual(self.charges(), (4, 2048))
        self.assertEqual(self.model.calls, 1)

    def test_quota_exhaustion_blocks_unreserved_intent_without_provider(self):
        for index in range(3):
            self.reserve(dict(self.reservation, identity="ceo-other-" + str(index)))
        with self.assertRaisesRegex(ValueError, "ceiling"):
            self.recover()
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(self.charges(), (4, 2048))

    def test_changed_attempt_identity_context_or_policy_cannot_reconcile(self):
        self.reserve()
        for field, value in (
                ("attempt", "b" * 64), ("identity", "ceo-other"),
                ("context", dict(self.context, rounds=2)),
                ("policy", dict(self.policy, maximum_requests=5))):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.execute(True, dict(self.reservation, **{field: value}))
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(self.charges(), (2, 1024))

    def test_revoked_authority_blocks_unstarted_and_completed_replay(self):
        self.reserve()
        for complete in (False, True):
            if complete:
                self.write(self.authority / "authority.json", dict(enabled=True, epoch=1, revoked=[]))
                self.execute()
            self.write(self.authority / "authority.json",
                       dict(enabled=True, epoch=1, revoked=["service-ceo"]))
            with self.assertRaisesRegex(ValueError, "revoked"):
                self.recover()
        self.assertEqual(self.model.calls, 1)

    def test_manager_execution_entrypoint_cannot_select_ceo_role_from_body(self):
        self.reserve()
        with self.assertRaises(ValueError):
            self.execute(role="manager")
        self.assertEqual(self.model.calls, 0)

    def test_future_venture_restart_after_reservation_and_after_execution(self):
        # Fresh normal review writes the mode-bound reservation. Crash exactly
        # after its durable reservation, then restart through the real review API.
        self.flow = "research-" + "f" * 24
        self.state = dict(self.state, id=self.flow, venture_id=self.flow)
        self.context = dict(self.context, session_id=self.flow, venture_id=self.flow)
        self.config = dict(self.config, context=self.context, state_dir=str(self.root / "future"))
        bootstrap = dict(self.reservation, context=self.context, identity="future-session")
        del bootstrap["execution_mode"]
        self.reserve(bootstrap)
        self.client._request.side_effect = lambda method, path, data: (
            self.reserve(data), (_ for _ in ()).throw(OSError("crash after reserve")))[1]
        with patch("agents.ceo.venture_exercise.configured_provider", return_value=self.model):
            with self.assertRaises(OSError):
                review(self.config, self.state, self.client)
        self.client._request.reset_mock()
        self.client._request.side_effect = AssertionError("restart must use existing reservation")
        result = self.recover()
        self.assertEqual(self.recover(), result)
        self.assertEqual(result["state"], "COMPLETE")
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(self.charges(), (3, 1536))

    def test_split_local_and_broker_authority_blocks_before_remote_charge(self):
        # A new synthetic venture, never a legacy pending outcome. Its broker
        # session exists, but the CEO cannot access that ledger locally.
        original_checkpoint = self.path.read_bytes()
        original_inference = self.dbpath.read_bytes()
        self.flow = "research-" + "d" * 24
        self.state = dict(self.state, id=self.flow, venture_id=self.flow)
        self.context = dict(self.context, session_id=self.flow, venture_id=self.flow)
        self.config = dict(self.config, context=self.context,
                           state_dir=str(self.root / "split-future"))
        broker = self.root / "broker-authority"
        broker.mkdir(mode=0o700)
        for name in ("authority.json", "exchange-usage-policy.json"):
            self.write(broker / name, json.loads((self.authority / name).read_text()))
        with patch.object(service_identity, "AUTHORITY_DIRECTORY", broker):
            bootstrap = dict(self.reservation, context=self.context, identity="split-session")
            del bootstrap["execution_mode"]
            self.reserve(bootstrap)
        def remote(method, path, data):
            with patch.object(service_identity, "AUTHORITY_DIRECTORY", broker):
                return self.reserve(data)
        self.client._request.side_effect = remote
        local_ledger = (self.authority / "resources.sqlite").read_bytes()
        self.client._request.reset_mock()
        with self.assertRaisesRegex(RecoveryImpossible, "CEO_LOCAL_LEDGER_BINDING_REQUIRED"):
            self.recover()
        self.client._request.assert_not_called()
        self.assertEqual(self.model.calls, 0)
        self.assertEqual((self.authority / "resources.sqlite").read_bytes(), local_ledger)
        self.assertEqual(self.path.read_bytes(), original_checkpoint)
        self.assertEqual(self.dbpath.read_bytes(), original_inference)
        with sqlite3.connect(broker / "resources.sqlite") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0], 1)

    def test_local_session_preflight_is_readonly_and_rejects_changed_binding(self):
        from agents.ceo.provider_reservation import require_ceo_session
        path = self.authority / "resources.sqlite"
        original = path.read_bytes()
        require_ceo_session(self.context, self.policy)
        for context, policy in (
                (dict(self.context, session_id="missing-synthetic-session"), self.policy),
                (dict(self.context, objective="Changed synthetic scope"), self.policy),
                (self.context, dict(self.policy, maximum_requests=5))):
            with self.subTest(context=context), self.assertRaisesRegex(
                    RecoveryImpossible, "CEO_LOCAL_LEDGER_BINDING_REQUIRED"):
                require_ceo_session(context, policy)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.model.calls, 0)

    def test_pending_checkpoint_hash_and_prompt_change_still_refused(self):
        self.reserve()
        pending = json.loads(self.pending)
        pending["request_hash"] = "0" * 64
        self.path.write_text(canonical(pending))
        with self.assertRaisesRegex(ValueError, "pending request mismatch"):
            self.recover()
        self.assertEqual(self.model.calls, 0)


if __name__ == "__main__":
    unittest.main()

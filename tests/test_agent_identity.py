"""Supplemental adversarial identity evidence; ephemeral keys and mock inference."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import sys
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import uuid
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo import service_identity as identity
from agents.ceo.escalation_inbox import ROOT, canonical
from agents.ceo.provider_dispatch import load_runtime
from agents.ceo.scheduled_exercise import write_json


class AgentIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "authority"
        self.patch = patch.object(identity, "AUTHORITY_DIRECTORY", self.directory)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.keys = identity.preparation_authority()
        self.context = dict(run_id="TEST", assignment_hash="a" * 64,
                            implementation="b" * 64, epoch=1)
        self.detail = dict(task_id="development-1", response_hash="c" * 64)

    def signed(self, action="worker_submission", detail=None, worker="development-1"):
        return self.keys.attest(action, detail or self.detail, self.context, 1, "GENESIS", worker=worker)

    def verify(self, value, action="worker_submission", detail=None, context=None, sequence=1, previous="GENESIS"):
        self.keys.verify_attestation(value, action, detail or self.detail,
                                     context or self.context, sequence, previous)

    def test_segregated_worker_manager_ceo_keys_and_stable_restart(self):
        first = self.signed()
        other = self.keys.attest("worker_submission", dict(task_id="testing-1"), self.context,
                                 1, "GENESIS", worker="testing-1")
        manager = self.signed("manager_signoff")
        ceo = self.signed("ceo_final_review")
        self.assertEqual(len({v["public_key"] for v in (first, other, manager, ceo)}), 4)
        self.verify(first)
        self.keys = identity.preparation_authority()
        self.verify(first)

    def test_cross_worker_impersonation_denied(self):
        self.verify(self.signed())
        with self.assertRaises(ValueError):
            self.verify(self.signed(worker="testing-1"))

    def test_worker_cannot_sign_manager_and_manager_cannot_sign_ceo(self):
        for target, signer in (("manager_signoff", "worker-development-1"),
                               ("ceo_final_review", "service-manager"),
                               ("ceo_appointment", "worker-development-1")):
            value = self.signed(target)
            forged = self.keys._event_key(signer, self.context)
            value["signature"] = forged.sign(canonical(value["body"]).encode()).hex()
            with self.subTest(target=target, signer=signer), self.assertRaises(Exception):
                self.verify(value, target)

    def test_forged_signature_role_origin_key_and_content_denied(self):
        original = self.signed()
        for field, value in (("signature", "0" * 128), ("public_key", "0" * 64)):
            bad = deepcopy(original)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(Exception):
                self.verify(bad)
        for field, value in (("role", "ceo"), ("actor", "service-ceo"),
                             ("domain", "owner-approval"), ("detail_hash", "0" * 64)):
            bad = deepcopy(original)
            bad["body"][field] = value
            with self.subTest(field=field), self.assertRaises(Exception):
                self.verify(bad)
        with self.assertRaises(Exception):
            self.verify(original, detail=dict(self.detail, response_hash="d" * 64))

    def test_replay_scope_hash_sequence_previous_and_run_denied(self):
        signed = self.signed()
        for field, value in (("run_id", "OTHER"), ("assignment_hash", "0" * 64),
                             ("implementation", "0" * 64)):
            with self.subTest(field=field), self.assertRaises(Exception):
                self.verify(signed, context=dict(self.context, **{field: value}))
        with self.assertRaises(Exception):
            self.verify(signed, sequence=2)
        with self.assertRaises(Exception):
            self.verify(signed, previous="0" * 64)

    def test_epoch_revocation_and_disable_rechecked_without_restart(self):
        signed = self.signed()
        for policy in (dict(epoch=2, revoked=[], enabled=True),
                       dict(epoch=1, revoked=["worker-development-1"], enabled=True),
                       dict(epoch=1, revoked=[], enabled=False)):
            write_json(self.directory / "authority.json", policy)
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                self.verify(signed)

    def test_global_quota_across_instances_and_failed_attempts_is_not_refunded(self):
        with patch.object(identity, "DAILY_REQUESTS", 2):
            self.keys.reserve_provider("failed-call", 100, context=self.context)
            identity.preparation_authority().reserve_provider("other-run", 100, context=self.context)
            with self.assertRaises(ValueError):
                self.keys.reserve_provider("third", 100, context=self.context)

    def test_atomic_global_quota_under_concurrent_reservations(self):
        def reserve(index):
            try:
                identity.preparation_authority().reserve_provider(str(index), 100, context=self.context)
                return True
            except ValueError:
                return False
        # Create schema before exercising concurrent callers.
        self.keys.reserve_provider("initial", 100, context=self.context)
        with patch.object(identity, "DAILY_REQUESTS", 3), ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve, range(8))), 2)

    def test_token_quota_and_duplicate_reservation_denied(self):
        with patch.object(identity, "DAILY_OUTPUT_TOKENS", 100):
            self.keys.reserve_provider("first", 100, context=self.context)
            with self.assertRaises(ValueError):
                self.keys.reserve_provider("second", 1, context=self.context)
        for tokens in (True, 0, 16385):
            with self.assertRaises(ValueError):
                self.keys.reserve_provider("bad", tokens, context=self.context)
        with self.assertRaises(Exception):
            self.keys.reserve_provider("first", 100, context=self.context)

    def manager(self):
        runtime = load_runtime()
        sys.path.insert(0, str(ROOT / "ventures/venture-001/runtime"))
        try:
            import test_provider_manager as fixtures
        finally:
            sys.path.pop(0)
        run = "identity-test-" + uuid.uuid4().hex[:20]
        manager = runtime.AgentManager(run, test_provider=fixtures.TestProvider(),
                                       identities=self.keys, assignment=dict(scope="TEST_ONLY"))
        self.addCleanup(lambda: shutil.rmtree(manager.home, ignore_errors=True))
        self.addCleanup(manager.close)
        return manager

    def test_existing_studio_journey_signs_every_worker_and_manager_review(self):
        manager = self.manager()
        result = manager.run_agents()
        self.assertEqual(result["status"], "prepared_with_research_blocked")
        manager.verify_agent_state()
        events = [json.loads(row["body"]) for row in manager.db.execute("SELECT body FROM events")]
        workers = [e for e in events if e["action"] == "worker_submission"]
        self.assertEqual(len(workers), 5)
        self.assertEqual(len({e["attestation"]["public_key"] for e in workers}), 5)
        self.assertTrue(any(e["action"] == "ceo_appointment" for e in events))
        self.assertTrue(any(e["action"] == "manager_signoff" for e in events))
        for role in ("development", "testing", "security", "commercial", "research"):
            self.assertTrue(any(e["attestation"]["body"]["actor"] == "worker-" + role + "-1" for e in workers))
        prompt = (manager.home / "inference/development-1/request.json").read_text()
        self.assertNotIn("identities.private", prompt)
        self.assertNotIn("signature", prompt)
        self.assertEqual(result["approval_status"], "UNAPPROVED_PILOT")

    def test_rehashing_tampered_event_chain_cannot_forge_signed_history(self):
        manager = self.manager()
        manager.plan()
        rows = list(manager.db.execute("SELECT * FROM events ORDER BY sequence"))
        previous = "GENESIS"
        for row in rows:
            event = json.loads(row["body"])
            if event["action"] == "agent_assignment":
                event["detail"]["role"] = "ceo"
            body = canonical(event)
            sha = hashlib.sha256((previous + body).encode()).hexdigest()
            manager.db.execute("UPDATE events SET body=?,previous=?,hash=? WHERE sequence=?",
                               (body, previous, sha, row["sequence"]))
            previous = sha
        manager.db.commit()
        with self.assertRaises(ValueError):
            manager.verify_agent_state()

    def test_unassigned_worker_or_other_role_cannot_dispatch(self):
        manager = self.manager()
        manager.plan()
        for actor, role in (("development-1", "security"), ("unknown-1", "development")):
            with self.assertRaises(ValueError):
                manager.infer(actor, role, {}, "{}")


if __name__ == "__main__":
    unittest.main()

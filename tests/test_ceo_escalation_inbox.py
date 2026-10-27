"""Synthetic signing fixtures, not real CEO decisions or provider inference."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agents.ceo.escalation_inbox import (
    EscalationInbox, ROOT, canonical, digest, main,
)

PACKET = "ventures/venture-001/CEO-ESCALATION-ONLINE-20261027.md"


class EscalationInboxTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "artifacts").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.path = Path(self.temp.name) / "inbox.sqlite"
        self.signer = Ed25519PrivateKey.generate()  # test-only synthetic authority
        self.key = self.signer.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.inbox = EscalationInbox(self.path, ceo_public_key=self.key)
        self.packet = (ROOT / PACKET).read_bytes()

    def tearDown(self):
        self.inbox.close()
        self.temp.cleanup()

    def ingest(self, inbox=None, **changes):
        return (inbox or self.inbox).ingest(**dict(
            dict(item_id="studio-online", venture_id="venture-001",
                 source=PACKET, packet=self.packet), **changes))

    def review(self, disposition="HANDOFF"):
        item = self.inbox.read("studio-online")
        return dict(item_id=item["id"], packet_hash=item["packet_hash"],
                    disposition=disposition, summary="TEST fixture: scope conflict reviewed.",
                    manager_id="manager-venture-001", scope="PREPARATION_ONLY",
                    instructions=["Draft backend plan with tenant isolation and durable CRUD.",
                                  "Specify independent HTTP/browser and recovery acceptance.",
                                  "Report provider blocker; no credential or VM changes."],
                    owner_action="Precise configuration request required if blocked.")

    def receipt(self):
        item = self.inbox.read("studio-online")
        now = datetime.now(timezone.utc)
        return dict(venture_id=item["venture_id"], item_id=item["id"], packet_hash=item["packet_hash"],
                    review_hash=digest(canonical(item["review"]).encode()),
                    manager_id="manager-venture-001", decision=item["review"]["disposition"],
                    scope="PREPARATION_ONLY", ceo_id="test-ceo",
                    decision_reference="TEST-ONLY-signed-fixture",
                    issued_at=(now-timedelta(minutes=1)).isoformat(),
                    expires_at=(now+timedelta(hours=1)).isoformat())

    def decide(self, receipt=None, signer=None):
        receipt = receipt or self.receipt()
        return self.inbox.record_decision("studio-online", receipt,
            (signer or self.signer).sign(canonical(receipt).encode()).hex())

    def prepare(self, disposition="HANDOFF"):
        self.ingest()
        self.inbox.ack("studio-online", "test-reviewer")
        self.inbox.record_review("studio-online", self.review(disposition),
                                 evidence_source="fixture")

    def test_existing_escalation_durable_roundtrip_and_ack_is_not_decision(self):
        item = self.ingest()
        self.assertIn("not an executed CEO decision", item["packet"])
        self.assertEqual(item["packet_hash"], digest(self.packet))
        self.assertEqual(self.ingest(), item)
        self.inbox.ack(item["id"], "test-reviewer")
        self.inbox.close()
        self.inbox = EscalationInbox(self.path)
        self.assertEqual(self.inbox.read(item["id"])["status"], "ACKNOWLEDGED")
        self.assertEqual(len(self.inbox.read()), 1)
        with self.assertRaises(ValueError):
            self.inbox.handoff(item["id"], "manager-venture-001")
        self.assertEqual(self.inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 2)

    def test_review_alone_cannot_handoff_and_signed_fixture_can_export_only(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.inbox.handoff("studio-online", "manager-venture-001")
        item = self.decide()
        self.assertEqual(item["status"], "HANDOFF_READY")
        result = self.inbox.handoff("studio-online", "manager-venture-001")
        for key in ("operational_authority", "worker_autoexec", "external_actions_allowed"):
            self.assertIs(result[key], False)
        self.assertEqual(result["review_source"], "fixture")
        with self.assertRaises(ValueError):
            self.inbox.handoff("studio-online", "other-manager")
        item["handoff_exported"] = True
        self.assertEqual(self.decide(item["decision"]["receipt"]), item)
        count = self.inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        self.assertEqual(self.inbox.handoff("studio-online", "manager-venture-001"), result)
        self.assertEqual(self.inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], count)
        self.inbox.close()
        self.inbox = EscalationInbox(self.path, ceo_public_key=self.key)
        self.assertEqual(self.inbox.handoff("studio-online", "manager-venture-001"), result)

    def test_unconfigured_or_wrong_authority_denied(self):
        self.prepare()
        with self.assertRaises(Exception):
            self.decide(signer=Ed25519PrivateKey.generate())
        self.inbox.key = None
        with self.assertRaises(ValueError):
            self.decide()
        self.assertEqual(self.inbox.read("studio-online")["status"], "REVIEWED")

    def test_strict_review_schema_and_bindings(self):
        self.ingest()
        self.inbox.ack("studio-online", "test-reviewer")
        for changes in ({"extra": True}, {"packet_hash": "wrong"},
                        {"item_id": "wrong"}, {"scope": "LIVE"}, {"disposition": "APPROVED"},
                        {"instructions": []}, {"instructions": ["x"] * 9},
                        {"summary": ""}, {"manager_id": "../bad"},
                        {"owner_action": False}):
            review = dict(self.review(), **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.inbox.record_review("studio-online", review, evidence_source="fixture")
        self.assertEqual(self.inbox.read("studio-online")["status"], "ACKNOWLEDGED")

    def test_hold_denied_and_invalid_receipts_never_handoff(self):
        self.prepare("HOLD")
        for changes in ({"venture_id": "another-venture"}, {"review_hash": "wrong"}, {"packet_hash": "wrong"},
                        {"manager_id": "other"}, {"decision": "HANDOFF"},
                        {"scope": "LIVE"}, {"extra": True},
                        {"expires_at": "2000-01-01T00:00:00+00:00"},
                        {"issued_at": "2099-01-01T00:00:00+00:00"}):
            with self.subTest(changes=changes), self.assertRaises(Exception):
                self.decide(dict(self.receipt(), **changes))
        self.assertEqual(self.decide()["status"], "HOLD")
        with self.assertRaises(ValueError):
            self.inbox.handoff("studio-online", "manager-venture-001")

    def test_denied_is_terminal(self):
        self.prepare("DENIED")
        self.assertEqual(self.decide()["status"], "DENIED")
        with self.assertRaises(ValueError):
            self.inbox.record_review("studio-online", self.review(), evidence_source="fixture")
        with self.assertRaises(ValueError):
            self.inbox.handoff("studio-online", "manager-venture-001")

    def test_expiry_rechecked_at_handoff_and_key_rotation_denies(self):
        self.prepare()
        self.decide()
        self.inbox.key = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        with self.assertRaises(Exception):
            self.inbox.handoff("studio-online", "manager-venture-001")
        self.inbox.key = self.key
        with patch("agents.ceo.escalation_inbox.datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) + timedelta(days=2)
            clock.fromisoformat.side_effect = datetime.fromisoformat
            with self.assertRaises(ValueError):
                self.inbox.handoff("studio-online", "manager-venture-001")

    def test_atomic_concurrent_ingestion_conflict_and_capacity(self):
        def ingest():
            inbox = EscalationInbox(self.path)
            try:
                return self.ingest(inbox)
            finally:
                inbox.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: ingest(), range(8)))
        self.assertTrue(all(item == results[0] for item in results))
        self.assertEqual(self.inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 1)
        with self.assertRaises(ValueError):
            self.ingest(packet=b"changed")
        with patch("agents.ceo.escalation_inbox.MAX_ITEMS", 1):
            with self.assertRaises(ValueError):
                self.ingest(item_id="second")
        self.assertEqual(len(self.inbox.read()), 1)

    def test_transaction_failure_rolls_back_snapshot_and_event(self):
        original = self.inbox._save
        def crash(item, kind):
            original(item, kind)
            raise KeyboardInterrupt()
        with patch.object(self.inbox, "_save", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                self.ingest()
        self.assertEqual(self.inbox.read(), [])
        self.assertEqual(self.inbox.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 0)
        self.ingest()

    def test_tampered_snapshot_event_and_missing_tail_block_reads(self):
        self.ingest()
        self.inbox.ack("studio-online", "test-reviewer")
        for sql in ("UPDATE inbox SET snapshot='{}'",
                    "UPDATE audit SET event='{}' WHERE sequence=1",
                    "DELETE FROM audit WHERE sequence=2"):
            self.inbox.db.execute("SAVEPOINT tamper")
            self.inbox.db.execute(sql)
            with self.assertRaises(Exception):
                self.inbox.read()
            self.inbox.db.execute("ROLLBACK TO tamper")
            self.inbox.db.execute("RELEASE tamper")
        self.inbox.verify()

    def test_cli_ingest_read_ack_and_path_bounds(self):
        prefix = ["--database", str(self.path)]
        for args in (["ingest", "--id", "studio-online", "--venture", "venture-001",
                      "--file", PACKET],
                     ["read", "--id", "studio-online"],
                     ["ack", "--id", "studio-online", "--actor", "test-reviewer"]):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(prefix + args), 0)
            self.assertNotIn("HANDOFF_READY", output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(prefix + ["ingest", "--id", "bad",
                "--venture", "venture-001", "--file", "../outside"]), 4)
        with self.assertRaises(ValueError):
            EscalationInbox(ROOT.parent / "outside.sqlite")
        alias = self.path.parent / "alias"
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            EscalationInbox(alias)

    def test_input_bounds_and_ack_conflict(self):
        for changes in ({"packet": b"x" * 65537}, {"packet": b""},
                        {"packet": b"\xff"}, {"item_id": "../bad"}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, UnicodeError)):
                self.ingest(**changes)
        self.ingest()
        with self.assertRaises(ValueError):
            self.inbox.record_review("studio-online", self.review(), evidence_source="fixture")
        self.inbox.ack("studio-online", "first")
        with self.assertRaises(ValueError):
            self.inbox.ack("studio-online", "second")

    def test_review_replay_provenance_immutability_and_event_bound(self):
        self.prepare()
        item = self.inbox.read("studio-online")
        self.assertEqual(self.inbox.record_review("studio-online", self.review(),
                         evidence_source="fixture"), item)
        for changes in ({"summary": "changed"}, {"instructions": ["new task"]}):
            with self.assertRaises(ValueError):
                self.inbox.record_review("studio-online", dict(self.review(), **changes),
                                         evidence_source="fixture")
        with self.assertRaises(ValueError):
            self.inbox.record_review("studio-online", self.review(),
                                     evidence_source="real_provider_inference")
        with patch("agents.ceo.escalation_inbox.MAX_EVENTS", 3):
            with self.assertRaises(ValueError):
                self.decide()
        self.assertEqual(self.inbox.read("studio-online"), item)

    def test_receipt_validity_bound_and_database_mode(self):
        self.prepare()
        receipt = self.receipt()
        receipt["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        with self.assertRaises(ValueError):
            self.decide(receipt)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

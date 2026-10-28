"""Supplemental deterministic protocol tests; no network or operational keys.

Signatures below are fixed fixtures using the published RFC 8032 section 7.1
test identities. Only public keys/signatures are retained; tests never sign,
generate keys, provision identities or invoke any dispatcher.
Run: infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_cross_vm_transport -v
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
import ssl
import unittest
from unittest.mock import Mock, patch

from agents.ceo import cross_vm_transport as transport
from agents.ceo.escalation_inbox import canonical, digest

FIXTURES = {
    "assignment": {
        "body": {
            "domain": "cross-vm-assignment-v1",
            "actor_id": "test-ceo",
            "role": "ceo",
            "recipient_id": "test-manager",
            "task_id": "test-task-1",
            "venture_id": "test-venture",
            "scope": "PREPARATION_ONLY",
            "issued_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2026-01-01T00:05:00+00:00",
            "nonce": "test-assignment-nonce",
            "content_sha256": "df694ba5e3e5cac7efaed6e317694fcc8c0aa0bfea652fc595fe454a49765bb9",
            "live": False
        },
        "content": {
            "instructions": [
                "TEST ONLY: inspect fixture"
            ]
        },
        "signature": "371596ce9aec07397b06f111ecd84ca248b50eec120fc20aa036673d3737018b25f244befec84cd1e71a5d7f2f3f67d3ed34d04856c96006506fb7c8f8ae420e"
    },
    "ack": {
        "body": {
            "domain": "cross-vm-acknowledgement-v1",
            "actor_id": "test-manager",
            "role": "manager",
            "recipient_id": "test-ceo",
            "task_id": "test-task-1",
            "venture_id": "test-venture",
            "scope": "PREPARATION_ONLY",
            "issued_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2026-01-01T00:05:00+00:00",
            "nonce": "test-ack-nonce",
            "content_sha256": "df694ba5e3e5cac7efaed6e317694fcc8c0aa0bfea652fc595fe454a49765bb9",
            "live": False,
            "assignment_sha256": "b67daeb08712ffb1f84ae7a050400f69f17a8944cc90251454dd9820396be393",
            "status": "RECEIVED"
        },
        "signature": "6622c6ddf603ab8431e4c254e5a3f7f765c629378968edf405c625cb3e6b22ad11be4f205fa6436aa1380a8606f69e0d3848d3fbe9bfbb257808310703872e00"
    },
    "wrong_ack": {
        "body": {
            "domain": "cross-vm-acknowledgement-v1",
            "actor_id": "test-manager",
            "role": "manager",
            "recipient_id": "test-ceo",
            "task_id": "test-task-1",
            "venture_id": "test-venture",
            "scope": "PREPARATION_ONLY",
            "issued_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2026-01-01T00:05:00+00:00",
            "nonce": "test-ack-nonce",
            "content_sha256": "df694ba5e3e5cac7efaed6e317694fcc8c0aa0bfea652fc595fe454a49765bb9",
            "live": False,
            "assignment_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "status": "RECEIVED"
        },
        "signature": "a3ad6246b6423c19c56c3df1387a8d2cd1f087b3c281c2556e0a8d8df9693f96dccb43faffb38f16137754e5f9621183a4112c4b1e86c36d12b92cfbf346500c"
    }
}
ACTORS = {
    "test-ceo": ("ceo", bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")),
    "test-manager": ("manager", bytes.fromhex(
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")),
}
NOW = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)


class ReplayStore:
    """Test double only. Runtime must supply atomic durable implementations."""

    def __init__(self):
        self.nonces = set()
        self.tasks = {}

    def consume(self, actor, nonce, expires):
        key = (actor, nonce)
        if key in self.nonces:
            return False
        self.nonces.add(key)
        return True

    def reserve(self, task_id, content_hash):
        if task_id in self.tasks:
            return False
        self.tasks[task_id] = content_hash
        return True


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.assignment = deepcopy(FIXTURES["assignment"])
        self.store = ReplayStore()

    def verify(self, envelope=None, **kwargs):
        return transport.verify_assignment(
            self.assignment if envelope is None else envelope, ACTORS,
            ceo_id="test-ceo", manager_id="test-manager",
            consume_nonce=self.store.consume, now=kwargs.get("now", NOW))

    def test_valid_signature_and_canonical_builder(self):
        verified = self.verify()
        body = self.assignment["body"]
        built = transport.assignment_body(
            actor_id="test-ceo", manager_id="test-manager",
            task_id=body["task_id"], venture_id=body["venture_id"],
            content=self.assignment["content"], issued_at=body["issued_at"],
            expires_at=body["expires_at"], nonce=body["nonce"])
        self.assertEqual(built, body)
        self.assertEqual(body["content_sha256"],
                         digest(canonical(self.assignment["content"]).encode()))
        self.assertEqual(verified, self.assignment)
        self.assertIsNot(verified, self.assignment)

    def test_invalid_signature_and_wrong_public_key(self):
        self.assignment["signature"] = "0" * 128
        with self.assertRaisesRegex(transport.EnvelopeError, "signature"):
            self.verify()
        self.assertFalse(self.store.nonces)
        pins = dict(ACTORS, **{"test-ceo": ("ceo", ACTORS["test-manager"][1])})
        with self.assertRaisesRegex(transport.EnvelopeError, "signature"):
            transport.verify_assignment(FIXTURES["assignment"], pins,
                ceo_id="test-ceo", manager_id="test-manager",
                consume_nonce=self.store.consume, now=NOW)

    def test_expired_including_exact_expiry_and_future(self):
        for moment in (NOW + timedelta(minutes=4),
                       NOW + timedelta(days=1), NOW - timedelta(minutes=2)):
            with self.subTest(moment=moment), self.assertRaises(transport.EnvelopeError):
                self.verify(now=moment)
        self.assertFalse(self.store.nonces)

    def test_role_scope_recipient_domain_and_live_denied(self):
        for field, value in (("role", "worker"), ("scope", "FINANCE"),
                             ("recipient_id", "other-manager"),
                             ("domain", transport.ACKNOWLEDGEMENT), ("live", True)):
            envelope = deepcopy(self.assignment)
            envelope["body"][field] = value
            with self.subTest(field=field), self.assertRaises(transport.EnvelopeError):
                self.verify(envelope)
        pins = dict(ACTORS, **{"test-ceo": ("worker", ACTORS["test-ceo"][1])})
        with self.assertRaisesRegex(transport.EnvelopeError, "pinned role"):
            transport.verify_assignment(self.assignment, pins,
                ceo_id="test-ceo", manager_id="test-manager",
                consume_nonce=self.store.consume, now=NOW)
        self.assertFalse(self.store.nonces)

    def test_tampered_content_and_nonce_replay(self):
        tampered = deepcopy(self.assignment)
        tampered["content"]["instructions"].append("tampered")
        with self.assertRaisesRegex(transport.EnvelopeError, "content binding"):
            self.verify(tampered)
        self.assertFalse(self.store.nonces)
        self.verify()
        with self.assertRaisesRegex(transport.EnvelopeError, "nonce replay"):
            self.verify()

    def test_non_utc_naive_and_excessive_window_denied(self):
        for issued, expires in (
                ("2026-01-01T00:00:00", "2026-01-01T00:05:00"),
                ("2026-01-01T00:00:00+01:00", "2026-01-01T00:05:00+01:00"),
                ("2026-01-01T00:00:00+00:00", "2026-01-01T00:05:01+00:00")):
            envelope = deepcopy(self.assignment)
            envelope["body"].update(issued_at=issued, expires_at=expires)
            with self.subTest(issued=issued), self.assertRaises(transport.EnvelopeError):
                self.verify(envelope)

    def test_json_size_nonfinite_and_unknown_fields_denied(self):
        for value in ({"x": "a" * transport.MAX_WIRE}, {"x": float("nan")}):
            envelope = deepcopy(self.assignment)
            envelope["content"] = value
            with self.assertRaises(transport.EnvelopeError):
                self.verify(envelope)
        self.assignment["unexpected"] = "denied"
        with self.assertRaises(ValueError):
            self.verify()

    def test_valid_acknowledgement_and_ack_replay(self):
        verified = self.verify()
        def ack():
            return transport.verify_acknowledgement(FIXTURES["ack"], verified,
                ACTORS, consume_nonce=self.store.consume, now=NOW)
        self.assertEqual(ack()["status"], "RECEIVED")
        with self.assertRaisesRegex(transport.EnvelopeError, "nonce replay"):
            ack()

    def test_wrong_signed_acknowledgement_and_invalid_ack_signature(self):
        verified = self.verify()
        for envelope in (FIXTURES["wrong_ack"],
                         dict(FIXTURES["ack"], signature="0" * 128)):
            with self.assertRaises(transport.EnvelopeError):
                transport.verify_acknowledgement(envelope, verified, ACTORS,
                    consume_nonce=self.store.consume, now=NOW)
        self.assertEqual(len(self.store.nonces), 1)

    def test_expired_acknowledgement(self):
        with self.assertRaises(transport.EnvelopeError):
            transport.verify_acknowledgement(FIXTURES["ack"], self.verify(), ACTORS,
                consume_nonce=self.store.consume, now=NOW + timedelta(minutes=4))


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.store = ReplayStore()
        self.client = self.client_for(self.store)
        clock_patch = patch.object(transport, "datetime", wraps=datetime)
        clock = clock_patch.start()
        clock.now.return_value = NOW
        self.addCleanup(clock_patch.stop)
        connection_patch = patch.object(transport.http.client, "HTTPSConnection")
        self.connection_type = connection_patch.start()
        self.addCleanup(connection_patch.stop)
        self.connection = self.connection_type.return_value
        self.response(json.dumps(FIXTURES["ack"]).encode())

    def client_for(self, store):
        return transport.CrossVMTransport(
            "https://tasks.invalid:9443/assignments", ACTORS,
            ceo_id="test-ceo", manager_id="test-manager",
            consume_nonce=store.consume, reserve_task=store.reserve)

    def response(self, raw, status=200):
        response = io.BytesIO(raw)
        response.status = status
        self.connection.getresponse.return_value = response

    def test_https_verified_post_and_valid_signed_ack(self):
        self.assertEqual(self.client.send(FIXTURES["assignment"])["status"], "RECEIVED")
        self.connection_type.assert_called_once()
        args, kwargs = self.connection_type.call_args
        self.assertEqual(args, ("tasks.invalid", 9443))
        self.assertEqual(kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(kwargs["context"].check_hostname)
        call = self.connection.request.call_args
        self.assertEqual(call.args, ("POST", "/assignments"))
        self.assertEqual(call.kwargs["headers"]["Idempotency-Key"], "test-task-1")
        self.assertEqual(json.loads(call.kwargs["body"]), FIXTURES["assignment"])
        self.connection.close.assert_called_once()

    def test_network_failure_unknown_outcome_and_no_retry(self):
        self.connection.request.side_effect = OSError("TEST sensitive exception")
        with self.assertRaises(transport.UnknownOutcome) as caught:
            self.client.send(FIXTURES["assignment"])
        self.assertEqual(caught.exception.task_id, "test-task-1")
        self.assertNotIn("sensitive", str(caught.exception))
        self.connection.request.assert_called_once()
        # Reusing this client or a new one with the same storage never sends again.
        for client in (self.client, self.client_for(self.store)):
            with self.assertRaises(transport.EnvelopeError):
                client.send(FIXTURES["assignment"])
        self.connection.request.assert_called_once()
        self.assertIn("test-task-1", self.store.tasks)

    def test_prior_task_reservation_blocks_before_connection(self):
        self.store.reserve("test-task-1", "prior-content-hash")
        with self.assertRaisesRegex(transport.EnvelopeError, "reserved"):
            self.client.send(FIXTURES["assignment"])
        self.connection_type.assert_not_called()

    def test_invalid_assignment_never_reserves_or_opens_network(self):
        envelope = deepcopy(FIXTURES["assignment"])
        envelope["signature"] = "0" * 128
        with self.assertRaises(transport.EnvelopeError):
            self.client.send(envelope)
        self.assertFalse(self.store.tasks)
        self.connection_type.assert_not_called()

    def test_wrong_signed_ack_is_unknown_outcome(self):
        self.response(json.dumps(FIXTURES["wrong_ack"]).encode())
        with self.assertRaises(transport.UnknownOutcome):
            self.client.send(FIXTURES["assignment"])
        self.connection.request.assert_called_once()
        self.assertIn("test-task-1", self.store.tasks)

    def test_redirect_http_errors_invalid_json_and_large_ack_no_retry(self):
        for status, raw in ((302, b""), (503, b""), (200, b"not JSON"),
                            (200, b'{"body":{},"body":{}}'),
                            (200, b"x" * (transport.MAX_ACK + 1))):
            with self.subTest(status=status, raw_length=len(raw)):
                self.store = ReplayStore()
                self.client = self.client_for(self.store)
                self.connection.reset_mock()
                self.response(raw, status)
                with self.assertRaises(transport.UnknownOutcome):
                    self.client.send(FIXTURES["assignment"])
                self.connection.request.assert_called_once()
                self.connection.close.assert_called_once()

    def test_tls_certificate_failure_is_unknown_without_fallback(self):
        self.connection.request.side_effect = ssl.SSLCertVerificationError("TEST")
        with self.assertRaises(transport.UnknownOutcome):
            self.client.send(FIXTURES["assignment"])
        self.connection_type.assert_called_once()
        self.connection.request.assert_called_once()

    def test_replay_storage_failure_prevents_network(self):
        self.client._consume_nonce = Mock(side_effect=OSError("TEST storage"))
        with self.assertRaises(OSError):
            self.client.send(FIXTURES["assignment"])
        self.connection_type.assert_not_called()
        self.client._consume_nonce = self.store.consume
        self.client._reserve_task = Mock(side_effect=OSError("TEST storage"))
        with self.assertRaises(OSError):
            self.client.send(FIXTURES["assignment"])
        self.connection_type.assert_not_called()

    def test_insecure_or_implicit_endpoints_and_bad_timeouts_rejected(self):
        for endpoint in ("http://tasks.invalid/assignments", "https://tasks.invalid",
                         "https://tasks.invalid/", "https://user@tasks.invalid/tasks",
                         "https://tasks.invalid/tasks?token=TEST",
                         "https://tasks.invalid/tasks#fragment",
                         "https://tasks.invalid:bad/tasks", "https://tasks.invalid/\n"):
            with self.subTest(endpoint=endpoint), self.assertRaises(transport.EnvelopeError):
                transport.CrossVMTransport(endpoint, ACTORS, ceo_id="test-ceo",
                    manager_id="test-manager", consume_nonce=self.store.consume,
                    reserve_task=self.store.reserve)
        for timeout in (True, 0, 61, float("inf"), float("nan")):
            with self.assertRaises(transport.EnvelopeError):
                transport.CrossVMTransport("https://tasks.invalid/tasks", ACTORS,
                    ceo_id="test-ceo", manager_id="test-manager",
                    consume_nonce=self.store.consume, reserve_task=self.store.reserve,
                    timeout=timeout)


if __name__ == "__main__":
    unittest.main()

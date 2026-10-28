"""Standalone cross-VM preparation protocol; no dispatcher or authority integration.

Signers outside this module sign canonical(body).encode(), as service_identity
does. assignment_body constructs signing input only: it cannot mint signatures.
A valid signature authenticates data, never owner, finance or execution authority.

Callers MUST supply trusted pins and atomic replay/reservation callbacks backed
by durable storage before runtime integration. consume_nonce(actor, nonce,
expires_at) and reserve_task(task_id, content_sha256) return exactly True once,
False on any replay/conflict, and fail closed on storage failure. Reservations
survive restarts and ambiguous delivery; never release them for automatic retry.
The remote receiver must independently verify, deduplicate task_id, and enforce
current policy before doing anything. Acknowledgements attest receipt only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import http.client
import json
import math
import re
import ssl
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from agents.ceo.escalation_inbox import canonical, digest, exact, identifier

ASSIGNMENT = "cross-vm-assignment-v1"
ACKNOWLEDGEMENT = "cross-vm-acknowledgement-v1"
SCOPE = "PREPARATION_ONLY"
MAX_WIRE = 65536
MAX_ACK = 8192
MAX_LIFETIME = timedelta(minutes=5)
COMMON = ("domain", "actor_id", "role", "recipient_id", "task_id", "venture_id",
          "scope", "issued_at", "expires_at", "nonce", "content_sha256", "live")


class EnvelopeError(ValueError):
    """Untrusted, stale, replayed or out-of-scope protocol input."""


class UnknownOutcome(RuntimeError):
    """Delivery may have happened. Reconcile task_id; no automatic retry."""

    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__("UNKNOWN_OUTCOME: reconcile reserved task " + task_id)


def _wire(value, limit=MAX_WIRE):
    try:
        raw = canonical(value).encode()
        if len(raw) > limit:
            raise ValueError()
        return raw
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise EnvelopeError("invalid or oversized canonical JSON") from None


def _timestamp(value):
    if type(value) is not str or len(value) > 40:
        raise EnvelopeError("invalid timestamp")
    try:
        result = datetime.fromisoformat(value)
        if result.utcoffset() != timedelta(0):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise EnvelopeError("UTC timestamp required") from None


def _body(body, *, domain, actor_id, recipient_id, role, now):
    exact(body, COMMON if domain == ASSIGNMENT else
          (*COMMON, "assignment_sha256", "status"))
    for field in ("actor_id", "recipient_id", "task_id", "venture_id", "nonce"):
        identifier(body[field])
    if (body["domain"] != domain or body["actor_id"] != actor_id
            or body["recipient_id"] != recipient_id or actor_id == recipient_id
            or body["role"] != role or body["scope"] != SCOPE
            or body["live"] is not False):
        raise EnvelopeError("actor role scope or domain denied")
    if (type(body["content_sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", body["content_sha256"])):
        raise EnvelopeError("invalid content hash")
    issued, expires = (_timestamp(body[k]) for k in ("issued_at", "expires_at"))
    if (now.tzinfo is None or not issued <= now < expires
            or not timedelta(0) < expires - issued <= MAX_LIFETIME):
        raise EnvelopeError("timestamp outside bounded validity")


def assignment_body(*, actor_id, manager_id, task_id, venture_id, content,
                    issued_at, expires_at, nonce):
    """Build unsigned signing input. Stable task_id is independent of nonce/time.

    Trusted caller chooses a globally unique logical task_id; changed work gets a
    new task_id. Content is opaque preparation data, never executable authority.
    """
    if type(content) is not dict:
        raise EnvelopeError("assignment content must be an object")
    body = dict(domain=ASSIGNMENT, actor_id=actor_id, role="ceo",
                recipient_id=manager_id, task_id=task_id, venture_id=venture_id,
                scope=SCOPE, issued_at=issued_at, expires_at=expires_at,
                nonce=nonce, content_sha256=digest(_wire(content)), live=False)
    _body(body, domain=ASSIGNMENT, actor_id=actor_id, recipient_id=manager_id,
          role="ceo", now=_timestamp(issued_at))
    _wire(body)
    return body


def _signed(envelope, actors, *, domain, actor_id, recipient_id, role, now):
    exact(envelope, ("body", "signature", "content") if domain == ASSIGNMENT
          else ("body", "signature"))
    _wire(envelope, MAX_WIRE if domain == ASSIGNMENT else MAX_ACK)
    body = envelope["body"]
    _body(body, domain=domain, actor_id=actor_id, recipient_id=recipient_id,
          role=role, now=now)
    pin = actors.get(actor_id)
    if pin is None or pin[0] != role:
        raise EnvelopeError("pinned role denied")
    signature = envelope["signature"]
    if type(signature) is not str or not re.fullmatch(r"[0-9a-f]{128}", signature):
        raise EnvelopeError("invalid signature encoding")
    try:
        Ed25519PublicKey.from_public_bytes(pin[1]).verify(
            bytes.fromhex(signature), _wire(body))
    except (InvalidSignature, ValueError, TypeError):
        raise EnvelopeError("signature denied") from None
    return body


def verify_assignment(envelope, actors, *, ceo_id, manager_id, consume_nonce,
                      now=None):
    """Authenticate and atomically consume a nonce only after all checks pass."""
    # Snapshot mutable input before verification or callback invocation.
    envelope = json.loads(_wire(envelope))
    body = _signed(envelope, actors, domain=ASSIGNMENT, actor_id=ceo_id,
                   recipient_id=manager_id, role="ceo",
                   now=now if now is not None else datetime.now(timezone.utc))
    if (type(envelope["content"]) is not dict
            or digest(_wire(envelope["content"])) != body["content_sha256"]):
        raise EnvelopeError("content binding denied")
    if consume_nonce(ceo_id, body["nonce"], body["expires_at"]) is not True:
        raise EnvelopeError("nonce replay denied")
    return envelope


def verify_acknowledgement(envelope, assignment, actors, *, consume_nonce,
                           now=None):
    """Verify manager receipt bound to this exact verified assignment body.

    assignment is the output of verify_assignment. RECEIVED and DUPLICATE mean
    receipt/deduplication only; REJECTED means refusal. None proves execution.
    """
    envelope = json.loads(_wire(envelope, MAX_ACK))
    original = assignment["body"]
    body = _signed(envelope, actors, domain=ACKNOWLEDGEMENT,
                   actor_id=original["recipient_id"],
                   recipient_id=original["actor_id"], role="manager",
                   now=now if now is not None else datetime.now(timezone.utc))
    if (any(body[k] != original[k] for k in
            ("task_id", "venture_id", "scope", "content_sha256"))
            or body["assignment_sha256"] != digest(_wire(original))
            or body["status"] not in ("RECEIVED", "DUPLICATE", "REJECTED")
            or _timestamp(body["issued_at"]) < _timestamp(original["issued_at"])):
        raise EnvelopeError("acknowledgement binding denied")
    if consume_nonce(body["actor_id"], body["nonce"], body["expires_at"]) is not True:
        raise EnvelopeError("acknowledgement nonce replay denied")
    return body


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeError("duplicate JSON field")
        result[key] = value
    return result


class CrossVMTransport:
    """Explicit HTTPS task endpoint; no guessed broker address, redirect or retry.

    CA roots default to system trust; optional ca_file supplies a CA bundle.
    No unverified SSL context or alternate transport can be supplied.
    """

    def __init__(self, endpoint, actors, *, ceo_id, manager_id, consume_nonce,
                 reserve_task, ca_file=None, timeout=10):
        if (type(endpoint) is not str or len(endpoint) > 2048
                or any(ord(c) <= 32 or ord(c) >= 127 for c in endpoint)):
            raise EnvelopeError("invalid endpoint")
        try:
            url = urlsplit(endpoint)
            if (url.scheme != "https" or not url.hostname or url.username is not None
                    or url.password is not None or url.query or url.fragment
                    or not url.path or url.path == "/"):
                raise ValueError()
            port = url.port if url.port is not None else 443
            if port < 1:
                raise ValueError()
        except ValueError:
            raise EnvelopeError("explicit HTTPS task endpoint required") from None
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 < timeout <= 60):
            raise EnvelopeError("bounded timeout required")
        if not callable(consume_nonce) or not callable(reserve_task):
            raise EnvelopeError("durable replay and reservation callbacks required")
        self._context = ssl.create_default_context(cafile=ca_file)
        self._host, self._port, self._path = url.hostname, port, url.path
        self._actors = dict(actors)
        self._ceo_id, self._manager_id = ceo_id, manager_id
        self._consume_nonce, self._reserve_task = consume_nonce, reserve_task
        self._timeout = timeout

    def send(self, envelope):
        assignment = verify_assignment(
            envelope, self._actors, ceo_id=self._ceo_id, manager_id=self._manager_id,
            consume_nonce=self._consume_nonce)
        body = assignment["body"]
        wire = _wire(assignment)
        if self._reserve_task(body["task_id"], body["content_sha256"]) is not True:
            raise EnvelopeError("task already reserved or conflicting; reconcile")
        connection = None
        try:
            # Recheck expiry after potentially blocking durable reservations.
            _body(body, domain=ASSIGNMENT, actor_id=self._ceo_id,
                  recipient_id=self._manager_id, role="ceo",
                  now=datetime.now(timezone.utc))
            # HTTPSConnection performs one attempt and never follows redirects.
            connection = http.client.HTTPSConnection(
                self._host, self._port, timeout=self._timeout, context=self._context)
            connection.request("POST", self._path, body=wire, headers={
                "Content-Type": "application/json", "Accept": "application/json",
                "Idempotency-Key": body["task_id"]})
            response = connection.getresponse()
            if response.status != 200:
                raise EnvelopeError("unexpected response status")
            raw = response.read(MAX_ACK + 1)
            if len(raw) > MAX_ACK:
                raise EnvelopeError("oversized acknowledgement")
            acknowledgement = json.loads(raw, object_pairs_hook=_object)
            return verify_acknowledgement(
                acknowledgement, assignment, self._actors,
                consume_nonce=self._consume_nonce)
        except Exception:
            # Never leak endpoint, response, payload or underlying exception text.
            raise UnknownOutcome(body["task_id"]) from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

"""Synthetic signed non-executing real-VM transport probe.

Not a CEO service. Generates an ephemeral test-only key in memory,
inserts one bounded signed preparation fixture into the configured outbox,
and writes only its public verification key.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.cross_vm_transport import assignment_body
from agents.ceo.cross_vm_outbox import PreparationOutbox
from agents.ceo.cross_vm_state import DurableHandoffState
from agents.ceo.escalation_inbox import canonical

def main():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    now = datetime.now(timezone.utc)
    content = {"instructions": ["TEST ONLY: verify receipt; never execute work"]}
    task = "or010-test-" + uuid4().hex
    body = assignment_body(
        actor_id="or010-test-ceo", manager_id="or010-test-manager",
        task_id=task, venture_id="or010-test-venture", content=content,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=4)).isoformat(),
        nonce="nonce-" + uuid4().hex
    )
    envelope = {
        "body": body,
        "content": content,
        "signature": private.sign(canonical(body).encode()).hex()
    }
    state = DurableHandoffState("/var/lib/venture-control-broker/or010-test-nonces.sqlite")
    outbox = PreparationOutbox("/var/lib/venture-control-broker/outbox.sqlite")
    try:
        assert outbox.enqueue_verified(
            envelope, {"or010-test-ceo": ("ceo", public)},
            expected_ceo="or010-test-ceo",
            expected_manager="or010-test-manager",
            consume_nonce=state.consume_nonce, now=now
        )
    finally:
        outbox.close()
        state.close()
    Path("/tmp/or010-test-ceo-public.hex").write_text(public.hex())
    print("synthetic_signed_queued", task)

if __name__ == "__main__":
    main()

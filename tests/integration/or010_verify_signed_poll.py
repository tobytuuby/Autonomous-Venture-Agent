"""Real-VM mTLS signed poll smoke; TEST ONLY, no assignment execution."""
from pathlib import Path
from agents.ceo.cross_vm_poll_client import PreparationPollClient
from agents.ceo.cross_vm_state import DurableHandoffState

HOME = Path("/home/epsilon/.local/share/venture-agents/or010")
PUBLIC = Path(".or010-public/ceo-public.hex").read_text().strip()
actors = {"or010-test-ceo": ("ceo", bytes.fromhex(PUBLIC))}
state = DurableHandoffState(HOME / "receipt-state.sqlite")
try:
    poller = PreparationPollClient(
        "https://192.168.0.167:8443/v1/assignments/pending",
        ca_file=str(HOME / "ca.crt"),
        client_cert=str(HOME / "agent-client.crt"),
        client_key=str(HOME / "client.key"),
        actors=actors, ceo_id="or010-test-ceo", manager_id="or010-test-manager",
        consume_nonce=state.consume_nonce,
    )
    assignments = poller.poll()
    if len(assignments) != 1:
        raise RuntimeError("expected exactly one synthetic assignment")
    assignment = assignments[0]
    body = assignment["body"]
    assert body["scope"] == "PREPARATION_ONLY" and body["live"] is False
    assert body["role"] == "ceo" and body["recipient_id"] == "or010-test-manager"
    assert state.reserve_task(body["task_id"], body["content_sha256"])
    print("real_vm_mtls_signed_assignment_received", body["task_id"])
    print("signature_verified=true durable_receipt=true executed=false")
finally:
    state.close()

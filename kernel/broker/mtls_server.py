"""mTLS capability broker, preparation polling and opt-in signed receipt ingestion."""
import os
from http.server import ThreadingHTTPServer

from agents.ceo.cross_vm_outbox import PreparationOutbox
from kernel.broker.isolated_mtls import handler_for, tls_context


def required(key):
    value = os.environ.get(key, "").strip()
    if not value:
        raise RuntimeError(f"missing required broker configuration: {key}")
    return value


def main():
    cert = required("VENTURE_BROKER_CERT")
    key = required("VENTURE_BROKER_KEY")
    ca = required("VENTURE_BROKER_CLIENT_CA")
    cap = frozenset(required("VENTURE_BROKER_CAPABILITY_PINS").split(","))
    poll = frozenset(required("VENTURE_BROKER_POLLING_PINS").split(","))
    db_path = required("VENTURE_BROKER_OUTBOX_DB")

    def pending_assignments():
        # HTTP requests are threaded; SQLite connections are thread-affine.
        # Construct and close the read connection inside the request thread.
        outbox = PreparationOutbox(db_path)
        try:
            return outbox.pending(limit=10)
        finally:
            outbox.close()

    # Opt-in only: old read-only deployments stay closed to ACK until public
    # signing trust and fixed workload identities have been explicitly configured.
    acknowledge = None
    submit = None
    status = None
    if os.environ.get("VENTURE_BROKER_PREPARATION_TRUST"):
        from agents.ceo.control_plane import load_trust
        actors = load_trust(required("VENTURE_BROKER_PREPARATION_TRUST"))
        ceo_id = required("VENTURE_BROKER_CEO_ID")
        manager_id = required("VENTURE_BROKER_MANAGER_ID")

        def acknowledge(envelope):
            outbox = PreparationOutbox(db_path)
            try:
                return outbox.accept_ack(envelope, actors, expected_ceo=ceo_id,
                                         expected_manager=manager_id)
            finally:
                outbox.close()

        def submit(envelope):
            outbox = PreparationOutbox(db_path)
            try:
                # Exact committed submissions may be observed again after a lost
                # HTTP response; never reissue the authorization or consume nonce.
                from agents.ceo.escalation_inbox import canonical
                existing = outbox.record(envelope["body"]["task_id"])
                if existing is not None:
                    if canonical(existing["assignment"]) != canonical(envelope):
                        raise ValueError("conflicting assignment denied")
                    return False
                return outbox.enqueue_verified(envelope, actors, expected_ceo=ceo_id,
                    expected_manager=manager_id, consume_nonce=outbox.consume_nonce)
            finally:
                outbox.close()

        def status(task_id):
            outbox = PreparationOutbox(db_path)
            try:
                return outbox.record(task_id)
            finally:
                outbox.close()

    execute = None
    if os.environ.get("VENTURE_BROKER_PROVIDER_ENABLED") == "1":
        from pathlib import Path
        from agents.ceo.venture_exercise import configured_provider
        from agents.ceo.provider_gateway import execute_reserved
        provider = configured_provider(os.environ, required=True)
        from agents.ceo import service_identity
        provider.trace_path = service_identity.AUTHORITY_DIRECTORY / "broker-provider.jsonl"
        actor = required("VENTURE_BROKER_RESERVATION_ACTOR")
        def execute(payload):
            return execute_reserved(payload, actor=actor, provider=provider)

    from agents.ceo.cert_renewal import ManagerRenewalMailbox
    cert_mailbox = ManagerRenewalMailbox()
    handler = handler_for(capability_pins=cap, polling_pins=poll,
                          pending=pending_assignments, acknowledge=acknowledge,
                          reservation_actor=os.environ.get("VENTURE_BROKER_RESERVATION_ACTOR") or None,
                          ceo_reservation_pins=tuple(filter(None, os.environ.get("VENTURE_BROKER_CEO_RESERVATION_PINS", "").split(","))),
                          ceo_reservation_actor=os.environ.get("VENTURE_BROKER_CEO_RESERVATION_ACTOR") or None,
                          submit=submit, status=status, execute=execute, cert_mailbox=cert_mailbox)
    context = tls_context(server_cert=cert, server_key=key, client_ca=ca)
    server = ThreadingHTTPServer(("0.0.0.0", 8443), handler)
    try:
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

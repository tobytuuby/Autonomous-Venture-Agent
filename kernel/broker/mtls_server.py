"""mTLS-only capability broker and read-only signed preparation polling."""
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

    handler = handler_for(capability_pins=cap, polling_pins=poll,
                          pending=pending_assignments)
    context = tls_context(server_cert=cert, server_key=key, client_ca=ca)
    server = ThreadingHTTPServer(("0.0.0.0", 8443), handler)
    try:
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

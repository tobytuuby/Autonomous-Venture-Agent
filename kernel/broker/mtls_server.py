"""mTLS production broker entrypoint. Never starts without complete explicit identity config."""
import os
import sys
from kernel.broker.isolated_mtls import tls_context, handler_for
from http.server import ThreadingHTTPServer

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
    from agents.ceo.cross_vm_outbox import PreparationOutbox
    outbox = PreparationOutbox(required("VENTURE_BROKER_OUTBOX_DB"))
    handler = handler_for(capability_pins=cap, polling_pins=poll,
                          pending=lambda: outbox.pending(limit=10))
    context = tls_context(server_cert=cert, server_key=key, client_ca=ca)
    server = ThreadingHTTPServer(("0.0.0.0", 8443), handler)
    try:
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.serve_forever()
    finally:
        server.server_close()
        outbox.close()

if __name__ == "__main__":
    main()

"""mTLS-only, read-only polling surface for signed preparation assignments.

Not a public HTTP service. The embedding server MUST use CERT_REQUIRED TLS and
a dedicated Agents client CA; this handler additionally checks verified peer
certificate bytes against a pinned SHA256 fingerprint. No execution endpoint.
"""
import hashlib
import json
import ssl
from http.server import BaseHTTPRequestHandler

PATH = "/v1/assignments/pending"


def pending_payload(outbox, *, certificate, allowed_sha256):
    if (not isinstance(certificate, bytes) or not certificate
            or hashlib.sha256(certificate).hexdigest() != allowed_sha256):
        raise PermissionError("client certificate denied")
    return {"assignments": outbox.pending(limit=10)}


def make_handler(outbox, allowed_sha256):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != PATH:
                return self._respond(404, {"error": "not_found"})
            if not isinstance(self.connection, ssl.SSLSocket):
                return self._respond(403, {"error": "tls_required"})
            try:
                cert = self.connection.getpeercert(binary_form=True)
                payload = pending_payload(outbox, certificate=cert, allowed_sha256=allowed_sha256)
            except (PermissionError, ssl.SSLError):
                return self._respond(403, {"error": "identity_denied"})
            return self._respond(200, payload)

        def _respond(self, code, body):
            encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_):
            pass

    return Handler


def serve(outbox, *, host, port, server_cert, server_key, client_ca, client_fingerprint):
    from http.server import ThreadingHTTPServer
    if host not in ("127.0.0.1", "::1"):
        raise ValueError("service must bind to loopback behind approved tunnel")
    if len(client_fingerprint) != 64 or any(c not in "0123456789abcdef" for c in client_fingerprint):
        raise ValueError("pinned certificate fingerprint required")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(server_cert, server_key)
    context.load_verify_locations(cafile=client_ca)
    server = ThreadingHTTPServer((host, port), make_handler(outbox, client_fingerprint))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()

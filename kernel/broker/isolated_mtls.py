"""Isolated, fail-closed mTLS wrapper for the existing capability broker.

This module does not start a production listener. The caller must explicitly
supply a loopback bind address, certificate paths and certificate pinsets.
"""
import hashlib
import ssl
from http.server import ThreadingHTTPServer
from kernel.broker.server import Handler as ExistingBrokerHandler

POLL_PATH = "/v1/assignments/pending"
CAP_PATH = "/v1/capabilities/evaluate"

def tls_context(*, server_cert, server_key, client_ca):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(server_cert, server_key)
    ctx.load_verify_locations(cafile=client_ca)
    return ctx

def handler_for(*, capability_pins, polling_pins, pending=None):
    """Pin DER certificate SHA256 per authorized role, never trust HTTP headers."""
    if not capability_pins or not polling_pins:
        raise ValueError("both identity pinsets required")
    if not all(isinstance(s, str) and len(s) == 64 and
               all(c in "0123456789abcdef" for c in s)
               for s in (*capability_pins, *polling_pins)):
        raise ValueError("malformed fingerprint")
    class GuardedHandler(ExistingBrokerHandler):
        def _role(self):
            if not isinstance(self.connection, ssl.SSLSocket):
                return None
            cert = self.connection.getpeercert(binary_form=True)
            if not cert:
                return None
            fingerprint = hashlib.sha256(cert).hexdigest()
            if fingerprint in polling_pins:
                return "poll"
            if fingerprint in capability_pins:
                return "capability"
            return None

        def _deny(self):
            self._send(403, {"error": "identity_denied"})

        def do_GET(self):
            role = self._role()
            if self.path == POLL_PATH:
                if role != "poll":
                    return self._deny()
                if pending is None:
                    return self._send(503, {"error": "polling_unavailable"})
                return self._send(200, {"assignments": pending()})
            if self.path == "/health" and role == "capability":
                return super().do_GET()
            return self._deny() if role is None or self.path == "/health" else self._send(404, {"error": "not_found"})

        def do_POST(self):
            if self.path == CAP_PATH and self._role() == "capability":
                return super().do_POST()
            return self._deny() if self.path == CAP_PATH or self._role() is None else self._send(404, {"error": "not_found"})

        def do_PUT(self):
            return self._send(405, {"error": "method_not_allowed"})

        def do_DELETE(self):
            return self._send(405, {"error": "method_not_allowed"})
    return GuardedHandler

def isolated_server(*, host, port, server_cert, server_key, client_ca,
                    capability_pins, polling_pins, pending=None):
    if host not in ("127.0.0.1", "::1") or port == 8443:
        raise ValueError("isolated test binding only")
    srv = ThreadingHTTPServer((host, port), handler_for(
        capability_pins=set(capability_pins), polling_pins=set(polling_pins), pending=pending))
    try:
        srv.socket = tls_context(server_cert=server_cert, server_key=server_key,
                                 client_ca=client_ca).wrap_socket(srv.socket, server_side=True)
    except Exception:
        srv.server_close()
        raise
    return srv

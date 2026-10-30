"""Dedicated restricted Owner API. Does not provide venture admission or finance authority."""
import argparse
import hmac
import json
import os
import sqlite3
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agents.ceo.owner_idea_inbox import OwnerIdeaInbox, MAX_BODY
from agents.ceo.escalation_inbox import canonical


def handler_factory(inbox, token):
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("dedicated service credential required")

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(8)
        def reply(self, status, payload):
            raw = canonical(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def authenticated(self):
            return hmac.compare_digest(
                self.headers.get("Authorization", ""),
                "Bearer " + token
            )

        def do_GET(self):
            if not self.authenticated():
                return self.reply(401, {"error": "unauthorized"})
            if self.path != "/v1/owner/ideas":
                return self.reply(404, {"error": "not found"})
            return self.reply(200, {"ideas": inbox.ideas()})

        def do_POST(self):
            if not self.authenticated():
                return self.reply(401, {"error": "unauthorized"})
            if self.path != "/v1/owner/reviews":
                return self.reply(404, {"error": "not found"})
            if self.headers.get("X-Owner-Intent") != "explicit":
                return self.reply(403, {"error": "intent required"})
            try:
                if self.headers.get("Transfer-Encoding"):
                    raise ValueError("transfer encoding not allowed")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    raise ValueError("invalid size")
                value = json.loads(self.rfile.read(size))
                if type(value) is not dict or set(value) != {
                    "cycle_id", "proposal_digest", "decision", "reason"
                }:
                    raise ValueError("invalid fields")
                result = inbox.review(**value)
            except (TypeError, ValueError, sqlite3.IntegrityError, json.JSONDecodeError):
                return self.reply(409, {"error": "invalid, stale or duplicate decision"})
            return self.reply(200, result)

        def log_message(self, *_):
            pass

    return Handler


def serve(inbox, *, host, port, cert, key, client_ca, token):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=client_ca)
    context.load_cert_chain(certfile=cert, keyfile=key)
    if host != "127.0.0.1":
        raise ValueError("Owner API must bind to loopback; use a separately restricted tunnel")
    server = ThreadingHTTPServer((host, port), handler_factory(inbox, token))
    server.daemon_threads = True
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--discovery-db", required=True)
    p.add_argument("--review-db", required=True)
    p.add_argument("--cert", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--client-ca", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8792)
    a = p.parse_args()
    serve(OwnerIdeaInbox(a.discovery_db, a.review_db), host=a.host, port=a.port,
          cert=a.cert, key=a.key, client_ca=a.client_ca,
          token=os.environ.get("VENTURE_OWNER_API_TOKEN", ""))

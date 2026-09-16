#!/usr/bin/env python3
"""Minimal HTTP boundary for the capability broker."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from kernel.broker import Broker


broker = Broker()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "component": "capability-broker"})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/capabilities/evaluate":
            self._send(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("invalid body length")
            request = json.loads(self.rfile.read(length))
            result = broker.evaluate(request)
            self._send(200, result)
        except (ValueError, TypeError, json.JSONDecodeError, KeyError) as exc:
            self._send(400, {"decision": "deny", "reasons": ["malformed capability request", str(exc)], "grant": None})
        except Exception:
            self._send(503, {"decision": "deny", "reasons": ["broker failure"], "grant": None})

    def log_message(self, *_):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8443), Handler).serve_forever()

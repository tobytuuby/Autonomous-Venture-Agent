"""Restricted client for retrieving signed preparations via mutual TLS.

Only reads assignments. Never signs, executes or authorizes remote commands.
"""
import http.client
import json
import ssl
from urllib.parse import urlsplit
from agents.ceo.cross_vm_transport import verify_assignment
from agents.ceo.cross_vm_poll_server import PATH


class PreparationPollClient:
    def __init__(self, endpoint, *, ca_file, client_cert, client_key, actors,
                 ceo_id, manager_id, consume_nonce, timeout=10):
        url = urlsplit(endpoint)
        if (url.scheme != "https" or url.path != PATH or url.query or url.fragment
                or url.username or url.password or not url.hostname):
            raise ValueError("exact HTTPS polling endpoint required")
        self.host, self.port = url.hostname, url.port or 443
        self.timeout = timeout
        self.context = ssl.create_default_context(cafile=ca_file)
        self.context.load_cert_chain(client_cert, client_key)
        self.actors = actors
        self.ceo_id, self.manager_id = ceo_id, manager_id
        self.consume_nonce = consume_nonce

    def poll(self):
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            conn.request("GET", PATH, headers={"Accept": "application/json"})
            res = conn.getresponse()
            if res.status != 200:
                raise RuntimeError("poll denied")
            raw = res.read(65537)
            if len(raw) > 65536:
                raise ValueError("oversized response")
            payload = json.loads(raw)
            if type(payload) is not dict or set(payload) != {"assignments"}:
                raise ValueError("unexpected poll response")
            assignments = payload["assignments"]
            if type(assignments) is not list or len(assignments) > 10:
                raise ValueError("invalid assignment batch")
            return [verify_assignment(item, self.actors,
                    ceo_id=self.ceo_id, manager_id=self.manager_id,
                    consume_nonce=self.consume_nonce) for item in assignments]
        finally:
            conn.close()

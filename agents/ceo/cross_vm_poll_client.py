"""Restricted client for retrieving signed preparations via mutual TLS.

Retrieves untrusted assignments and posts signed receipts. Never executes commands.
"""
import http.client
import json
import ssl
from urllib.parse import urlsplit
from agents.ceo.cross_vm_transport import verify_assignment, _object, MAX_ACK

ACK_PATH = "/v1/assignments/ack"
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

    def fetch(self):
        """Fetch untrusted data; durable receiver must verify before accepting."""
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            conn.request("GET", PATH, headers={"Accept": "application/json"})
            res = conn.getresponse()
            if res.status != 200:
                raise RuntimeError("poll denied")
            raw = res.read(65537)
            if len(raw) > 65536:
                raise ValueError("oversized response")
            payload = json.loads(raw, object_pairs_hook=_object)
            if type(payload) is not dict or set(payload) != {"assignments"}:
                raise ValueError("unexpected poll response")
            assignments = payload["assignments"]
            if type(assignments) is not list or len(assignments) > 10:
                raise ValueError("invalid assignment batch")
            return assignments
        finally:
            conn.close()

    def poll(self):
        return [verify_assignment(item, self.actors,
                ceo_id=self.ceo_id, manager_id=self.manager_id,
                consume_nonce=self.consume_nonce) for item in self.fetch()]

    def acknowledge(self, envelope):
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        if len(raw) > MAX_ACK:
            raise ValueError("oversized acknowledgement")
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            conn.request("POST", ACK_PATH, body=raw, headers={"Content-Type": "application/json"})
            res = conn.getresponse()
            if res.status != 200:
                raise RuntimeError("acknowledgement denied")
            raw = res.read(MAX_ACK + 1)
            if len(raw) > MAX_ACK:
                raise ValueError("oversized acknowledgement response")
            result = json.loads(raw, object_pairs_hook=_object)
            if (type(result) is not dict or set(result) != {"task_id", "duplicate"}
                    or result["task_id"] != envelope["body"]["task_id"]
                    or type(result["duplicate"]) is not bool):
                raise ValueError("uncorrelated acknowledgement response")
            return result
        finally:
            conn.close()

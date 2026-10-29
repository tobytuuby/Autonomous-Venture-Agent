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


def verify_reservation(payload, result):
    """Require an exact receipt for this intent before any paid inference."""
    from agents.ceo.escalation_inbox import canonical, digest
    expected = dict(reserved=True, request_sha256=digest(canonical(payload).encode()),
        maximum_output_tokens=payload["policy"]["maximum_output_tokens"],
        scope="PREPARATION_ONLY")
    if (type(result) is not dict or result != expected
            or result.get("reserved") is not True
            or type(result.get("maximum_output_tokens")) is not int):
        raise ValueError("uncorrelated reservation response")
    return result


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



    def submit_assignment(self, envelope):
        """CEO-only signed assignment ingress; broker validates role and nonce."""
        from agents.ceo.escalation_inbox import canonical
        from kernel.broker.isolated_mtls import CEO_SUBMIT_PATH
        raw = canonical(envelope).encode()
        if len(raw) > MAX_ACK:
            raise ValueError("oversized signed submission")
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            conn.request("POST", CEO_SUBMIT_PATH, body=raw,
                         headers={"Content-Type": "application/json"})
            res = conn.getresponse()
            if res.status != 200:
                raise ValueError("broker assignment submission denied")
            data = res.read(1025)
            if len(data) > 1024:
                raise ValueError("oversized submission response")
            result = json.loads(data, object_pairs_hook=_object)
            if (type(result) is not dict or set(result) != {"accepted", "duplicate", "task_id"}
                    or result["accepted"] is not True or type(result["duplicate"]) is not bool
                    or result["task_id"] != envelope["body"]["task_id"]):
                raise ValueError("uncorrelated submission")
            return result
        finally:
            conn.close()

    def assignment_record(self, task_id):
        """CEO-only status; broker never grants database access."""
        from kernel.broker.isolated_mtls import CEO_STATUS_PREFIX
        import re
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,119}", task_id):
            raise ValueError("invalid task identity")
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            conn.request("GET", CEO_STATUS_PREFIX + task_id)
            res = conn.getresponse()
            if res.status != 200:
                raise ValueError("broker status denied")
            data = res.read(65537)
            if len(data) > 65536:
                raise ValueError("oversized broker record")
            result = json.loads(data, object_pairs_hook=_object)
            if type(result) is not dict or set(result) != {"record"}:
                raise ValueError("unexpected broker status")
            record = result["record"]
            if record is not None and (
                    type(record) is not dict or
                    set(record) != {"assignment", "state", "acknowledgement"} or
                    record["assignment"]["body"]["task_id"] != task_id or
                    record["state"] not in ("PENDING", "ACKNOWLEDGED")):
                raise ValueError("corrupt broker record")
            return record
        finally:
            conn.close()

    def execute_provider(self, payload):
        """Bounded paid call is broker-side only, after central reservation."""
        from agents.ceo.provider_gateway import EXECUTE_PATH, MAX_EXECUTE
        from agents.ceo.escalation_inbox import canonical
        raw = canonical(payload).encode()
        if len(raw) > MAX_EXECUTE:
            raise ValueError("oversized inference request")
        conn = http.client.HTTPSConnection(self.host, self.port,
            timeout=max(self.timeout, 50), context=self.context)
        try:
            conn.request("POST", EXECUTE_PATH, body=raw,
                         headers={"Content-Type": "application/json"})
            res = conn.getresponse()
            if res.status != 200:
                raise ValueError("broker provider execution denied or ambiguous")
            reply = res.read(16385)
            if len(reply) > 16384:
                raise ValueError("oversized inference response")
            value = json.loads(reply, object_pairs_hook=_object)
            if (type(value) is not dict or set(value) != {"result"}
                    or type(value["result"]) is not dict
                    or value["result"].get("tool_call") is not None
                    or type(value["result"].get("decision")) is not dict
                    or type(value["result"]["decision"].get("content")) is not str):
                raise ValueError("untrusted broker provider result")
            return value["result"]
        finally:
            conn.close()

    def reserve_provider(self, payload):
        """Reserve through the same verified mTLS origin; no redirects or fallback."""
        from agents.ceo.provider_reservation import RESERVATION_PATH, MAX_RESERVATION
        from agents.ceo.escalation_inbox import canonical
        raw = canonical(payload).encode()
        if len(raw) > MAX_RESERVATION:
            raise ValueError("oversized reservation")
        conn = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout, context=self.context)
        try:
            conn.request("POST", RESERVATION_PATH, body=raw,
                         headers={"Content-Type": "application/json"})
            res = conn.getresponse()
            if res.status != 200:
                raise ValueError("central reservation denied or unavailable")
            reply = res.read(1025)
            if len(reply) > 1024:
                raise ValueError("oversized reservation response")
            result = json.loads(reply, object_pairs_hook=_object)
            return verify_reservation(payload, result)
        finally:
            conn.close()

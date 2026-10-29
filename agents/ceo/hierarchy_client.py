"""Authenticated role-specific remote hierarchy interface using existing mTLS."""
import json
import ssl
import urllib.error
import urllib.request
from agents.ceo.escalation_inbox import canonical
from agents.ceo.hierarchy_gateway import STATE_PREFIX, COMMAND_PATH, ARTIFACT_PATH, ARTIFACT_PREFIX
from agents.ceo.hierarchy_gateway import valid_id

MAX_JSON = 32000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("hierarchy TLS redirect denied")


class HierarchyClient:
    def __init__(self, endpoint, *, ca_file, client_cert, client_key):
        if (type(endpoint) is not str or not endpoint.startswith("https://")
                or not endpoint.endswith("/v1/assignments/pending")):
            raise ValueError("existing pinned broker endpoint required")
        self.base = endpoint[:-len("/v1/assignments/pending")]
        context = ssl.create_default_context(cafile=str(ca_file))
        context.load_cert_chain(certfile=str(client_cert), keyfile=str(client_key))
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context), NoRedirect())

    def _request(self, method, path, payload=None):
        raw = canonical(payload).encode("utf-8") if payload is not None else None
        if raw is not None and len(raw) > 16000:
            raise ValueError("oversized signed request")
        req = urllib.request.Request(self.base + path, method=method,
              data=raw, headers={"Content-Type":"application/json"} if raw else {})
        try:
            with self.opener.open(req, timeout=48 if "inference" in path else 12) as response:
                if response.status != 200:
                    raise ValueError("broker denied hierarchy request")
                content = response.read(MAX_JSON + 1)
        except urllib.error.HTTPError as exc:
            raise ValueError("broker hierarchy request failed with HTTP " + str(exc.code)) from exc
        if len(content) > MAX_JSON:
            raise ValueError("unbounded broker reply denied")
        return json.loads(content)

    def read(self, workflow_id):
        r = self._request("GET", STATE_PREFIX + valid_id(workflow_id))
        if type(r) is not dict or set(r) != {"state"}:
            raise ValueError("unexpected hierarchy state")
        return r["state"]

    def apply(self, command, signature):
        r = self._request("POST", COMMAND_PATH,
                          dict(command=command, signature=signature))
        if type(r) is not dict or set(r) != {"state"}:
            raise ValueError("unexpected hierarchy apply response")
        return r["state"]

    def store(self, ref, content):
        if type(content) is not bytes:
            raise ValueError("artifact bytes required")
        r = self._request("POST", ARTIFACT_PATH,
                          dict(ref=ref, content=content.decode("utf-8")))
        if r != {"stored": True}:
            raise ValueError("artifact store not committed")

    def load(self, ref):
        if type(ref) is not str or not ref.startswith("preparation-"):
            raise ValueError("artifact reference denied")
        r = self._request("GET", ARTIFACT_PREFIX + ref)
        if type(r) is not dict or set(r) != {"content"} or type(r["content"]) is not str:
            raise ValueError("artifact response invalid")
        return r["content"].encode("utf-8")

    def bootstrap_prepare(self, payload):
        from agents.ceo.hierarchy_gateway import BOOTSTRAP_PREPARE_PATH
        r=self._request("POST",BOOTSTRAP_PREPARE_PATH,payload)
        if type(r) is not dict or set(r)!={"handoff"}:
            raise ValueError("unexpected owner fixture handoff")
        return r["handoff"]

    def bootstrap_commit(self, command, signature):
        from agents.ceo.hierarchy_gateway import BOOTSTRAP_COMMIT_PATH
        r=self._request("POST",BOOTSTRAP_COMMIT_PATH,
                        dict(command=command,signature=signature))
        if type(r) is not dict or set(r)!={"state"}:
            raise ValueError("unexpected workflow genesis")
        return r["state"]

    def worker_reserve(self, payload):
        return self._request("POST", "/v1/inference/worker-reservations", payload)

    def worker_execute(self, payload):
        return self._request("POST", "/v1/inference/worker-execute", payload)

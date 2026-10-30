"""Negative-boundary tests for the owner API adapter."""
import base64
import http.client
from contextlib import closing
import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from agents.ceo.owner_api import handler_factory
from agents.ceo.owner_idea_inbox import OwnerIdeaInbox


class OwnerAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        discovery = root / "discovery.sqlite"
        self.reviewdb = root / "review.sqlite"
        with closing(sqlite3.connect(discovery)) as db:
            db.execute("CREATE TABLE discovery(cycle_id TEXT, result TEXT, state TEXT, created_utc TEXT)")
            db.execute("INSERT INTO discovery VALUES(?,?,?,?)", (
                "cycle-1", json.dumps({"proposals": [{"title": "Sample"}]}),
                "COMPLETE", "2026-10-30"))
            db.commit()
        inbox = OwnerIdeaInbox(discovery, self.reviewdb)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(inbox, "x" * 40))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, payload=None, authorized=True, intent=True):
        headers = {"Content-Type": "application/json"}
        if authorized:
            headers["Authorization"] = "Bearer " + "x" * 40
        if intent:
            headers["X-Owner-Intent"] = "explicit"
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=headers)
        response = conn.getresponse()
        status, raw = response.status, response.read()
        conn.close()
        return status, json.loads(raw)

    def test_rejects_unauthorized_and_unknown_routes(self):
        self.assertEqual(self.request("GET", "/v1/owner/ideas", authorized=False)[0], 401)
        self.assertEqual(self.request("GET", "/other")[0], 404)
        self.assertEqual(self.request("POST", "/other", {})[0], 404)

    def test_digest_bound_decision_and_duplicate(self):
        ideas = self.request("GET", "/v1/owner/ideas")[1]["ideas"]
        self.assertEqual(len(ideas), 1)
        review = dict(cycle_id="cycle-1", proposal_digest=ideas[0]["digest"],
                      decision="APPROVE_FOR_RESEARCH", reason="")
        self.assertEqual(self.request("POST", "/v1/owner/reviews", review, intent=False)[0], 403)
        self.assertEqual(self.request("POST", "/v1/owner/reviews", {**review, "proposal_digest": "a"*64})[0], 409)
        status, result = self.request("POST", "/v1/owner/reviews", review)
        self.assertEqual(status, 200)
        self.assertFalse(result["venture_admitted"])
        self.assertFalse(result["capital_allocated"])
        self.assertEqual(self.request("POST", "/v1/owner/reviews", review)[0], 409)
        self.assertEqual(self.request("GET", "/v1/owner/ideas")[1]["ideas"][0]["review"]["decision"], "APPROVE_FOR_RESEARCH")

    def test_token_variations_and_paths(self):
        for value in ["bearer " + "x"*40, "Bearer  " + "x"*40,
                      "Bearer " + "x"*40 + " ", "Basic " + "x"*40]:
            conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
            conn.request("GET", "/v1/owner/ideas", headers={"Authorization": value})
            response = conn.getresponse()
            self.assertEqual(response.status, 401)
            response.read()
            conn.close()
        self.assertEqual(self.request("GET", "/v1/owner/ideas%00")[0], 404)
        self.assertEqual(self.request("GET", "/v1/owner/../ideas")[0], 404)

    def test_invalid_http_framing(self):
        for headers in [
            {"Content-Length": "-1"},
            {"Content-Length": "100000"},
            {"Content-Length": "garbage"},
            {"Transfer-Encoding": "chunked"},
        ]:
            conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
            supplied = {"Authorization": "Bearer " + "x"*40,
                        "X-Owner-Intent": "explicit", **headers}
            conn.putrequest("POST", "/v1/owner/reviews")
            for k, v in supplied.items():
                conn.putheader(k, v)
            conn.endheaders()
            response = conn.getresponse()
            self.assertEqual(response.status, 409)
            response.read()
            conn.close()

    def test_concurrent_review_submission_only_one_wins(self):
        from concurrent.futures import ThreadPoolExecutor
        ideas = self.request("GET", "/v1/owner/ideas")[1]["ideas"]
        payload = dict(cycle_id="cycle-1", proposal_digest=ideas[0]["digest"],
                       decision="REJECT", reason="test")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.request("POST", "/v1/owner/reviews", payload)[0], range(8)))
        self.assertEqual(results.count(200), 1)
        self.assertEqual(results.count(409), 7)

    def test_rejects_extra_fields_and_unauthorized_post(self):
        payload = dict(cycle_id="cycle-1", proposal_digest="0"*64,
                       decision="REJECT", reason="", grant_capital=True)
        self.assertEqual(self.request("POST", "/v1/owner/reviews", payload, authorized=False)[0], 401)
        self.assertEqual(self.request("POST", "/v1/owner/reviews", payload)[0], 409)


if __name__ == "__main__":
    unittest.main()

"""Isolated signed-state and loopback mTLS count-query evidence; no live access."""
import copy
import json
import sqlite3
import threading
import unittest
from unittest.mock import patch, Mock

from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_gateway import WORKER_COUNTS_PREFIX
from agents.ceo.hierarchy_research_daemon import worker_round_reservation_count, hold_exhausted_research
from kernel.broker.isolated_mtls import isolated_server
from tests import test_broker_isolated_mtls as tls
from tests import test_research_continuation as research


class ResearchCountTests(unittest.TestCase):
    setUpClass = classmethod(tls.BrokerMtlsTests.setUpClass.__func__)
    tearDownClass = classmethod(tls.BrokerMtlsTests.tearDownClass.__func__)
    request = tls.BrokerMtlsTests.request

    def setUp(self):
        self.fx = research.ResearchContinuationTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.addCleanup(patch.stopall)
        patch("agents.ceo.service_identity.AUTHORITY_DIRECTORY", self.fx.fx.base).start()
        self.fx.resources.chmod(0o600)
        self.fx.fx.base.chmod(0o700)
        self.server = isolated_server(host="127.0.0.1", port=0,
            server_cert=self.paths["server"][0], server_key=self.paths["server"][1],
            client_ca=self.ca, capability_pins=[self.pin("cap")],
            polling_pins=[self.pin("poll")], ceo_reservation_pins=[self.pin("other")],
            ceo_reservation_actor="service-ceo",
            worker_pins=[self.pin("worker-a")], worker_actors={self.pin("worker-a"): "worker-a"},
            hierarchy=self.fx.gate)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.srv = self.server
        self.addCleanup(self.stop_server)
        self.client = HierarchyClient(
            "https://localhost:"+str(self.server.server_port)+"/v1/assignments/pending",
            ca_file=self.ca, client_cert=self.paths["other"][0], client_key=self.paths["other"][1])

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_tls_roles_exact_workflow_and_missing_state_denied(self):
        path = WORKER_COUNTS_PREFIX + self.fx.flow
        for who in ("cap", "poll", "worker-a", "rogue"):
            self.assertEqual(self.request(who, "GET", path)[0], 403)
        self.assertEqual(self.request("other", "POST", path, "{}")[0], 404)
        for suffix in ("?round=1", "-retry", "/extra", "%2f", ""):
            target = path + suffix if suffix else WORKER_COUNTS_PREFIX + "research-"+"0"*24
            self.assertEqual(self.request("other", "GET", target)[0], 400)
        self.assertEqual(self.client.worker_research_counts(self.fx.state())["round_count"], 0)

    def test_retained_counts_read_only_modes_and_stale_snapshot(self):
        # Legacy R1 reservations count even without the supplemental charge table.
        with sqlite3.connect(self.fx.resources) as db:
            db.execute("CREATE TABLE worker_reservations(identity TEXT PRIMARY KEY, request TEXT)")
            db.execute("INSERT INTO worker_reservations VALUES(?,?)",
                       ("legacy", json.dumps(dict(workflow_id=self.fx.flow))))
        prior = self.fx.state()
        self.assertEqual(worker_round_reservation_count(self.client, prior), 1)
        self.fx.apply(self.fx.continuation())
        self.fx.delegate()
        for n in range(4):
            self.fx.reserve(self.fx.payload("count-"+str(n)))
        paths = [self.fx.resources, self.fx.gate.directory/"workflow.sqlite"]
        before = [p.read_bytes() for p in paths]
        result = self.client.worker_research_counts(self.fx.state())
        self.assertEqual((result["round"], result["round_count"], result["venture_count"]), (2, 4, 5))
        self.assertEqual([p.read_bytes() for p in paths], before)
        self.assertEqual(self.fx.resources.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.fx.fx.base.stat().st_mode & 0o777, 0o700)
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.client.worker_research_counts(prior)
        with self.assertRaisesRegex(ValueError, "quota exhausted"):
            self.fx.reserve(self.fx.payload("over"))

    def test_missing_corrupt_ledger_and_unsigned_state_fail_closed(self):
        self.fx.resources.unlink()
        with self.assertRaisesRegex(ValueError, "HTTP 503"):
            self.client.worker_research_counts(self.fx.state())
        self.assertFalse(self.fx.resources.exists())
        self.fx.resources.write_bytes(b"not sqlite")
        with self.assertRaisesRegex(ValueError, "HTTP 503"):
            self.client.worker_research_counts(self.fx.state())
        self.fx.resources.unlink()
        with sqlite3.connect(self.fx.resources) as db:
            db.execute("CREATE TABLE worker_reservations(identity TEXT, request TEXT)")
            db.execute("INSERT INTO worker_reservations VALUES('bad', '{}')")
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            self.client.worker_research_counts(self.fx.state())
        state = self.fx.state()
        with sqlite3.connect(self.fx.gate.directory/"workflow.sqlite") as db:
            changed = copy.deepcopy(state)
            changed["evidence"]["research-approval-"+"b"*24] = "b"*64
            db.execute("UPDATE inbox SET snapshot=? WHERE id=?", (json.dumps(changed), self.fx.flow))
        with self.assertRaisesRegex(ValueError, "HTTP 400"):
            self.client.worker_research_counts(state)

    def test_client_rejects_invalid_counts_and_query_errors(self):
        snapshot = self.fx.state()
        good = self.client.worker_research_counts(snapshot)
        for field, value in (("round_count", True), ("round_count", -1),
                             ("round_count", 1), ("venture_count", "0"),
                             ("workflow_id", "research-other"), ("snapshot_sha256", "0"*64),
                             ("round", 2)):
            with patch.object(self.client, "_request", return_value=dict(good, **{field:value})):
                with self.assertRaises(ValueError):
                    self.client.worker_research_counts(snapshot)
        client = Mock()
        client.worker_research_counts.side_effect = ValueError("denied")
        snapshot["state"] = "WORKER_PENDING"
        with self.assertRaisesRegex(ValueError, "denied"):
            hold_exhausted_research(client, dict(role="ceo", actor_id="service-ceo"), snapshot, 4)
        client.apply.assert_not_called()

    def test_round_four_and_cumulative_twelve_trigger_existing_hold_path(self):
        # Stop at the existing safety check to prove both ceilings select hold,
        # even when a configured override is greater than four.
        snapshot = self.fx.state()
        snapshot["state"] = "WORKER_PENDING"
        for counts in (dict(round_count=4, venture_count=4),
                       dict(round_count=0, venture_count=12)):
            client = Mock()
            client.worker_research_counts.return_value = counts
            with patch("agents.ceo.hierarchy_research_daemon.allowed_config",
                       side_effect=ValueError("hold safety check")):
                with self.assertRaisesRegex(ValueError, "hold safety check"):
                    hold_exhausted_research(client, dict(role="ceo", actor_id="service-ceo"),
                                           snapshot, 16)
            client.apply.assert_not_called()

"""Whole synthetic broker process replacement; no installed service operations."""
import http.client
import os
import select
import signal
import threading
import unittest

from agents.ceo.ceo_broker import execute_ceo
from agents.ceo.escalation_inbox import canonical
from agents.ceo.hierarchy_gateway import HierarchyGateway
from agents.ceo.hierarchy_providers import RecoveryImpossible
from tests import test_ceo_broker as fixture
from tests import test_ceo_research_mtls_acceptance as base


class DeploymentBrokerRestartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CEOBrokerTests.setUpClass()
        tls = fixture.CEOBrokerTests.tls
        tls.srv.shutdown()
        tls.srv.server_close()
        tls.thread.join(timeout=5)

    @classmethod
    def tearDownClass(cls):
        fixture.CEOBrokerTests.tearDownClass()

    def setUp(self):
        self.fx = fixture.CEOBrokerTests(methodName="runTest")
        self.addCleanup(self.fx.doCleanups)
        threads = set(threading.enumerate())
        self.fx.setUp()
        self.fx.pending()
        self.fx.reserve()
        self.fx.server.shutdown()
        self.fx.server.server_close()
        for thread in set(threading.enumerate()) - threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(threading.active_count(), 1)
        self.pid = None
        self.addCleanup(self.stop)

    def start(self, mode):
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                cfg = dict(self.fx.server_kwargs, port=self.fx.server.server_port)
                gateway = HierarchyGateway(self.fx.gate.directory, self.fx.gate.actors)
                cfg["hierarchy"] = gateway
                def provider(request, tools):
                    if mode == "PENDING":
                        os._exit(82)
                    raise AssertionError("completed or ambiguous provider replay")
                # Execution validates provider identity even for durable replay.
                provider.endpoint = self.fx.models["ceo"].endpoint
                provider.model = self.fx.models["ceo"].model
                def execute(payload, *, actor):
                    result = execute_ceo(payload, actor=actor, hierarchy=gateway,
                        provider=self.fx.models["ceo"] if mode == "COMPLETE" else provider)
                    if mode == "COMPLETE":
                        os._exit(83)  # Durable response committed, no wire reply.
                    return result
                cfg["ceo_execute"] = execute
                server = base.isolated_server(**cfg)
                os.write(write_fd, b"READY")
                os.close(write_fd)
                server.serve_forever()
            except BaseException:
                import traceback
                traceback.print_exc()
                os._exit(99)
            os._exit(0)
        self.pid = pid
        os.close(write_fd)
        try:
            self.assertTrue(select.select([read_fd], [], [], 8)[0])
            self.assertEqual(os.read(read_fd, 5), b"READY")
        finally:
            os.close(read_fd)
        return pid

    def stop(self):
        if self.pid is not None:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
            self.pid = None

    def crash_request(self, mode):
        self.start(mode)
        with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError)):
            self.fx.client().ceo_execute(self.fx.payload)
        pid, status = os.waitpid(self.pid, 0)
        self.pid = None
        self.assertTrue(os.WIFEXITED(status))
        self.assertEqual(os.WEXITSTATUS(status), 83 if mode == "COMPLETE" else 82)
        return pid

    def test_completed_wire_loss_fresh_broker_and_ceo_response_reuse(self):
        first = self.crash_request("COMPLETE")
        committed = self.fx.ledger_bytes()
        charged = self.fx.counts()
        second = self.start("FORBID")
        self.assertNotEqual(first, second)
        self.assertEqual(self.fx.client().ceo_proof(self.fx.payload)["execution_status"], "COMPLETE")
        packet = self.fx.resume()  # Existing review recovery against new broker PID.
        self.assertEqual(packet["state"], "COMPLETE")
        self.assertEqual(self.fx.resume(), packet)
        self.assertEqual(self.fx.ledger_bytes(), committed)
        self.assertEqual(self.fx.counts(), charged)
        self.fx.reopen(self.fx.original_state)
        print(canonical(dict(scenario="WHOLE_BROKER_COMPLETE_RESTART",
            original_pid=first, replacement_pid=second, provider_replay="FORBIDDEN",
            ledger="BYTE_IDENTICAL", signed_workflow="VERIFIED")), flush=True)

    def test_pending_wire_loss_fresh_broker_keeps_quota_and_holds(self):
        first = self.crash_request("PENDING")
        pending = self.fx.ledger_bytes()
        charged = self.fx.counts()
        second = self.start("FORBID")
        self.assertEqual(self.fx.client().ceo_proof(self.fx.payload)["execution_status"], "PENDING")
        for _ in range(2):
            with self.assertRaisesRegex(RecoveryImpossible, "PROVIDER_EXECUTION_AMBIGUOUS"):
                self.fx.resume()
        self.assertEqual(self.fx.ledger_bytes(), pending)
        self.assertEqual(self.fx.counts(), charged)
        self.fx.reopen(self.fx.original_state)
        print(canonical(dict(scenario="WHOLE_BROKER_PENDING_RESTART",
            original_pid=first, replacement_pid=second, outcome="HELD",
            ledger="BYTE_IDENTICAL", signed_workflow="VERIFIED")), flush=True)

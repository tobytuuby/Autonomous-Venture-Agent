"""C1 synthetic admission/drain evidence; no live state or provider access."""
import io
import http.client
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kernel.broker.isolated_mtls import MaintenanceAdmission, MaintenanceDenied, handler_for
from kernel.broker import mtls_server

ROOT = Path(__file__).resolve().parents[1]


def assert_wire_denied(test, request):
    # Admission rejects before reading even the request line. TLS may close
    # while http.client is still writing a separately sent POST body; that
    # transport rejection is also fail-closed, not a guaranteed JSON response.
    try:
        response = request()
    except (BrokenPipeError, ConnectionResetError, http.client.RemoteDisconnected):
        return
    test.assertEqual(response, (503, {"error": "maintenance_denied"}))


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="c1-maintenance-", dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.directory.chmod(0o700)
        self.path = self.directory / "control"
        self.path.write_bytes(b"OPEN\n")
        self.active = self.directory / "control.active"
        self.active.write_bytes(b"")
        for path in (self.path, self.active):
            path.chmod(0o600)
        self.identity = ":".join(str(n) for path in (self.path, self.active, self.directory)
                                 for n in (path.stat().st_dev, path.stat().st_ino))
        self.gate = MaintenanceAdmission(str(self.path), self.identity)

    def denied(self, gate=None):
        with self.assertRaises(MaintenanceDenied):
            with (gate or self.gate).request():
                self.fail("unsafe admission")

    def test_close_precedes_drain_and_explicit_release_waits_for_all_threads(self):
        with self.gate.request(), self.gate.request():
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(0.02):
                    self.fail("active work drained")
            self.assertEqual(self.path.read_bytes(), b"CLOSED\n")
            self.denied()
            with self.assertRaises(MaintenanceDenied):
                self.gate.release()
        with self.gate.drain(0):
            with self.assertRaises(MaintenanceDenied):
                self.gate.release()
        self.denied()
        self.gate.release()
        with self.gate.request():
            pass

    def test_exception_and_timeout_leave_closed(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with self.gate.request():
                raise RuntimeError("synthetic callback")
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with self.gate.drain(0):
                raise RuntimeError("synthetic operator")
        self.denied(MaintenanceAdmission(str(self.path), self.identity))
        for timeout in (-1, float("nan"), float("inf"), 301, True):
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(timeout):
                    pass

    def test_operator_death_restart_and_cross_process_activity(self):
        code = """import sys
from kernel.broker.isolated_mtls import MaintenanceAdmission
gate = MaintenanceAdmission(sys.argv[1], sys.argv[2])
with gate.request():
    print('accepted', flush=True)
    sys.stdin.readline()
with gate.drain(1):
    print('closed', flush=True)
    sys.stdin.readline()
"""
        proc = subprocess.Popen([sys.executable, "-B", "-c", code, str(self.path),
                                 self.identity], cwd=ROOT, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "accepted")
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(0.02):
                    pass
            proc.stdin.write("\n")
            proc.stdin.flush()
            self.assertEqual(proc.stdout.readline().strip(), "closed")
            proc.kill()
            proc.wait(timeout=3)
            restarted = MaintenanceAdmission(str(self.path), self.identity)
            self.denied(restarted)
            restarted.release()
            with restarted.request():
                pass
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=3)

    def test_missing_malformed_symlink_hardlink_modes_ownership_and_replacement(self):
        for data in (b"", b"OPEN", b"OPEN\nextra", b"{}", b"CLOSED\nextra"):
            self.path.write_bytes(data)
            self.denied()
        self.path.write_bytes(b"OPEN\n")
        for path in (self.path, self.active, self.directory):
            original = path.stat().st_mode & 0o777
            path.chmod(0o777)
            self.denied()
            path.chmod(original)
        info = os.stat_result((0o100600, self.path.stat().st_ino,
            self.path.stat().st_dev, 1, os.geteuid()+1, 0, 5, 0, 0, 0))
        with patch("os.fstat", return_value=info):
            self.denied()
        for path in (self.path, self.active):
            saved = path.with_name(path.name + ".saved")
            path.rename(saved)
            self.denied()
            path.symlink_to(saved)
            self.denied()
            path.unlink()
            os.link(saved, path)
            self.denied()  # nlink=2
            path.unlink()
            path.write_bytes(b"" if path == self.active else b"OPEN\n")
            path.chmod(0o600)
            self.denied()
            with self.assertRaises(MaintenanceDenied):
                MaintenanceAdmission(str(self.path), self.identity)
            path.unlink()
            saved.rename(path)
        self.active.write_bytes(b"not a lock file")
        self.denied()

    def test_replacement_between_open_and_lock_denies(self):
        original = self.gate._lock
        def replace(fd, mode, deadline):
            original(fd, mode, deadline)
            self.path.rename(self.directory / "old")
            self.path.write_bytes(b"OPEN\n")
            self.path.chmod(0o600)
        with patch.object(self.gate, "_lock", side_effect=replace):
            self.denied()

    def test_config_absence_legacy_partial_blank_or_malformed_denies_before_startup(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(mtls_server.maintenance_from_environment())
        names = ("VENTURE_BROKER_MAINTENANCE_CONTROL", "VENTURE_BROKER_MAINTENANCE_IDENTITY")
        for env in ({names[0]: ""}, {names[1]: self.identity},
                    {names[0]: str(self.path), names[1]: "bad"},
                    {names[0]: str(self.path), names[1]: ""}):
            with patch.dict(os.environ, env, clear=True), self.assertRaises((RuntimeError, MaintenanceDenied)):
                mtls_server.main()
        with self.gate.drain(0):
            pass
        env = dict(zip(names, (str(self.path), self.identity)))
        with patch.dict(os.environ, env, clear=True), \
                patch("agents.ceo.cert_renewal.ManagerRenewalMailbox") as mailbox, \
                patch("kernel.broker.mtls_server.ThreadingHTTPServer") as server:
            with self.assertRaises(MaintenanceDenied):
                mtls_server.main()
            mailbox.assert_not_called()
            server.assert_not_called()

    def handler(self, **kwargs):
        cls = handler_for(capability_pins={"a"*64}, polling_pins={"b"*64},
            ceo_reservation_pins={"c"*64}, ceo_reservation_actor="service-ceo",
            reservation_actor="service-manager", worker_pins={"d"*64},
            maintenance=self.gate, **kwargs)
        h = object.__new__(cls)
        h.connection = Mock()
        h.headers = Message()
        h.headers["Content-Length"] = "2"
        h.rfile = io.BytesIO(b"{}")
        h._send = Mock(side_effect=lambda status, body: status)
        return h

    def assert_held(self):
        with self.assertRaises(MaintenanceDenied):
            with self.gate.drain(0):
                self.fail("callback not covered")
        self.assertEqual(self.path.read_bytes(), b"CLOSED\n")

    def test_request_parser_and_inherited_errors_are_admitted_before_dispatch(self):
        from http.server import BaseHTTPRequestHandler
        h = self.handler()
        def parse(_handler):
            self.assert_held()
            raise OSError("synthetic parser failure")
        with patch.object(BaseHTTPRequestHandler, "handle_one_request", parse):
            with self.assertRaisesRegex(OSError, "parser failure"):
                h.handle_one_request()
        with self.gate.drain(0):
            pass
        with patch.object(BaseHTTPRequestHandler, "handle_one_request") as parser:
            self.assertEqual(h.handle_one_request(), 503)
            parser.assert_not_called()
        self.assertTrue(h.close_connection)
        self.gate.release()

    def test_every_callback_family_holds_admission_and_postclose_never_dispatches(self):
        # All current GET callbacks and POST writer families. CSR key/role
        # validation is covered by the real TLS regression; mailbox entry here
        # is covered by the common dispatch wrapper below.
        cases = [
            ("GET", "/v1/assignments/pending", "poll", "pending"),
            ("GET", "/v1/assignments/status/task", "quota-ceo", "status"),
            ("GET", "/v1/certificates/manager/issued", "poll", "issued"),
            ("GET", "/v1/certificates/worker/issued", "worker", "issued"),
            ("GET", "/v1/hierarchy/research", "poll", "research_list"),
            ("GET", "/v1/hierarchy/research-worker-counts/task", "quota-ceo", "worker_research_counts"),
            ("GET", "/v1/hierarchy/state/task", "worker", "state"),
            ("GET", "/v1/hierarchy/artifact/task", "poll", "artifact"),
            ("POST", "/v1/inference/execute", "poll", "execute"),
            ("POST", "/v1/inference/ceo-execute", "quota-ceo", "ceo_execute"),
            ("POST", "/v1/inference/worker-reservations", "worker", "worker_reserve"),
            ("POST", "/v1/inference/worker-execute", "worker", "worker_execute"),
            ("POST", "/v1/hierarchy/bootstrap/prepare", "quota-ceo", "bootstrap_prepare"),
            ("POST", "/v1/hierarchy/bootstrap/commit", "quota-ceo", "bootstrap_commit"),
            ("POST", "/v1/hierarchy/command", "poll", "apply"),
            ("POST", "/v1/hierarchy/artifact", "worker", "store"),
            ("POST", "/v1/assignments/submit", "quota-ceo", "submit"),
            ("POST", "/v1/assignments/ack", "poll", "acknowledge"),
            ("POST", "/v1/inference/reservations", "poll", "reservation"),
            ("POST", "/v1/inference/ceo-proof", "quota-ceo", "proof"),
            ("POST", "/v1/capabilities/evaluate", "capability", "capability"),
        ]
        from agents.ceo.provider_reservation import RESERVATION_PATH
        cases[-3] = ("POST", RESERVATION_PATH, "poll", "reservation")
        for method, path, role, name in cases:
            with self.subTest(path=path):
                def callback(*args, **kwargs):
                    self.assert_held()
                    return True if name == "submit" else {}
                cb = Mock(side_effect=callback)
                hierarchy = SimpleNamespace(actors={"service-worker": ("worker", b"x"*32)})
                for field in ("research_list", "worker_research_counts", "state", "artifact",
                              "bootstrap_prepare", "bootstrap_commit", "apply", "store"):
                    setattr(hierarchy, field, cb)
                mailbox = SimpleNamespace(issued=cb)
                kw = {field: cb for field in ("pending", "status", "execute", "ceo_execute",
                    "worker_reserve", "worker_execute", "submit", "acknowledge")}
                h = self.handler(hierarchy=hierarchy, cert_mailbox=mailbox,
                                 worker_cert_mailbox=mailbox, **kw)
                h.path = path
                h._role = lambda: role
                with patch("agents.ceo.provider_reservation.reserve_exchange", cb), \
                        patch("agents.ceo.ceo_broker.ceo_proof", cb), \
                        patch("kernel.broker.server.broker.evaluate", cb):
                    getattr(h, "do_" + method)()
                cb.assert_called_once()
                # CLOSED also covers callback response serialization failures.
                cb.reset_mock()
                self.assertEqual(getattr(h, "do_" + method)(), 503)
                cb.assert_not_called()
                self.gate.release()

    def test_body_response_identity_admin_and_callback_exceptions_release(self):
        for stage in ("body", "response", "identity", "callback"):
            with self.subTest(stage=stage):
                cb = Mock(return_value={})
                h = self.handler(execute=cb)
                h.path = "/v1/inference/execute"
                h._role = lambda: "poll"
                if stage == "body":
                    h.rfile.read = lambda size: (self.assert_held() or b"{}")
                elif stage == "response":
                    h._send.side_effect = lambda *args: self.assert_held()
                elif stage == "identity":
                    h.path = "/health"
                    h._role = lambda: (self.assert_held() or None)
                else:
                    cb.side_effect = RuntimeError("synthetic callback")
                h.do_POST()
                # All paths, including swallowed callback exceptions, released.
                with self.gate.drain(0):
                    pass
                self.gate.release()
        for method in ("GET", "POST", "PUT", "DELETE"):
            h = self.handler()
            h.path = "/admin"
            h._role = lambda: None
            h._send.side_effect = lambda *args: self.assert_held()
            getattr(h, "do_" + method)()
            with self.gate.drain(0):
                pass
            self.gate.release()

    def test_inflight_callback_durable_commit_and_wire_exception(self):
        entered, finish = threading.Event(), threading.Event()
        durable = self.directory / "durable"
        def callback(payload):
            entered.set()
            if not finish.wait(3):
                raise AssertionError("test callback timed out")
            with durable.open("wb") as stream:
                stream.write(b"COMPLETE:original-request:charge=1")
                stream.flush()
                os.fsync(stream.fileno())
            return {}
        h = self.handler(execute=callback)
        h.path = "/v1/inference/execute"
        h._role = lambda: "poll"
        h._send.side_effect = OSError("synthetic lost response")
        errors = []
        def run():
            try:
                h.do_POST()
            except OSError as exc:
                errors.append(exc)
        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assert_held()
            self.assertFalse(durable.exists())
        finally:
            finish.set()
            thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertTrue(errors)
        before = durable.read_bytes()
        with self.gate.drain(0):
            pass
        self.gate.release()
        self.assertEqual(durable.read_bytes(), before)


    def test_failed_persistence_and_directory_substitution_never_admit(self):
        with self.gate.drain(0):
            pass
        with patch("os.fsync", side_effect=OSError("synthetic storage failure")):
            with self.assertRaises(MaintenanceDenied):
                self.gate.release()
        self.assertEqual(self.path.read_bytes(), b"CLOSED\n")
        self.denied()
        saved = self.directory.with_name(self.directory.name + "-saved")
        self.directory.rename(saved)
        try:
            self.directory.mkdir(mode=0o700)
            # Even moving the pinned files into a different parent is refused.
            for name in ("control", "control.active"):
                (saved / name).rename(self.directory / name)
            with self.assertRaises(MaintenanceDenied):
                MaintenanceAdmission(str(self.path), self.identity)
        finally:
            for name in ("control", "control.active"):
                (self.directory / name).rename(saved / name)
            self.directory.rmdir()
            saved.rename(self.directory)

    def test_startup_constructors_are_admitted_and_later_requests_are_closed(self):
        def build(gate):
            self.assertIsNotNone(gate)
            self.assert_held()
            return Mock(), Mock()
        env = {"VENTURE_BROKER_MAINTENANCE_CONTROL": str(self.path),
               "VENTURE_BROKER_MAINTENANCE_IDENTITY": self.identity}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(mtls_server, "_configured_server", side_effect=build):
            mtls_server.main()
        with self.gate.drain(0):
            pass


class MaintenanceTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests import test_broker_isolated_mtls as fixture
        cls.fixture = fixture
        with patch("tempfile.tempdir", str(ROOT)):
            fixture.BrokerMtlsTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.BrokerMtlsTests.tearDownClass()

    def setUp(self):
        self.fx = MaintenanceTests(methodName="runTest")
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.gate = self.fx.gate

    def server(self, **kwargs):
        from kernel.broker.isolated_mtls import isolated_server
        tls = self.fixture.BrokerMtlsTests
        server = isolated_server(host="127.0.0.1", port=0,
            server_cert=tls.paths["server"][0], server_key=tls.paths["server"][1],
            client_ca=tls.ca, capability_pins=[tls.pin("cap")],
            polling_pins=[tls.pin("poll")], maintenance=self.gate, **kwargs)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 4)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = tls(methodName="runTest")
        client.srv = server
        return client

    def test_real_tls_get_and_post_inflight_close_then_reject(self):
        for method, path in (("GET", "/v1/assignments/pending"),
                             ("POST", "/v1/inference/execute")):
            with self.subTest(method=method):
                entered, finish = threading.Event(), threading.Event()
                count = []
                def callback(*args):
                    count.append("accepted")
                    entered.set()
                    if not finish.wait(4):
                        raise AssertionError("synthetic callback timeout")
                    return [] if method == "GET" else {}
                client = self.server(pending=callback, execute=callback)
                results = []
                thread = threading.Thread(target=lambda: results.append(
                    client.request("poll", method, path, body="{}" if method == "POST" else None)))
                thread.start()
                try:
                    self.assertTrue(entered.wait(2))
                    self.fx.assert_held()
                    assert_wire_denied(self, lambda: client.request("poll", method, path, body="{}"))
                    self.assertEqual(count, ["accepted"])
                finally:
                    finish.set()
                    thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(results[0][0], 200)
                with self.gate.drain(0):
                    pass
                self.gate.release()

    def test_real_tls_negative_roles_csr_and_missing_control(self):
        mailbox = SimpleNamespace(issued=Mock(return_value="synthetic"),
                                  submit=Mock())
        client = self.server(cert_mailbox=mailbox, worker_pins=[self.fixture.BrokerMtlsTests.pin("other")],
                             worker_cert_mailbox=mailbox)
        for who in (None,):
            with self.assertRaises((ssl.SSLError, OSError)):
                client.request(who, "GET", "/health")
        self.assertEqual(client.request("rogue", "GET", "/health")[0], 403)
        self.assertEqual(client.request("cap", "GET", "/v1/assignments/pending")[0], 403)
        self.assertEqual(client.request("other", "GET", "/v1/certificates/manager/issued")[0], 403)
        self.assertEqual(client.request("poll", "POST", "/v1/inference/worker-execute", "{}")[0], 403)
        tls = self.fixture.BrokerMtlsTests
        csr = self.fx.directory / "manager.csr"
        self.fixture.run("req", "-new", "-key", tls.paths["poll"][1],
                         "-subj", "/CN=synthetic-manager", "-out", csr)
        # A real key-bound CSR reaches submit under a held admission.
        mailbox.submit.side_effect = lambda data: self.fx.assert_held()
        self.assertEqual(client.request("poll", "POST", "/v1/certificates/manager/csr",
                                        csr.read_bytes())[0], 200)
        mailbox.submit.assert_called_once()
        with self.gate.drain(0):
            pass
        for who, method, path in (
                ("poll", "POST", "/v1/certificates/manager/csr"),
                ("other", "POST", "/v1/certificates/worker/csr"),
                ("cap", "GET", "/health"), ("rogue", "GET", "/admin"),
                ("poll", "GET", "/v1/certificates/manager/issued")):
            assert_wire_denied(self, lambda: client.request(who, method, path, "{}"))
        mailbox.issued.assert_not_called()
        self.assertEqual(mailbox.submit.call_count, 1)
        self.gate.release()
        self.fx.path.unlink()
        assert_wire_denied(self, lambda: client.request("cap", "GET", "/health"))


class MaintenanceLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests import test_ceo_broker as fixture
        cls.fixture = fixture
        with patch("tempfile.tempdir", str(ROOT)):
            fixture.CEOBrokerTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.CEOBrokerTests.tearDownClass()

    def setUp(self):
        from tests import test_ceo_research_mtls_acceptance as base
        self.admission = MaintenanceTests(methodName="runTest")
        self.admission.setUp()
        self.addCleanup(self.admission.doCleanups)
        self.gate = self.admission.gate
        self.fx = self.fixture.CEOBrokerTests(methodName="runTest")
        self.addCleanup(self.fx.doCleanups)
        original = base.isolated_server
        def server(**kwargs):
            return original(**dict(kwargs, maintenance=self.gate))
        with patch.object(base, "isolated_server", server):
            self.fx.setUp()

    def test_complete_reuse_closed_denial_release_no_charge_or_provider_duplication(self):
        from agents.ceo.ceo_broker import EXECUTE_PATH
        self.fx.test_readonly_absent_exact_complete_proof_and_response_replay()
        before, counts = self.fx.ledger_bytes(), self.fx.counts()
        calls = len(self.fx.models["ceo"].calls)
        with self.gate.drain(0):
            assert_wire_denied(self, lambda: self.fx.wire("other", EXECUTE_PATH, self.fx.payload))
        self.gate.release()
        self.fx.client().ceo_execute(self.fx.payload)
        self.assertEqual(self.fx.ledger_bytes(), before)
        self.assertEqual(self.fx.counts(), counts)
        self.assertEqual(len(self.fx.models["ceo"].calls), calls)

    def test_negative_roles_under_configured_admission(self):
        self.fx.test_pinned_certificates_and_manager_worker_routes_remain_isolated()

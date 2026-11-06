"""C6 source-only legacy exchange tests. All providers/transports are synthetic."""
from contextlib import ExitStack
import copy
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from agents.ceo import preparation_exchange as exchange
from agents.ceo.escalation_inbox import ROOT, canonical
from kernel.broker.isolated_mtls import MaintenanceAdmission, MaintenanceDenied


class Provider:
    endpoint = "https://fixture.invalid/v1"
    model = "gpt-6-sol"

    def __init__(self, role, callback):
        self.role, self.callback = role, callback

    def __call__(self, request, tools):
        self.callback()
        content = (dict(disposition="PREPARE", instructions=["Synthetic preparation"])
                   if self.role == "ceo" else dict(status="RECEIVED", summary="Synthetic receipt"))
        return dict(tool_call=None, decision=dict(content=canonical(content)))

    def bind_reservation(self, payload):
        pass


def fixtures(stack, config, callback):
    """Real signer/model/checkpoints, in-memory transport and reservation response."""
    stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("C6 network denied")))
    role = config["role"]
    provider = Provider(role, callback)
    client = Mock()
    assignment = json.loads(Path(config["assignment"]).read_text())
    client.fetch.return_value = [assignment]
    records = {}
    client.assignment_record.side_effect = lambda task: records.get(task)
    def submit(value):
        records[value["body"]["task_id"]] = dict(assignment=value, state="PENDING")
        return dict(duplicate=False)
    client.submit_assignment.side_effect = submit
    stack.enter_context(patch.object(exchange, "configured_provider", return_value=provider))
    stack.enter_context(patch("agents.ceo.provider_gateway.RemoteInferenceProvider", return_value=provider))
    stack.enter_context(patch.object(exchange, "PreparationPollClient", return_value=client))
    stack.enter_context(patch.object(exchange.RemoteStandingModel, "_reserve"))
    return client


def child(config_path, marker=None):
    """Separate Python process, real flock and SQLite; never network."""
    config = json.loads(Path(config_path).read_text())
    def provider():
        if marker:
            Path(marker).write_text("provider")
            deadline = time.monotonic() + 10
            while not Path(marker + ".finish").exists():
                if time.monotonic() > deadline:
                    raise AssertionError("synthetic provider timeout")
                time.sleep(.005)
    with ExitStack() as stack:
        fixtures(stack, config, provider)
        exchange.run(config, once=True)


class ExchangeMaintenanceC6Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="c6-", dir=ROOT / "artifacts")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.control = self.home / "control"
        self.active = self.home / "control.active"
        self.control.write_bytes(b"OPEN\n")
        self.active.write_bytes(b"")
        for path in (self.control, self.active):
            path.chmod(0o600)
        identity = ":".join(str(n) for p in (self.control, self.active, self.home)
                            for n in (p.stat().st_dev, p.stat().st_ino))
        self.setting = dict(control=str(self.control), identity=identity)
        self.gate = MaintenanceAdmission(str(self.control), identity)
        keys = {role: Ed25519PrivateKey.generate() for role in ("ceo", "manager")}
        self.context = dict(session_id="c6-session", venture_id="c6-venture",
            ceo_id="ceo", manager_id="manager", objective="Synthetic preparation", rounds=1)
        actors = {role: (role, key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)) for role, key in keys.items()}
        trust = self.home / "trust.json"
        trust.write_text(canonical(dict(actors={actor: dict(role=role, public_key=key.hex())
                         for actor, (role, key) in actors.items()})))
        policy = self.home / "policy.json"
        policy.write_text(canonical(dict(domain="preparation-exchange-usage-v1", enabled=True, epoch=1,
            roles={r: dict(actor_id=r, endpoint=Provider.endpoint, model=Provider.model) for r in keys},
            maximum_requests=4, maximum_output_tokens=512)))
        policy.chmod(0o600)
        self.configs = {}
        for role, key in keys.items():
            (self.home / role).mkdir(mode=0o700)
            seed = self.home / (role + ".seed")
            seed.write_bytes(key.private_bytes(serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw, serialization.NoEncryption()))
            seed.chmod(0o600)
            self.configs[role] = dict(role=role, signing_key=str(seed),
                context=self.context, trust=str(trust), usage_policy=str(policy),
                state_directory=str(self.home / role), endpoint="https://fixture.invalid",
                ca_file=str(trust), client_cert=str(trust), client_key=str(trust),
                assignment=str(self.home / "assignment.json"),
                maintenance_admission=copy.deepcopy(self.setting))
        signer = exchange.RoleSigner(self.configs["ceo"]["signing_key"], "ceo", "ceo", actors)
        assignment = signer.assignment(dict(disposition="PREPARE", instructions=["Synthetic preparation"]),
            manager_id="manager", task_id="c6-session-1", venture_id="c6-venture")
        (self.home / "assignment.json").write_text(canonical(assignment))

    def tree(self):
        return {str(p.relative_to(self.home)): p.read_bytes() for p in self.home.rglob("*")
                if p.is_file() and p not in (self.control, self.active)}

    def test_closed_before_state_sqlite_or_provider_for_both_roles(self):
        with self.gate.drain(0):
            before = self.tree()
            for config in self.configs.values():
                with patch.object(exchange, "ExchangeState") as state, \
                     patch.object(exchange, "configured_provider") as provider:
                    with self.assertRaises(MaintenanceDenied):
                        exchange.run(config, once=True)
                    state.assert_not_called()
                    provider.assert_not_called()
            self.assertEqual(self.tree(), before)

    def test_malformed_and_unsafe_controls_fail_closed(self):
        invalid = [None, False, "", {}, dict(control=str(self.control)),
            dict(self.setting, extra=True), dict(self.setting, identity="0:1"),
            dict(self.setting, identity="+1:2:3:4:5:6"),
            dict(self.setting, control=str(self.home / ".." / self.home.name / "control"))]
        for value in invalid:
            with self.subTest(value=value), patch.object(exchange, "ExchangeState") as state:
                with self.assertRaises(MaintenanceDenied):
                    exchange.run(dict(self.configs["manager"], maintenance_admission=value), once=True)
                state.assert_not_called()
        for mutation in ("missing", "symlink", "replace", "mode", "malformed", "active-mode", "directory-mode"):
            with self.subTest(mutation=mutation):
                if mutation in ("missing", "symlink", "replace"):
                    self.control.rename(self.home / "saved")
                    if mutation == "symlink":
                        self.control.symlink_to(self.home / "saved")
                    elif mutation == "replace":
                        self.control.write_bytes(b"OPEN\n")
                        self.control.chmod(0o600)
                elif mutation == "mode":
                    self.control.chmod(0o644)
                elif mutation == "active-mode":
                    self.active.chmod(0o644)
                elif mutation == "directory-mode":
                    self.home.chmod(0o755)
                else:
                    self.control.write_bytes(b"UNKNOWN\n")
                try:
                    before = self.tree()
                    with self.assertRaises(MaintenanceDenied):
                        exchange.run(self.configs["manager"], once=True)
                    self.assertEqual(self.tree(), before)
                finally:
                    saved = self.home / "saved"
                    if saved.exists():
                        if self.control.exists() or self.control.is_symlink():
                            self.control.unlink()
                        saved.rename(self.control)
                    self.control.chmod(0o600)
                    self.active.chmod(0o600)
                    self.home.chmod(0o700)
                    self.control.write_bytes(b"OPEN\n")

    def test_active_tick_and_teardown_drain_before_sleep_postclose_no_work(self):
        for role in ("ceo", "manager"):
            with self.subTest(role=role):
                config = self.configs[role]
                reached, finish, drained = threading.Event(), threading.Event(), threading.Event()
                errors, calls, closed = [], [], []
                def provider():
                    calls.append(role)
                    reached.set()
                    if not finish.wait(5):
                        raise AssertionError("provider timeout")
                original_close = exchange.ExchangeState.close
                def close(state):
                    # Even WAL teardown must remain active after CLOSED.
                    with self.assertRaises(MaintenanceDenied):
                        with self.gate.drain(0):
                            pass
                    original_close(state)
                    closed.append(True)
                def sleep(seconds):
                    self.assertEqual(seconds, 5)
                    self.assertTrue(closed)
                    self.assertTrue(drained.wait(5))
                    with self.gate.drain(0):
                        # Lifetime duplicate lock still held after SQLite closes.
                        with (Path(config["state_directory"]) / "exchange.lock").open("a") as lock:
                            with self.assertRaises(BlockingIOError):
                                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                def runner():
                    try:
                        with ExitStack() as stack:
                            client = fixtures(stack, config, provider)
                            stack.enter_context(patch.object(exchange.ExchangeState, "close", close))
                            stack.enter_context(patch.object(exchange, "time", SimpleNamespace(sleep=sleep)))
                            with self.assertRaises(MaintenanceDenied):
                                exchange.run(config)
                            self.assertEqual(client.fetch.call_count, 1 if role == "manager" else 0)
                    except BaseException as exc:
                        errors.append(exc)
                def drain():
                    try:
                        with self.gate.drain(5):
                            # Real durable checkpoints must precede quiescence.
                            with sqlite3.connect(Path(config["state_directory"]) / "exchange.sqlite") as db:
                                self.assertEqual(db.execute("SELECT COUNT(*) FROM calls WHERE response IS NOT NULL").fetchone()[0], 1)
                                if role == "manager":
                                    self.assertEqual(db.execute("SELECT sent FROM received").fetchone()[0], 1)
                            drained.set()
                    except BaseException as exc:
                        errors.append(exc)
                thread = threading.Thread(target=runner)
                closer = threading.Thread(target=drain)
                thread.start()
                try:
                    self.assertTrue(reached.wait(5))
                    closer.start()
                    deadline = time.monotonic() + 3
                    while self.control.read_bytes() != b"CLOSED\n" and time.monotonic() < deadline:
                        finish.wait(.005)
                    self.assertEqual(self.control.read_bytes(), b"CLOSED\n")
                    self.assertFalse(drained.is_set())
                finally:
                    finish.set()
                    thread.join(8)
                    if closer.ident is not None:
                        closer.join(8)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertTrue(drained.is_set())
                self.assertEqual(calls, [role])
                before = self.tree()
                with self.assertRaises(MaintenanceDenied):
                    exchange.run(config, once=True)
                self.assertEqual(before, self.tree())
                with sqlite3.connect(Path(config["state_directory"]) / "exchange.sqlite") as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM calls WHERE response IS NOT NULL").fetchone()[0], 1)
                    table = "received" if role == "manager" else "issued"
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 1)
                    if role == "manager":
                        self.assertEqual(db.execute("SELECT sent FROM received").fetchone()[0], 1)
                self.gate.release()

    def test_absent_config_and_restart_exact_receipt_no_provider_replay(self):
        config = dict(self.configs["manager"])
        del config["maintenance_admission"]
        calls = []
        with ExitStack() as stack:
            client = fixtures(stack, config, lambda: calls.append("provider"))
            self.assertEqual(exchange.run(config, once=True), 0)
            ack = client.acknowledge.call_args.args[0]
            self.assertEqual(exchange.run(config, once=True), 0)
            self.assertEqual(client.acknowledge.call_args.args[0], ack)
            config["maintenance_admission"] = self.setting
            self.assertEqual(exchange.run(config, once=True), 0)
            self.assertEqual(client.acknowledge.call_args.args[0], ack)
        self.assertEqual(calls, ["provider"])

    def test_ambiguous_provider_failure_closes_and_never_reinfers_on_restart(self):
        calls = []
        def fail():
            calls.append("provider")
            raise OSError("synthetic ambiguous response")
        with ExitStack() as stack:
            fixtures(stack, self.configs["manager"], fail)
            self.assertEqual(exchange.run(self.configs["manager"], once=True), 0)
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                exchange.run(self.configs["manager"], once=True)
        self.assertEqual(calls, ["provider"])
        with self.gate.drain(0):
            pass

    def test_multiple_ticks_keep_policy_pin_and_refuse_second_provider_call(self):
        config = copy.deepcopy(self.configs["manager"])
        config["context"]["rounds"] = 2
        calls = []
        assignment = json.loads(Path(config["assignment"]).read_text())
        second = copy.deepcopy(assignment)
        second["body"]["task_id"] = "c6-session-2"
        second["body"]["nonce"] = "second-synthetic-nonce"
        key = Ed25519PrivateKey.from_private_bytes(Path(self.configs["ceo"]["signing_key"]).read_bytes())
        second["signature"] = key.sign(canonical(second["body"]).encode()).hex()
        def sleep(seconds):
            policy_path = Path(config["usage_policy"])
            policy = json.loads(policy_path.read_text())
            policy["maximum_output_tokens"] = 256
            policy_path.write_text(canonical(policy))
        with ExitStack() as stack:
            client = fixtures(stack, config, lambda: calls.append("provider"))
            client.fetch.side_effect = [[assignment], [second]]
            stack.enter_context(patch.object(exchange, "time", SimpleNamespace(sleep=sleep)))
            with self.assertRaisesRegex(ValueError, "policy changed"):
                exchange.run(config)
        self.assertEqual(calls, ["provider"])
        with self.gate.drain(0):
            pass

    def test_two_process_duplicate_startup_and_closed_restart_denial(self):
        config_path = self.home / "config.json"
        config_path.write_text(canonical(self.configs["manager"]))
        marker = self.home / "reached"
        command = [sys.executable, "-c",
            "from tests.test_preparation_exchange_maintenance_c6 import child; "
            "import sys; child(*sys.argv[1:])", str(config_path)]
        first = subprocess.Popen(command + [str(marker)], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and first.poll() is None and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertTrue(marker.exists())
            duplicate = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=8)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("BlockingIOError", duplicate.stderr)
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(0):
                    pass
            Path(str(marker) + ".finish").write_text("finish")
            stdout, stderr = first.communicate(timeout=8)
            self.assertEqual(first.returncode, 0, stderr)
            with self.gate.drain(0):
                before = self.tree()
                restart = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=8)
                self.assertNotEqual(restart.returncode, 0)
                self.assertIn("MaintenanceDenied", restart.stderr)
                self.assertEqual(self.tree(), before)
            with sqlite3.connect(self.home / "manager/exchange.sqlite") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM calls").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT sent FROM received").fetchone()[0], 1)
        finally:
            if first.poll() is None:
                first.kill()
            first.communicate()


if __name__ == "__main__":
    unittest.main()

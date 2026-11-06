"""C3A same-host synthetic role writers; no services, providers or live state."""
import copy
import hashlib
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
from contextlib import ExitStack
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from agents.ceo import hierarchy_service as service
from agents.ceo import hierarchy_research_daemon as daemon
from agents.ceo import hierarchy_worker_service as worker_service
from agents.ceo import ceo_research_review as ceo_review
from agents.ceo.role_maintenance import admission, configured_gate
from agents.ceo.hierarchy_providers import HierarchyProvider
from agents.ceo.escalation_inbox import canonical
from agents.ceo.venture_workflow import hashed
from kernel.broker.isolated_mtls import MaintenanceAdmission, MaintenanceDenied

ROOT = Path(__file__).resolve().parents[1]
ACTORS = ("service-manager", "worker-a", "worker-b", "worker-c", "service-worker")


class RoleMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="c3a-", dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.control = self.root / "control"
        self.control.write_bytes(b"OPEN\n")
        self.active = self.root / "control.active"
        self.active.write_bytes(b"")
        for path in (self.control, self.active):
            path.chmod(0o600)
        self.identity = ":".join(str(n) for p in (self.control, self.active, self.root)
                                 for n in (p.stat().st_dev, p.stat().st_ino))
        self.setting = dict(control=str(self.control), identity=self.identity)
        self.gate = MaintenanceAdmission(str(self.control), self.identity)
        self.signer = Ed25519PrivateKey.generate()
        self.seed = self.root / "seed"
        self.seed.write_bytes(self.signer.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        self.seed.chmod(0o600)
        self.policy = self.root / "policy.json"
        self.policy.write_text(json.dumps(dict(model="gpt-6-luna",
            domain="worker-preparation-inference-v1", maximum_requests=4,
            roles=dict(manager=dict(model="gpt-6-sol", actor_id="service-manager", endpoint="fixture")))))
        self.flow = "research-" + "a"*24

    def config(self, actor="service-manager", suffix=""):
        state = self.root / (actor + suffix)
        state.mkdir(exist_ok=True, mode=0o700)
        return dict(role="manager" if actor == "service-manager" else "worker",
            actor_id=actor, workflow_id=self.flow, trust="fixture",
            signing_key=str(self.seed), endpoint="fixture", ca_file="fixture",
            client_cert="fixture", client_key="fixture", state_dir=str(state),
            policy=str(self.policy), context=dict(session_id=self.flow),
            maintenance_admission=copy.deepcopy(self.setting))

    def snapshot(self, actor):
        role = "manager" if actor == "service-manager" else "worker"
        state = dict(id=self.flow, venture_id=self.flow, mode="PREPARATION_ONLY",
            state="MANAGER_PENDING" if role == "manager" else "WORKER_PENDING",
            scope_hash="scope", revision=1, used_units=0,
            scope=dict(manager_id="service-manager", worker_id="service-worker" if actor == "service-worker" else "worker-a",
                       budget_units=5, seed_cents=1, tasks=["Desk research"]),
            handoff=dict(item_id=self.flow, review=dict(item_id=self.flow)),
            last_command=dict(evidence=[]), evidence={"research-approval-" + "a"*24: "a"*64},
            operational_authority=False, external_actions_allowed=False,
            execution_performed=False, money_released=False)
        if actor.startswith("worker-"):
            state["decomposition"] = dict(approval=dict(signature="synthetic"),
                assignments=[dict(id=n, worker_id=a, task=n, depends_on=[] if n != "C" else ["A", "B"])
                             for n, a in daemon.RESEARCH_WORKERS.items()],
                states=dict(A="COMPLETE" if actor == "worker-c" else "READY",
                            B="COMPLETE" if actor == "worker-c" else "READY", C="READY"))
        return state

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()
                and p not in (self.control, self.active)}

    def patches(self, stack, config, client):
        public = self.signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        stack.enter_context(patch.object(service, "load_trust",
            return_value={config["actor_id"]: (config["role"], public)}))
        stack.enter_context(patch.object(service, "HierarchyClient", return_value=client))

    def test_closed_all_entrypoints_before_constructor_or_directory_write(self):
        for actor in ACTORS:
            cfg = self.config(actor)
            before = self.tree()
            with self.gate.drain(0):
                with patch.object(service, "HierarchyProvider") as provider, \
                     patch.object(service, "HierarchyClient") as client:
                    for call in (
                        lambda: service.run(cfg, once=True),
                        lambda: service.tick_research_task(cfg, Mock(), {}, Mock(), {}),
                        lambda: daemon.poll(cfg, once=True),
                        lambda: daemon.allowed_config(cfg, self.flow, self.snapshot(actor)),
                    ):
                        with self.assertRaises(MaintenanceDenied):
                            call()
                    provider.assert_not_called()
                    client.assert_not_called()
                self.assertEqual(self.tree(), before)
            self.gate.release()

    def test_strict_config_absence_and_malformed_never_fall_back(self):
        self.assertIsNone(configured_gate({}))
        invalid = [None, False, "", {}, dict(control=str(self.control)),
            dict(self.setting, extra=True), dict(self.setting, identity="0:1"),
            dict(self.setting, identity=" 1:2:3:4:5:6"),
            dict(self.setting, identity="+1:2:3:4:5:6"),
            dict(self.setting, control=str(self.root / ".." / self.root.name / "control"))]
        for value in invalid:
            with self.subTest(value=value), patch.object(service, "HierarchyProvider") as provider:
                with self.assertRaises(MaintenanceDenied):
                    service.run(dict(role="worker", maintenance_admission=value), once=True)
                provider.assert_not_called()
        for mutation in ("missing", "mode", "symlink", "replace", "malformed"):
            with self.subTest(mutation=mutation):
                original = self.control.read_bytes()
                if mutation == "missing":
                    self.control.rename(self.root / "saved")
                elif mutation == "symlink":
                    self.control.rename(self.root / "saved")
                    self.control.symlink_to(self.root / "saved")
                elif mutation == "replace":
                    self.control.rename(self.root / "saved")
                    self.control.write_bytes(original)
                    self.control.chmod(0o600)
                elif mutation == "mode":
                    self.control.chmod(0o644)
                else:
                    self.control.write_bytes(b"UNKNOWN\n")
                try:
                    with self.assertRaises(MaintenanceDenied):
                        with admission(dict(maintenance_admission=self.setting)):
                            self.fail("unsafe control admitted")
                finally:
                    saved = self.root / "saved"
                    if saved.exists():
                        if self.control.exists() or self.control.is_symlink():
                            self.control.unlink()
                        saved.rename(self.control)
                    self.control.chmod(0o600)
                    self.control.write_bytes(original)

    def race(self, entry):
        # Real SQLite constructor + intent/checkpoint; synthetic remote responses
        # and a signed final artifact. All six writers overlap one local gate.
        configs = [self.config(a) for a in ACTORS] + [self.config("service-manager", "-second")]
        reached = threading.Barrier(len(configs) + 1)
        finish = threading.Event()
        drained = threading.Event()
        errors = []
        records = []
        records_lock = threading.Lock()

        def provider_response(*args):
            reached.wait(timeout=8)
            if not finish.wait(8):
                raise AssertionError("writer was not released")
            return dict(decision=dict(content="synthetic result"), tool_call=None)

        local = threading.local()
        def client_factory(*args, **kwargs):
            return local.client

        def run_direct(cfg, existing=None):
            actor = cfg["actor_id"]
            state = self.snapshot(actor)
            client = Mock()
            client.read.return_value = state
            client.worker_reserve.return_value = dict(reserved=True, duplicate=False)
            client.worker_execute.side_effect = provider_response
            client._request.side_effect = lambda method, path, payload: (
                dict(reserved=True) if path.endswith("/reservations")
                else dict(result=provider_response()))
            with admission(cfg):
                path = Path(cfg["state_dir"]) / "inference.sqlite"
                provider = existing or HierarchyProvider(role=cfg["role"], actor=actor,
                    workflow_id=self.flow, client=client, policy=json.loads(self.policy.read_text()),
                    context=cfg["context"], state_path=path)
                opportunity = dict(role=cfg["role"], scope_hash="scope",
                    snapshot_sha256=hashed(state), state=state["state"])
                if actor.startswith("worker-"):
                    name = actor[-1].upper()
                    opportunity.update(assignment_id=name, tasks=[name])
                result = provider(dict(system="synthetic", json_object_mode=True, opportunity=opportunity), ())
                raw = canonical(result).encode()
                signature = self.signer.sign(raw)
                self.signer.public_key().verify(signature, raw)
                (path.parent / "signed.json").write_text(canonical(dict(result=result, signature=signature.hex())))
                with records_lock:
                    records.append(path)

        class SyntheticRunner:
            def __init__(self, workflow, **kwargs):
                self.callback = kwargs[kwargs["role_filter"]]
            def tick(self, flow):
                run_direct(local.config, self.callback.provider)
                return dict(state="DECOMPOSITION_REVIEW", revision=2)

        def final_writer(cfg):
            try:
                local.config = cfg
                state = self.snapshot(cfg["actor_id"])
                local.client = Mock()
                local.client.research_list.return_value = [dict(workflow_id=self.flow, state=state["state"])]
                local.client.read.return_value = state
                local.client.worker_reserve.return_value = dict(reserved=True, duplicate=False)
                local.client.worker_execute.side_effect = provider_response
                local.client._request.side_effect = lambda method, path, payload: (
                    dict(reserved=True) if path.endswith("/reservations")
                    else dict(result=provider_response()))
                if entry == "poll" and cfg["actor_id"] != "service-worker":
                    daemon.poll(cfg, once=True)
                else:
                    service.run(cfg, once=True)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=final_writer, args=(c,)) for c in configs]
        def close():
            try:
                with self.gate.drain(8):
                    drained.set()
            except BaseException as exc:
                errors.append(exc)
        public = self.signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        with patch.object(service, "load_trust", return_value={
                a: ("manager" if a == "service-manager" else "worker", public) for a in ACTORS}), \
             patch.object(service, "HierarchyClient", side_effect=client_factory), \
             patch.object(service, "tick_research_task", return_value=False), \
             patch.object(service, "HierarchyRunner", SyntheticRunner), \
             patch.object(daemon, "HierarchyClient", side_effect=client_factory), \
             patch.object(daemon, "worker_submission_count", return_value=0), \
             patch.object(daemon, "role_tick", side_effect=lambda cfg, once: run_direct(cfg)):
            for thread in threads:
                thread.start()
            try:
                reached.wait(timeout=8)
                closer = threading.Thread(target=close)
                closer.start()
                deadline = time.monotonic() + 3
                while self.control.read_bytes() != b"CLOSED\n" and time.monotonic() < deadline:
                    time.sleep(.005)
                self.assertEqual(self.control.read_bytes(), b"CLOSED\n")
                self.assertFalse(drained.is_set())
                # No new constructor, directory or broker call after closure.
                with patch.object(service, "HierarchyProvider") as constructor:
                    with self.assertRaises(MaintenanceDenied):
                        service.run(configs[0], once=True)
                    constructor.assert_not_called()
                finish.set()
            finally:
                finish.set()
                for thread in threads:
                    thread.join(10)
                if "closer" in locals():
                    closer.join(10)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(errors, [])
        self.assertTrue(drained.is_set())
        self.assertEqual(len(records), 6)
        before = self.tree()
        for cfg in configs:
            with self.assertRaises(MaintenanceDenied):
                with admission(cfg):
                    self.fail("new work after drain")
        self.assertEqual(self.tree(), before)
        for path in records:
            with sqlite3.connect(path) as db:
                rows = db.execute("SELECT identity, response, attempt FROM calls").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertIsNotNone(rows[0][1])
            self.assertEqual(len(rows[0][2]), 64)

    def test_concurrent_manager_abc_legacy_local_writes_drain(self):
        self.race("direct")

    def test_poll_scope_and_nested_tick_finish_before_drain(self):
        self.race("poll")

    def test_direct_service_holds_constructor_and_final_tick_writes(self):
        cfg = self.config()
        client = Mock()
        client.read.return_value = dict(state="MANAGER_PENDING")
        with ExitStack() as stack:
            self.patches(stack, cfg, client)
            stack.enter_context(patch.object(service, "tick_research_task", return_value=False))
            runner = stack.enter_context(patch.object(service, "HierarchyRunner"))
            def tick(flow):
                with self.assertRaises(MaintenanceDenied):
                    with self.gate.drain(.01):
                        self.fail("drained before signed transition")
                (Path(cfg["state_dir"]) / "final").write_bytes(b"synthetic signed transition")
                return dict(state="DECOMPOSITION_REVIEW", revision=2)
            runner.return_value.tick.side_effect = tick
            # Real adapter construction writes SQLite under initialization lease.
            service.run(cfg, once=True)
        with self.gate.drain(0):
            before = self.tree()
            with self.assertRaises(MaintenanceDenied):
                service.run(cfg, once=True)
            self.assertEqual(self.tree(), before)

    def test_exceptions_release_all_leases_and_keep_closed(self):
        cfg = self.config()
        for failure in (RuntimeError("callback"), KeyboardInterrupt()):
            with self.assertRaises(type(failure)):
                with admission(cfg):
                    with admission(dict(cfg)):
                        with self.assertRaises(MaintenanceDenied):
                            with self.gate.drain(0):
                                pass
                        raise failure
            with self.gate.drain(0):
                pass
            with self.assertRaises(MaintenanceDenied):
                with admission(cfg):
                    pass
            self.gate.release()

    def test_gate_is_thread_local_and_control_agents_are_independent(self):
        cfg = self.config()
        errors = []
        def other():
            try:
                with admission(cfg):
                    errors.append("incorrect inherited lease")
            except MaintenanceDenied:
                pass
        with admission(cfg):
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(0):
                    pass
            t = threading.Thread(target=other)
            t.start()
            t.join(2)
            self.assertFalse(t.is_alive())
            # Independent host-local fixture remains open; local closure alone
            # gives no coverage for the other host.
            with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
                root = Path(tmp)
                for name, data in (("control", b"OPEN\n"), ("control.active", b"")):
                    (root / name).write_bytes(data)
                    (root / name).chmod(0o600)
                identity = ":".join(str(n) for p in (root/"control", root/"control.active", root)
                                    for n in (p.stat().st_dev, p.stat().st_ino))
                with admission(dict(maintenance_admission=dict(control=str(root/"control"), identity=identity))):
                    pass
        self.assertEqual(errors, [])

    def child_code(self, code):
        if "C3A_STRICT_TREE" in os.environ:
            # Preserve strict protected imports in fresh crash/restart children.
            return ("import os, sys\nfrom scripts.ceo_strict_installed_dry_run import Finder\n"
                    "sys.meta_path.insert(0, Finder(os.environ['C3A_STRICT_TREE'], "
                    "os.environ['C3A_STRICT_PROFILE']))\n" + code)
        return code

    def test_operator_death_and_fresh_role_process_stays_closed(self):
        code = """import sys
from kernel.broker.isolated_mtls import MaintenanceAdmission
with MaintenanceAdmission(sys.argv[1], sys.argv[2]).drain(1):
    print("closed", flush=True)
    sys.stdin.readline()
"""
        proc = subprocess.Popen([sys.executable, "-B", "-c", self.child_code(code),
            str(self.control), self.identity], cwd=ROOT, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "closed")
            proc.kill()
            proc.communicate(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)
        cfg = self.config()
        before = self.tree()
        code = """import json, sys
from agents.ceo.hierarchy_service import run
from kernel.broker.isolated_mtls import MaintenanceDenied
try:
    run(json.loads(sys.argv[1]), once=True)
except MaintenanceDenied:
    sys.exit(0)
sys.exit(9)
"""
        result = subprocess.run([sys.executable, "-B", "-c", self.child_code(code), json.dumps(cfg)],
            cwd=ROOT, capture_output=True, text=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.control.read_bytes(), b"CLOSED\n")
        self.assertEqual(self.tree(), before)

    def test_constructor_and_poll_idle_boundary_are_both_admitted(self):
        cfg = self.config()
        client = Mock()
        client.read.return_value = None
        original = service.HierarchyProvider
        def constructor(**kwargs):
            # Closure during initialization must wait for the constructor's
            # SQLite writes and then deny entry to the first work cycle.
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(0):
                    pass
            return original(**kwargs)
        with ExitStack() as stack:
            self.patches(stack, cfg, client)
            stack.enter_context(patch.object(service, "HierarchyProvider", side_effect=constructor))
            stack.enter_context(patch.object(service, "tick_research_task"))
            with self.assertRaises(MaintenanceDenied):
                service.run(cfg, once=True)
        self.assertTrue((Path(cfg["state_dir"]) / "inference.sqlite").exists())
        client.read.assert_not_called()
        self.gate.release()
        with ExitStack() as stack:
            self.patches(stack, cfg, client)
            tick = stack.enter_context(patch.object(service, "tick_research_task", return_value=False))
            def sleep(seconds):
                with self.gate.drain(0):
                    pass  # No lease is retained across the idle poll interval.
            stack.enter_context(patch.object(service.time, "sleep", side_effect=sleep))
            with self.assertRaises(MaintenanceDenied):
                service.run(cfg)
            self.assertEqual(tick.call_count, 1)
        with self.gate.drain(0):
            pass

    def test_actual_entrypoint_exception_leaves_intent_and_no_retry(self):
        cfg = self.config("worker-a")
        client = Mock()
        state = self.snapshot("worker-a")
        client.read.return_value = state
        client.worker_reserve.return_value = dict(reserved=True, duplicate=False)
        def fail(payload):
            with self.assertRaises(MaintenanceDenied):
                with self.gate.drain(0):
                    pass
            raise RuntimeError("synthetic transport failure")
        client.worker_execute.side_effect = fail
        class Runner:
            def __init__(self, workflow, **kwargs):
                self.provider = kwargs["worker"].provider
            def tick(inner, flow):
                return inner.provider(dict(system="synthetic", json_object_mode=True,
                    opportunity=dict(role="worker", scope_hash="scope",
                        snapshot_sha256=hashed(state), state="WORKER_PENDING",
                        assignment_id="A", tasks=["A"])), ())
        with ExitStack() as stack:
            self.patches(stack, cfg, client)
            stack.enter_context(patch.object(service, "tick_research_task", return_value=False))
            stack.enter_context(patch.object(service, "HierarchyRunner", Runner))
            with self.assertRaisesRegex(RuntimeError, "synthetic transport"):
                service.run(cfg, once=True)
            before = self.tree()
            with self.assertRaises(MaintenanceDenied):
                service.run(cfg, once=True)
            self.assertEqual(self.tree(), before)
        with sqlite3.connect(Path(cfg["state_dir"]) / "inference.sqlite") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM calls WHERE response IS NULL").fetchone()[0], 1)
        self.assertEqual(client.worker_execute.call_count, 1)
        with self.gate.drain(0):
            pass

    def test_ceo_signed_review_final_writes_remain_inside_lease(self):
        from tests.test_ceo_research_review import FakeModel, FakeClient
        cfg = self.config()
        cfg.update(role="ceo", actor_id="service-ceo")
        raw = canonical(dict(role="worker", action="submit", scope_hash="scope",
            deliverable="A hypothetical desk comparison with clear unknowns.",
            explanation="Research draft needs more evidence.")).encode()
        sha = hashlib.sha256(raw).hexdigest()
        state = dict(id=self.flow, state="HOLD", mode="PREPARATION_ONLY",
            operational_authority=False, external_actions_allowed=False,
            execution_performed=False, money_released=False,
            scope=dict(tasks=["Desk research only"]), scope_hash="scope",
            evidence={"preparation-"+sha: sha})
        model = FakeModel()
        class ClosingModel:
            model = "gpt-6-sol"
            def __call__(inner, request, tools):
                with self.assertRaises(MaintenanceDenied):
                    with self.gate.drain(0):
                        pass
                return model(request, tools)
        result = ceo_review.review(cfg, state, FakeClient(raw), ClosingModel())
        self.signer.public_key().verify(bytes.fromhex(result["signature"]),
                                       canonical(result["packet"]).encode())
        self.assertEqual(result["state"], "COMPLETE")
        before = self.tree()
        with self.gate.drain(0):
            with self.assertRaises(MaintenanceDenied):
                ceo_review.review(cfg, state, FakeClient(raw), model)
        self.assertEqual(model.calls, 1)
        self.assertEqual(self.tree(), before)

    def test_worker_config_legacy_exact_fields_and_opt_in(self):
        cfg = self.config("service-worker")
        cfg["workflow_id"] = "level2d-acceptance-1"
        cfg.pop("context")
        cfg.pop("maintenance_admission")
        cfg["trust"] = str(self.seed)
        for field in ("client_key", "client_cert", "ca_file"):
            cfg[field] = str(self.seed)
        expected = json.loads((ROOT / "infrastructure/level2d-worker-policy.json").read_text())
        self.policy.write_text(json.dumps(expected))
        path = self.root / "config.json"
        path.write_text(json.dumps(cfg))
        self.assertEqual(worker_service.load_config(path), cfg)
        cfg["maintenance_admission"] = copy.deepcopy(self.setting)
        path.write_text(json.dumps(cfg))
        self.assertEqual(worker_service.load_config(path), cfg)
        cfg["maintenance_admission"] = None
        path.write_text(json.dumps(cfg))
        with self.assertRaises(MaintenanceDenied):
            worker_service.load_config(path)
        cfg["maintenance_admission"] = copy.deepcopy(self.setting)
        cfg["extra"] = True
        path.write_text(json.dumps(cfg))
        with self.assertRaises(ValueError):
            worker_service.load_config(path)
        cfg.pop("extra")
        cfg["actor_id"] = "worker-a"
        path.write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError, "fixture identity"):
            worker_service.load_config(path)

    def test_ceo_pause_composes_and_closed_review_has_no_writes(self):
        cfg = self.config()
        cfg.update(role="ceo", actor_id="service-ceo")
        lock = self.root / "pause"
        lock.write_bytes(b"")
        lock.chmod(0o600)
        cfg["deployment_lock"] = str(lock)
        from agents.ceo.deployment_pause import lease
        client = Mock()
        with lease(lock, exclusive=True) as exclusive:
            self.assertTrue(exclusive)
            with patch.object(daemon, "HierarchyClient", return_value=client):
                daemon.poll(cfg, once=True, worker_limit_override=4)
            client.research_list.assert_not_called()
        with self.gate.drain(0):
            before = self.tree()
            with patch.object(ceo_review, "write_atomic") as write:
                with self.assertRaises(MaintenanceDenied):
                    ceo_review.review(cfg, {}, client)
                write.assert_not_called()
            self.assertEqual(self.tree(), before)


if __name__ == "__main__":
    unittest.main()

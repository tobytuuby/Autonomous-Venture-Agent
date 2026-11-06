"""Two host-labelled fixtures, real C1 locks and code replacement; no live IO."""
import copy
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
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.role_maintenance import admission
from kernel.broker.isolated_mtls import MaintenanceAdmission, MaintenanceDenied
from scripts import level2d_acceptance_deploy_control as deploy
from scripts.ceo_stage6_deployment_gate import deployment_decision


class CoordinatedMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="c4-fixture-", dir=deploy.P)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.gates = {}
        participants = []
        for host, roles in {
            "Control": ("ceo", "broker"),
            "Agents": ("manager-1", "manager-2", "manager-3",
                       "worker-A", "worker-B", "worker-C"),
        }.items():
            directory = self.root / host
            directory.mkdir(mode=0o700)
            control = directory / "control"
            control.write_bytes(b"OPEN\n")
            active = directory / "control.active"
            active.write_bytes(b"")
            for path in (control, active):
                path.chmod(0o600)
            identity = ":".join(str(n) for p in (control, active, directory)
                                for n in (p.stat().st_dev, p.stat().st_ino))
            self.gates[host] = MaintenanceAdmission(str(control), identity)
            participants.extend(dict(host=host, role=role, uid=os.geteuid(),
                                     control=str(control.relative_to(self.root)),
                                     identity=identity) for role in roles)
        frozen = []
        prerequisites = {}
        for kind in ("trust", "signed_scope_quota", "timers", "external_writers", "identities"):
            name = "prerequisites/" + kind + ".json"
            value = dict(classification="SYNTHETIC_ONLY", ready=True)
            if kind == "identities":
                value = [dict(host=p["host"], role=p["role"],
                              source="fixture-v1", installed="fixture-v1", loaded="fixture-v1")
                         for p in participants]
            self.write(name, json.dumps(value))
            frozen.append(name)
            prerequisites[kind] = name
        updates = {}
        for host in self.gates:
            name = "code/" + host + "/service.py"
            self.write(name, "VERSION = 1\n")
            frozen.append(name)
            updates[name] = "VERSION = 2\n"
        self.write("state/execution.json", '{"execution":"COMPLETE","response":"DURABLE"}')
        self.write("state/workflow.json", '{"scope":"synthetic","revision":3,"quota":12}')
        self.signer = Ed25519PrivateKey.generate()
        raw = (self.root / "state/workflow.json").read_bytes()
        self.write("state/workflow.sig", self.signer.sign(raw).hex())
        with sqlite3.connect(self.root / "state/resources.sqlite") as db:
            db.execute("CREATE TABLE quota (used INTEGER, maximum INTEGER)")
            db.execute("INSERT INTO quota VALUES (4,12)")
        for p in participants:
            if p["role"] != "broker":
                self.write("state/" + p["role"] + ".response", "not started")
        self.plan = dict(classification="SYNTHETIC_ONLY", participants=participants,
                         frozen=frozen, prerequisites=prerequisites,
                         baseline=deploy._snapshot(self.root, frozen),
                         state=["state/" + p.name for p in (self.root / "state").iterdir()],
                         execution_status="state/execution.json", updates=updates)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_maintenance(self, timeout=2):
        return deploy.coordinated_synthetic_maintenance(
            self.root, self.plan, deploy._digest(self.plan), timeout)

    def assert_closed(self):
        for gate in self.gates.values():
            self.assertEqual(gate.path.read_bytes(), b"CLOSED\n")
            with self.assertRaises(MaintenanceDenied), gate.request():
                self.fail("fresh admission")

    def release(self, attestation):
        return deploy.release_synthetic_after_attestation(
            self.root, self.plan, deploy._digest(self.plan), deploy._digest(attestation))

    def test_complete_code_only_change_attests_closed_then_independent_release(self):
        before = deploy._snapshot(self.root, self.plan["state"])
        attestation = self.run_maintenance()
        self.assert_closed()
        self.assertFalse(attestation["deployment_allowed"])
        self.assertEqual(attestation["state"], before)
        self.assertEqual(deploy._snapshot(self.root, self.plan["state"]), before)
        for name in self.plan["updates"]:
            self.assertEqual((self.root / name).read_text(), "VERSION = 2\n")
        self.signer.public_key().verify(
            bytes.fromhex((self.root / "state/workflow.sig").read_text()),
            (self.root / "state/workflow.json").read_bytes())
        self.assertEqual(len(list((self.root / "code-backup").iterdir())), 2)
        self.release(attestation)
        for gate in self.gates.values():
            with gate.request():
                pass
        self.assertFalse(deployment_decision()["deployment_allowed"])

    def test_three_managers_abc_and_ceo_slow_actions_drain_before_snapshot(self):
        roles = [p for p in self.plan["participants"] if p["role"] != "broker"]
        reached = threading.Barrier(len(roles) + 1)
        finish = threading.Event()
        errors, reports = [], []
        def action(p):
            try:
                gate = self.gates[p["host"]]
                setting = dict(control=str(gate.path), identity=p["identity"])
                with admission(dict(maintenance_admission=setting)):
                    # Existing local role lease spans a broker action and final write.
                    broker_context = (self.gates["Control"].request()
                                      if p["host"] == "Agents" else admission({}))
                    with broker_context:
                        reached.wait(5)
                        if not finish.wait(5):
                            raise AssertionError("slow fixture action timeout")
                        self.write("state/" + p["role"] + ".response", "durable synthetic response")
            except BaseException as exc:
                errors.append(exc)
        def maintain():
            try:
                reports.append(self.run_maintenance(4))
            except BaseException as exc:
                errors.append(exc)
        threads = [threading.Thread(target=action, args=(p,)) for p in roles]
        for thread in threads:
            thread.start()
        try:
            reached.wait(5)
            closer = threading.Thread(target=maintain)
            closer.start()
            deadline = time.monotonic() + 2
            while any(g.path.read_bytes() != b"CLOSED\n" for g in self.gates.values()):
                if time.monotonic() > deadline:
                    self.fail("all controls must close before waiting")
                time.sleep(.005)
            self.assertEqual(reports, [])
            self.assert_closed()
        finally:
            finish.set()
            for thread in threads:
                thread.join(6)
            if "closer" in locals():
                closer.join(6)
        self.assertEqual(errors, [])
        self.assertEqual(len(reports), 1)
        for p in roles:
            name = "state/" + p["role"] + ".response"
            self.assertEqual(reports[0]["state"][name]["sha256"],
                             deploy.sha(b"durable synthetic response"))
        self.assert_closed()

    def test_pending_and_ambiguous_hold_without_retry_or_state_restore(self):
        for status in (dict(execution="PENDING", response=None),
                       dict(execution="COMPLETE", response="LOST"),
                       dict(execution="UNKNOWN", response=None)):
            self.write("state/execution.json", json.dumps(status))
            before = deploy._snapshot(self.root, self.plan["state"])
            with self.assertRaisesRegex(ValueError, "HOLD"):
                self.run_maintenance()
            self.assert_closed()
            self.assertEqual(deploy._snapshot(self.root, self.plan["state"]), before)
            self.assertFalse((self.root / "code-backup").exists())
        for name in self.plan["updates"]:
            self.assertEqual((self.root / name).read_text(), "VERSION = 1\n")

    def test_timeout_closes_both_hosts_no_code_change(self):
        with self.gates["Agents"].request():
            with self.assertRaises(MaintenanceDenied):
                self.run_maintenance(.02)
        self.assert_closed()
        self.assertFalse((self.root / "closed-attestation.json").exists())

    def test_crash_during_drain_fresh_process_remains_closed(self):
        code = """import json,sys
from scripts.level2d_acceptance_deploy_control import coordinated_synthetic_maintenance
coordinated_synthetic_maintenance(sys.argv[1],json.loads(sys.argv[2]),sys.argv[3],10)
"""
        with self.gates["Agents"].request():
            child = subprocess.Popen([sys.executable, "-B", "-c", code, str(self.root),
                                      json.dumps(self.plan), deploy._digest(self.plan)],
                                     cwd=deploy.P, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 4
                while any(g.path.read_bytes() != b"CLOSED\n" for g in self.gates.values()):
                    if child.poll() is not None or time.monotonic() > deadline:
                        self.fail("child did not close both controls")
                    time.sleep(.005)
                child.kill()
                child.communicate(timeout=4)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=4)
        self.assert_closed()
        code = """import sys
from kernel.broker.isolated_mtls import MaintenanceAdmission,MaintenanceDenied
try:
 with MaintenanceAdmission(sys.argv[1],sys.argv[2]).request(): pass
except MaintenanceDenied: sys.exit(0)
sys.exit(9)
"""
        for gate in self.gates.values():
            result = subprocess.run([sys.executable, "-B", "-c", code, str(gate.path),
                                     ":".join(map(str, gate.identity))],
                                    cwd=deploy.P, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "closed-attestation.json").exists())

    def test_clean_operator_restart_receipt_requires_explicit_release(self):
        attestation = self.run_maintenance()
        code = """import json,sys
from scripts.level2d_acceptance_deploy_control import release_synthetic_after_attestation
release_synthetic_after_attestation(sys.argv[1],json.loads(sys.argv[2]),sys.argv[3],sys.argv[4])
"""
        self.assert_closed()
        result = subprocess.run([sys.executable, "-B", "-c", code, str(self.root),
                                 json.dumps(self.plan), deploy._digest(self.plan),
                                 deploy._digest(attestation)], cwd=deploy.P,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_code_failure_rolls_back_code_only_keeps_closed(self):
        original = deploy.atomic
        calls = []
        def fail_second(path, raw, info):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("synthetic disk failure")
            return original(path, raw, info)
        before = deploy._snapshot(self.root, self.plan["state"])
        with patch.object(deploy, "atomic", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.run_maintenance()
        self.assert_closed()
        for name in self.plan["updates"]:
            self.assertEqual((self.root / name).read_text(), "VERSION = 1\n")
        self.assertEqual(deploy._snapshot(self.root, self.plan["state"]), before)

    def test_drift_or_unreviewed_attestation_prevents_release(self):
        attestation = self.run_maintenance()
        with self.assertRaises(ValueError):
            deploy.release_synthetic_after_attestation(
                self.root, self.plan, deploy._digest(self.plan), "0" * 64)
        self.assert_closed()
        self.write("state/workflow.json", "changed")
        with self.assertRaisesRegex(ValueError, "drift"):
            self.release(attestation)
        self.assert_closed()
        self.assertEqual((self.root / "state/workflow.json").read_text(), "changed")

    def test_readonly_preflight_rejects_incomplete_review_and_identity(self):
        before = {str(p.relative_to(self.root)): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        variants = []
        missing = copy.deepcopy(self.plan)
        missing["participants"].pop()
        variants.append(missing)
        for key in self.plan["prerequisites"]:
            changed = copy.deepcopy(self.plan)
            changed["prerequisites"].pop(key)
            variants.append(changed)
        shared = copy.deepcopy(self.plan)
        shared["participants"][-1]["identity"] = "0:0:0:0:0:0"
        variants.append(shared)
        for plan in variants:
            with self.assertRaises((ValueError, MaintenanceDenied)):
                deploy.coordinated_preflight(self.root, plan, deploy._digest(plan))
        with self.assertRaises(ValueError):
            deploy.coordinated_preflight(self.root, self.plan, "0" * 64)
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes()
                                 for p in self.root.rglob("*") if p.is_file()})

    def test_changed_baseline_and_unsafe_paths_are_denied(self):
        self.write("prerequisites/trust.json", "{}")
        with self.assertRaisesRegex(ValueError, "baseline"):
            self.run_maintenance()
        with self.assertRaises(ValueError):
            deploy.coordinated_preflight(deploy.P, self.plan, deploy._digest(self.plan))
        with self.assertRaises(ValueError):
            deploy._snapshot(self.root, ["../AGENTS.md"])

    def test_unknown_state_sidecar_during_drain_aborts_closed(self):
        original = deploy._close_fixture_gates
        def extra(gates):
            result = original(gates)
            self.write("state/unknown.sqlite-wal", "unexpected writer")
            return result
        with patch.object(deploy, "_close_fixture_gates", side_effect=extra):
            with self.assertRaisesRegex(ValueError, "inventory"):
                self.run_maintenance()
        self.assert_closed()
        self.assertFalse((self.root / "code-backup").exists())

    def test_state_drift_during_code_update_is_preserved_for_hold(self):
        original = deploy.atomic
        changed = False
        def drift(path, raw, info):
            nonlocal changed
            original(path, raw, info)
            if not changed:
                changed = True
                self.write("state/workflow.json", "external writer")
        with patch.object(deploy, "atomic", side_effect=drift):
            with self.assertRaisesRegex(ValueError, "protected state"):
                self.run_maintenance()
        self.assert_closed()
        self.assertEqual((self.root / "state/workflow.json").read_text(), "external writer")
        for name in self.plan["updates"]:
            self.assertEqual((self.root / name).read_text(), "VERSION = 1\n")

    def test_partial_release_failure_recloses_all_hosts(self):
        attestation = self.run_maintenance()
        original = MaintenanceAdmission.release
        calls = []
        def fail_second(gate, timeout=0):
            calls.append(gate)
            if len(calls) == 2:
                raise MaintenanceDenied("fixture release failure")
            return original(gate, timeout)
        with patch.object(MaintenanceAdmission, "release", new=fail_second):
            with self.assertRaises(MaintenanceDenied):
                self.release(attestation)
        self.assert_closed()

    def test_identity_timer_and_external_writer_prerequisite_denial(self):
        for kind in ("identities", "timers", "external_writers"):
            name = self.plan["prerequisites"][kind]
            old = (self.root / name).read_text()
            value = json.loads(old)
            if kind == "identities":
                value[0]["loaded"] = "old-loaded-code"
            else:
                value["ready"] = False
            self.write(name, json.dumps(value))
            plan = copy.deepcopy(self.plan)
            plan["baseline"] = deploy._snapshot(self.root, plan["frozen"])
            with self.assertRaisesRegex(ValueError, "identity|prerequisite"):
                deploy.coordinated_preflight(self.root, plan, deploy._digest(plan))
            self.write(name, old)

    def test_real_entrypoint_denies_before_any_service_operation(self):
        with patch.object(deploy, "run", side_effect=AssertionError("live service access")), \
             patch.object(deploy, "require_research_ceo_inactive",
                          side_effect=AssertionError("live service access")):
            with self.assertRaisesRegex(SystemExit, "Stage6"):
                deploy.main()

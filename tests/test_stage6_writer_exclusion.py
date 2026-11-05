"""C2A synthetic local observation cannot authorize deployment or mutate C1."""
import copy
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import ceo_stage6_deployment_gate as gate


class WriterExclusionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=gate.ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pin = dict(Id="manager.service", User="manager",
                        FragmentPath="/etc/systemd/system/manager.service",
                        ExecStart="/installed/manager", ControlGroup="", role="manager")
        self.config = {"units": {"manager.service": self.pin}}
        self.snapshot = dict(units=[self.unit(self.pin)], processes=[], jobs=[], errors=[])

    @staticmethod
    def unit(pin, **changes):
        value = {k: pin[k] for k in gate.IDENTITY_FIELDS}
        value.update(LoadState="loaded", ActiveState="inactive", SubState="dead", MainPID="0")
        value.update(changes)
        return value

    def assess(self):
        # Snapshot tests must never accidentally consult actual service state.
        with patch.object(gate, "observe_local_writers", side_effect=AssertionError("live read")):
            result = gate.writer_exclusion_preflight(self.config, self.snapshot)
        self.assertEqual(result["decision"], "DENY")
        self.assertIs(result["deployment_allowed"], False)
        self.assertIs(result["cross_vm_coverage_verified"], False)
        self.assertIs(result["resume_verified"], False)
        return result

    def test_clean_local_snapshot_is_still_denied(self):
        result = self.assess()
        self.assertTrue(result["local_exclusion_ready"])
        self.assertEqual(result["classification"], "SYNTHETIC_SNAPSHOT")
        self.assertIn("SEPARATE_JOINED_PROOF_REQUIRED", result["blockers"])

    def test_active_roles_and_backup_timer_prevent_readiness(self):
        for role, name in (("manager", "manager.service"), ("worker", "worker.service"),
                           ("ceo", "ceo.service"), ("api", "api.service"),
                           ("timer", "backup.timer")):
            with self.subTest(role=role):
                pin = dict(self.pin, Id=name, role=role)
                self.config = {"units": {name: pin}}
                self.snapshot["units"] = [self.unit(pin, ActiveState="active",
                                                  SubState="waiting" if role == "timer" else "running")]
                self.assertFalse(self.assess()["local_exclusion_ready"])

    def test_unknown_unit_and_unknown_process_writer(self):
        self.snapshot["units"].append(self.unit(dict(self.pin, Id="unknown.service")))
        self.assertIn("UNKNOWN_OR_DUPLICATE_UNIT", self.assess()["reasons"])
        self.snapshot["units"].pop()
        self.snapshot["processes"] = [dict(pid=42, exe="/unknown", cgroups=["0::/unknown"])]
        self.assertIn("UNKNOWN_OR_EXTRA_PROCESS_WRITER", self.assess()["reasons"])

    def test_identity_mainpid_cgroup_and_incomplete_evidence(self):
        cases = [
            ("Id", "alias.service"), ("User", "root"), ("ExecStart", "/changed"),
            ("FragmentPath", "/changed"), ("LoadState", "not-found"),
            ("MainPID", "10"), ("MainPID", "-1"), ("ControlGroup", "/residual"),
            ("ActiveState", "activating"), ("ActiveState", "failed"),
        ]
        original = copy.deepcopy(self.snapshot)
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.snapshot = copy.deepcopy(original)
                self.snapshot["units"][0][key] = value
                self.assertFalse(self.assess()["local_exclusion_ready"])
        for key, value in (("errors", ["permission denied"]), ("jobs", [{"job": 1}]),
                           ("units", [])):
            self.snapshot = copy.deepcopy(original)
            self.snapshot[key] = value
            self.assertFalse(self.assess()["local_exclusion_ready"])

    def test_unconfigured_gate_and_invalid_snapshot(self):
        with patch.object(gate, "observe_local_writers", side_effect=AssertionError("live read")):
            for config, snapshot in ((None, None), ({}, {}), (self.config, {})):
                self.assertFalse(gate.writer_exclusion_preflight(config, snapshot)["local_exclusion_ready"])

    def broker_fixture(self):
        directory = self.root / "private"
        directory.mkdir(mode=0o700)
        control = directory / "control"
        active = directory / "control.active"
        control.write_bytes(b"CLOSED\n")
        active.write_bytes(b"")
        control.chmod(0o600)
        active.chmod(0o600)
        identity = ":".join(str(n) for p in (control, active, directory)
                            for n in (p.stat().st_dev, p.stat().st_ino))
        pin = dict(self.pin, Id="broker.service", role="broker", User="broker",
                   ControlGroup="/system.slice/broker.service")
        broker = dict(unit=pin["Id"], path=str(control), identity=identity, exe="/installed/python")
        self.config["units"][pin["Id"]] = pin
        self.config["broker"] = broker
        self.snapshot["units"].append(self.unit(pin, ActiveState="active",
                                               SubState="running", MainPID="55"))
        self.snapshot["processes"] = [dict(pid=55, exe=broker["exe"],
                                         cgroups=["0::" + pin["ControlGroup"]])]
        return control, active

    def test_closed_broker_no_leases_read_only(self):
        control, active = self.broker_fixture()
        before = [(p.stat().st_ino, p.read_bytes()) for p in (control, active)]
        from kernel.broker.isolated_mtls import MaintenanceAdmission
        with patch.object(MaintenanceAdmission, "_write", side_effect=AssertionError("write")), \
             patch.object(MaintenanceAdmission, "drain", side_effect=AssertionError("drain")), \
             patch.object(MaintenanceAdmission, "release", side_effect=AssertionError("release")):
            self.assertTrue(self.assess()["local_exclusion_ready"])
        self.assertEqual(before, [(p.stat().st_ino, p.read_bytes()) for p in (control, active)])

    def test_missing_broker_c1_file(self):
        control, _ = self.broker_fixture()
        control.unlink()
        self.assertIn("BROKER_C1_NOT_CLOSED_AND_DRAINED", self.assess()["reasons"])
        self.assertFalse(control.exists())

    def test_unconfigured_broker(self):
        self.broker_fixture()
        del self.config["broker"]
        self.assertIn("BROKER_C1_UNCONFIGURED", self.assess()["reasons"])

    def test_open_broker_and_outstanding_lease(self):
        control, active = self.broker_fixture()
        control.write_bytes(b"OPEN\n")
        self.assertFalse(self.assess()["local_exclusion_ready"])
        control.write_bytes(b"CLOSED\n")
        with active.open("rb") as held:
            fcntl.flock(held, fcntl.LOCK_SH | fcntl.LOCK_NB)
            self.assertFalse(self.assess()["local_exclusion_ready"])
        self.assertTrue(self.assess()["local_exclusion_ready"])

    def test_broker_process_identity_and_extra_writer(self):
        self.broker_fixture()
        original = copy.deepcopy(self.snapshot)
        for key, value in (("pid", 56), ("exe", "/wrong"), ("cgroups", ["0::/wrong"]),
                           ("cgroups", [])):
            self.snapshot = copy.deepcopy(original)
            self.snapshot["processes"][0][key] = value
            self.assertFalse(self.assess()["local_exclusion_ready"])
        self.snapshot = copy.deepcopy(original)
        self.snapshot["processes"].append(dict(pid=99, exe="/child", cgroups=["0::/system.slice/broker.service"]))
        self.assertFalse(self.assess()["local_exclusion_ready"])

    def test_cli_snapshot_deny_without_writes_or_subprocesses(self):
        config = self.root / "config.json"
        snapshot = self.root / "snapshot.json"
        config.write_text(json.dumps(self.config))
        snapshot.write_text(json.dumps(self.snapshot))
        before = sorted(self.root.iterdir())
        with patch.object(sys, "argv", ["gate", "--preflight-writers",
                "--writer-config", str(config), "--writer-snapshot", str(snapshot)]), \
             patch.object(subprocess, "check_output", side_effect=AssertionError("external command")), \
             patch("builtins.print") as output:
            self.assertEqual(gate.main(), 2)
        result = json.loads(output.call_args.args[0])
        self.assertFalse(result["deployment_allowed"])
        self.assertTrue(result["local_exclusion_ready"])
        self.assertEqual(result["classification"], "SYNTHETIC_SNAPSHOT")
        self.assertEqual(before, sorted(self.root.iterdir()))

    def test_observer_only_reads_systemd_and_proc(self):
        calls = []
        def read(command, **kwargs):
            calls.append(command)
            if "list-unit-files" in command:
                return '[{"unit_file":"manager.service"}]'
            if "list-units" in command:
                return '[{"unit":"manager.service"}]'
            if "list-jobs" in command:
                return "[]"
            return "\n".join(k + "=" + v for k, v in self.snapshot["units"][0].items())
        with patch.object(subprocess, "check_output", side_effect=read), \
             patch.object(Path, "iterdir", return_value=iter([])):
            observed = gate.observe_local_writers()
        self.assertEqual(observed["errors"], [])
        self.assertEqual(observed["units"][0]["Id"], "manager.service")
        self.assertEqual({c[1] for c in calls}, {"list-units", "list-unit-files", "show", "list-jobs"})
        with patch.object(subprocess, "check_output", side_effect=OSError), \
             patch.object(Path, "iterdir", side_effect=PermissionError):
            observed = gate.observe_local_writers()
        self.assertTrue(observed["errors"])
        self.assertFalse(gate.writer_exclusion_preflight(self.config, observed)["local_exclusion_ready"])


if __name__ == "__main__":
    unittest.main()

"""C2B realistic host metadata; no live service access or authority."""
import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import ceo_stage6_deployment_gate as gate
from tests import test_stage6_writer_exclusion as legacy


class ProtectedWriterTests(unittest.TestCase):
    setUp = legacy.WriterExclusionTests.setUp
    unit = staticmethod(legacy.WriterExclusionTests.unit)
    assess = legacy.WriterExclusionTests.assess
    broker_fixture = legacy.WriterExclusionTests.broker_fixture

    def bounded(self):
        private = self.root / "state"
        private.mkdir(mode=0o700)
        info = private.stat()
        self.config["protected_roots"] = [dict(path=str(private), uid=info.st_uid,
                                              dev=info.st_dev, ino=info.st_ino)]
        self.pin.update(uid=2101, writer_cgroup="/system.slice/manager.service")
        self.snapshot["processes"] = [
            dict(pid=212, exe="/usr/lib/systemd/systemd", uids=[3000]*4,
                 cap_eff=0, start="10", writable_fds=["/var/log/session.log"],
                 cgroups=["0::/user.slice/user-3000.slice/user@3000.service/init.scope"]),
            dict(pid=88, exe="/usr/bin/unrelated", uids=[3001]*4,
                 cap_eff=0, start="20", writable_fds=["/tmp/cache"],
                 cgroups=["0::/system.slice/unrelated.service"]),
        ]
        return private

    def test_realistic_unrelated_processes_can_pass_local_only(self):
        self.bounded()
        self.snapshot["jobs"] = [dict(unit="unrelated.service", job=8)]
        self.assertTrue(self.assess()["local_exclusion_ready"])

    def test_bounded_closed_broker_with_unrelated_host_processes(self):
        self.broker_fixture()
        broker_process = self.snapshot["processes"][0]
        self.bounded()
        pin = self.config["units"]["broker.service"]
        pin.update(uid=os.geteuid(), writer_cgroup=pin["ControlGroup"])
        broker_process.update(uids=[pin["uid"]]*4, cap_eff=0,
                              start="123", writable_fds=[])
        self.snapshot["processes"].append(broker_process)
        self.assertTrue(self.assess()["local_exclusion_ready"])

    def test_relevant_rogue_uid_cgroup_fd_and_unknown_metadata_deny(self):
        private = self.bounded()
        original = copy.deepcopy(self.snapshot)
        cases = [
            ("uids", [2101]*4), ("uids", [0]*4),
            ("cap_eff", 2), ("cap_eff", 1 << 7), ("writable_fds", [str(private / "ledger.sqlite")]),
            ("writable_fds", [str(private / "old.sqlite") + " (deleted)"]),
            ("cgroups", ["0::/system.slice/manager.service/child"]),
            ("cgroups", []), ("cgroups", ["unknown"]), ("uids", None),
            ("writable_fds", None), ("start", None), ("pid", -1),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.snapshot = copy.deepcopy(original)
                self.snapshot["processes"][1][key] = value
                self.assertFalse(self.assess()["local_exclusion_ready"])

    def test_root_pins_jobs_errors_and_selected_timer_deny(self):
        self.bounded()
        original = copy.deepcopy(self.snapshot)
        for key, value in (("jobs", [dict(unit="manager.service")]),
                           ("jobs", [dict(job=9)]), ("errors", ["unreadable /proc"])):
            self.snapshot = copy.deepcopy(original)
            self.snapshot[key] = value
            self.assertFalse(self.assess()["local_exclusion_ready"])
        self.snapshot = original
        self.config["protected_roots"][0]["ino"] += 1
        self.assertFalse(self.assess()["local_exclusion_ready"])

    def test_live_double_sample_stability_and_selected_units(self):
        self.bounded()
        # Live control flow with mocked metadata, not a live host attestation.
        with patch.object(gate, "observe_local_writers",
                          return_value=self.snapshot) as observe:
            result = gate.writer_exclusion_preflight(self.config)
        self.assertTrue(result["local_exclusion_ready"])
        self.assertEqual(observe.call_count, 2)
        changed = copy.deepcopy(self.snapshot)
        changed["processes"][1]["start"] = "new PID incarnation"
        with patch.object(gate, "observe_local_writers",
                          side_effect=[self.snapshot, changed]):
            result = gate.writer_exclusion_preflight(self.config)
        self.assertIn("LOCAL_OBSERVATION_CHANGED", result["reasons"])
        self.assertFalse(result["deployment_allowed"])

    def test_readonly_c1_opens_and_bad_owner_mode_inode_symlink_deny(self):
        control, active = self.broker_fixture()
        real_open = os.open
        modes = []
        def opening(path, flags, *args, **kwargs):
            modes.append(flags)
            return real_open(path, flags, *args, **kwargs)
        before = [(p.stat().st_ino, p.read_bytes()) for p in (control, active)]
        with patch.object(os, "open", side_effect=opening):
            self.assertTrue(self.assess()["local_exclusion_ready"])
        self.assertTrue(modes)
        self.assertTrue(all(flags & os.O_ACCMODE == os.O_RDONLY for flags in modes))
        self.assertEqual(before, [(p.stat().st_ino, p.read_bytes()) for p in (control, active)])
        control.chmod(0o640)
        self.assertFalse(self.assess()["local_exclusion_ready"])
        control.chmod(0o600)
        identity = self.config["broker"]["identity"]
        self.config["broker"]["identity"] = "0:0:0:0:0:0"
        self.assertFalse(self.assess()["local_exclusion_ready"])
        self.config["broker"]["identity"] = identity
        control.rename(control.with_name("moved"))
        control.symlink_to(control.with_name("moved"))
        self.assertFalse(self.assess()["local_exclusion_ready"])

    def test_arbitrary_external_protected_root_and_root_change_deny(self):
        self.bounded()
        original = copy.deepcopy(self.config)
        self.config["protected_roots"][0]["path"] = "/etc"
        self.assertFalse(self.assess()["local_exclusion_ready"])
        self.config = original
        with patch.object(gate, "validate_protected_roots", side_effect=[[(1, 2)], [(1, 3)]]):
            result = self.assess()
        self.assertIn("PROTECTED_ROOTS_CHANGED", result["reasons"])

    def test_live_c1_branch_uses_pinned_readonly_fixture_and_owner(self):
        control, active = self.broker_fixture()
        broker = dict(self.config["broker"], uid=os.geteuid())
        # Only the constant is redirected; all owner/mode/inode/lock code runs.
        with patch.object(gate, "LIVE_C1_ROOT", control.parent):
            self.assertTrue(gate.broker_closed_observation(broker, synthetic=False))
            broker["uid"] += 1
            self.assertFalse(gate.broker_closed_observation(broker, synthetic=False))

    def test_selected_systemd_and_proc_fd_reads(self):
        private = self.bounded()
        proc = self.root / "proc"
        entry = proc / "88"
        (entry / "fd").mkdir(parents=True)
        (entry / "fdinfo").mkdir()
        (entry / "status").write_text("Uid:\t3001 3001 3001 3001\nCapEff:\t00000000\n")
        (entry / "stat").write_text("88 (a process name) " + " ".join(["S"] + ["0"]*18 + ["123"]))
        (entry / "cgroup").write_text("0::/system.slice/unrelated.service\n")
        (entry / "exe").symlink_to("/usr/bin/unrelated")
        (entry / "fd" / "4").symlink_to(private / "ledger.sqlite")
        (entry / "fdinfo" / "4").write_text("flags:\t0100002\n")
        (entry / "fd" / "5").symlink_to(private / "readonly.sqlite")
        (entry / "fdinfo" / "5").write_text("flags:\t0100000\n")
        calls = []
        def systemctl(command, **kwargs):
            calls.append(command)
            if "list-units" in command:
                return '[{"unit":"manager.service"},{"unit":"unrelated.service"}]'
            if "list-unit-files" in command:
                return '[{"unit_file":"manager.service"},{"unit_file":"unrelated.service"}]'
            if "list-jobs" in command:
                return "[]"
            self.assertEqual(command[2], "manager.service")
            return "\n".join(k + "=" + v for k, v in self.snapshot["units"][0].items())
        with patch.object(gate, "PROC_ROOT", proc), patch.object(
                gate.subprocess, "check_output", side_effect=systemctl):
            observed = gate.observe_local_writers(self.config)
            self.assertEqual(observed["errors"], [])
            self.assertEqual(observed["processes"][0]["writable_fds"],
                             [str(private / "ledger.sqlite")])
            self.assertFalse(gate.writer_exclusion_preflight(
                self.config, observed)["local_exclusion_ready"])
            (entry / "fdinfo" / "4").unlink()
            self.assertTrue(gate.observe_local_writers(self.config)["errors"])

    def test_live_c1_rejects_arbitrary_external_or_fixture_path_before_open(self):
        for path in ("/etc/control", "/tmp/control",
                     "/usr/local/lib/venture-control-broker-level2c/artifacts/../control",
                     str(self.root / "control")):
            with self.subTest(path=path), patch.object(os, "open",
                    side_effect=AssertionError("must reject before open")):
                self.assertFalse(gate.broker_closed_observation(
                    dict(path=path, uid=os.geteuid(), identity="0:0:0:0:0:0"),
                    synthetic=False))


if __name__ == "__main__":
    unittest.main()

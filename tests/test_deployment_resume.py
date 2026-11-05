"""Synthetic CEO restart/exclusion evidence; real processes, loopback broker only."""
import copy
import json
import os
from pathlib import Path
import runpy
import signal
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from agents.ceo import hierarchy_research_daemon as daemon
from agents.ceo.deployment_pause import cycle, lease, preflight
from agents.ceo.escalation_inbox import ROOT, canonical
from agents.ceo.hierarchy_providers import RecoveryImpossible
from agents.ceo.venture_workflow import hashed
from tests import test_ceo_candidate_acceptance as candidate
from tests import test_ceo_research_mtls_acceptance as base


def child_call(action, expected=0):
    pid = os.fork()
    if pid == 0:
        try:
            action()
        except BaseException:
            import traceback
            traceback.print_exc()
            os._exit(99)
        os._exit(0)
    deadline = time.monotonic() + 25
    while True:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            break
        if time.monotonic() > deadline:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            raise AssertionError("synthetic child deadline")
        time.sleep(0.01)
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != expected:
        raise AssertionError("unexpected synthetic child exit: " + str(status))
    return pid


class DeploymentPauseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = self.root / "ceo-deployment.lock"
        self.lock.touch(mode=0o600)

    def test_cross_process_pause_and_release_without_state_mutation(self):
        before = self.lock.stat()
        with lease(self.lock, exclusive=True) as held:
            self.assertTrue(held)
            def check():
                with cycle(dict(role="ceo", actor_id="service-ceo",
                                deployment_lock=str(self.lock))) as admitted:
                    self.assertFalse(admitted)
                self.assertFalse(preflight(self.lock)["ceo_exclusion_observed"])
            child_call(check)
        with lease(self.lock) as admitted:
            self.assertTrue(admitted)
        after = self.lock.stat()
        self.assertEqual((before.st_ino, before.st_size, before.st_mtime_ns),
                         (after.st_ino, after.st_size, after.st_mtime_ns))

    def test_active_daemon_cycle_denies_exclusive_preflight(self):
        config = dict(role="ceo", actor_id="service-ceo", endpoint="unused",
                      ca_file="unused", client_cert="unused", client_key="unused",
                      deployment_lock=str(self.lock))
        client = Mock()
        def listing():
            child_call(lambda: self.assertFalse(
                preflight(self.lock)["ceo_exclusion_observed"]))
            return []
        client.research_list.side_effect = listing
        with patch.object(daemon, "HierarchyClient", return_value=client):
            daemon.poll(config, once=True, worker_limit_override=4)
            client.research_list.assert_called_once()
            with lease(self.lock, exclusive=True):
                daemon.poll(config, once=True, worker_limit_override=4)
            client.research_list.assert_called_once()
        self.assertTrue(preflight(self.lock)["ceo_exclusion_observed"])
        self.assertFalse(preflight(self.lock)["deployment_allowed"])

    def test_missing_alias_permissions_and_other_roles_fail_closed(self):
        for path in (self.root / "missing", ROOT.parent / "outside"):
            self.assertEqual(preflight(path)["blockers"][0],
                             "INVALID_OR_UNAVAILABLE_DEPLOYMENT_LOCK")
            self.assertFalse(path.exists())
        alias = self.root / "alias"
        alias.symlink_to(self.lock)
        self.assertFalse(preflight(alias)["ceo_exclusion_observed"])
        self.lock.chmod(0o644)
        self.assertFalse(preflight(self.lock)["ceo_exclusion_observed"])
        self.lock.chmod(0o600)
        for role in ("manager", "worker"):
            with self.assertRaisesRegex(ValueError, "CEO-only"):
                with cycle(dict(role=role, deployment_lock=str(self.lock))):
                    self.fail("role admitted")

    def test_exception_releases_lock_and_legacy_deployer_denies_before_io(self):
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with lease(self.lock, exclusive=True):
                raise RuntimeError("fixture")
        self.assertTrue(preflight(self.lock)["ceo_exclusion_observed"])
        from scripts import level2d_acceptance_deploy_control as deploy
        for state in ("active", "activating", "deactivating", "failed", "", "unknown"):
            with patch.object(deploy, "run", return_value=state) as inspect, patch.object(
                    deploy.subprocess, "run", side_effect=AssertionError("restart forbidden")):
                with self.assertRaisesRegex(SystemExit, "DENY: P1-04"):
                    deploy.main()
                inspect.assert_called_once_with("systemctl", "show",
                    "venture-owner-research-ceo.service", "--property=ActiveState", "--value")
        with patch.object(deploy, "run", side_effect=OSError("unavailable")):
            with self.assertRaisesRegex(SystemExit, "DENY: P1-04"):
                deploy.main()
        with patch.object(deploy, "run", return_value="inactive"):
            deploy.require_research_ceo_inactive()

    def test_preflight_cli_denies_even_when_exclusion_available(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(["python3", "-B", "scripts/ceo_stage6_deployment_gate.py",
            "--preflight-resume", "--deployment-lock", str(self.lock)],
            cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["decision"], "DENY")
        self.assertTrue(report["ceo_exclusion_observed"])
        self.assertFalse(report["resume_verified"])


class DeploymentResumeTests(candidate.CEOCandidateAcceptanceTests):
    test_three_round_process_exit_recovery_preserves_signed_trace_and_quota = None
    test_two_created_synthetic_ventures_reject_cross_bound_reservation = None

    def setUp(self):
        super().setUp()
        self.lock = self.root / "ceo-deployment.lock"
        self.lock.touch(mode=0o600)
        self.configs["service-ceo"]["deployment_lock"] = str(self.lock)

    def ledger(self):
        # Exact rows, not only counts: day/token charges and all identities persist.
        with sqlite3.connect(self.authority / "resources.sqlite") as db:
            names = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {n: db.execute('SELECT * FROM "' + n + '" ORDER BY 1').fetchall()
                    for n in names}

    def test_pause_leaves_shared_manager_worker_traffic_running(self):
        self.poll("service-ceo")  # Establish original centrally charged session.
        with lease(self.lock, exclusive=True) as held:
            self.assertTrue(held)
            before = self.state()
            charged = self.ledger()
            child_call(lambda: self.poll("service-ceo"))
            self.assertEqual(self.state(), before)
            self.assertEqual(self.ledger(), charged)
            # Same shared broker remains reachable and Manager advances its workflow.
            self.assertEqual(self.poll("service-manager")["state"], "DECOMPOSITION_REVIEW")
        self.assertEqual(self.poll("service-ceo")["state"], "WORKER_PENDING")
        with lease(self.lock, exclusive=True):
            self.assertEqual(self.poll("worker-a")["decomposition"]["states"]["A"], "COMPLETE")
            self.poll("worker-b")
            self.assertEqual(self.poll("worker-c")["state"], "MANAGER_REVIEW")
            self.assertEqual(self.poll("service-manager")["state"], "CEO_REVIEW")
        self.reopen(self.state())
        print(canonical(dict(scenario="CEO_PAUSE_SHARED_BROKER", manager="ADVANCED",
                             worker="ADVANCED", ceo="EXCLUDED", signed_lineage="VERIFIED")),
              flush=True)

    def test_completed_response_process_restart_and_daemon_code_rollback_no_inference(self):
        reviewed = self.round_review(1)
        self.exit_ceo_at("RESPONSE")
        original = self.ledger()
        self.reopen(reviewed)
        # Roll back only the daemon's code, keeping all current signed state/charges.
        # This is deliberately not a claim about arbitrary release compatibility.
        raw = subprocess.check_output(
            ["git", "show", "f336689:agents/ceo/hierarchy_research_daemon.py"], cwd=ROOT)
        old = self.root / "baseline_daemon.py"
        old.write_bytes(raw)
        baseline = runpy.run_path(str(old))["poll"]
        def resume():
            with patch("agents.ceo.venture_exercise.configured_provider",
                       side_effect=AssertionError("completed inference repeated")):
                baseline(self.configs["service-ceo"], once=True, worker_limit_override=4)
        child_call(resume)
        self.assertEqual(self.ledger(), original)
        after = self.state()
        self.assertEqual(after["state"], "MANAGER_PENDING")
        signed = after["last_command"]["payload"]["review"]
        self.keys["service-ceo"].public_key().verify(
            bytes.fromhex(signed["signature"]), canonical(signed["packet"]).encode())
        self.reopen(after)
        # Resubmit the committed signed command: no duplicate state/charge.
        child_call(lambda: self.client().apply(after["last_command"], after["signature"]))
        self.assertEqual(self.ledger(), original)
        self.assertEqual(self.state(), after)
        print(canonical(dict(scenario="COMPLETED_RESPONSE_CODE_ROLLBACK",
            daemon_sha256=__import__("hashlib").sha256(raw).hexdigest(),
            scope="DAEMON_ONLY_SAME_CURRENT_LEDGER", quota="EXACT_ROWS_UNCHANGED",
            result="SIGNED_CONTINUATION_NO_PROVIDER")), flush=True)

    def test_pending_execution_survives_process_death_and_repeated_restart_held(self):
        reviewed = self.round_review(1)
        marker = self.root / "synthetic-provider-count"
        original_call = base.SyntheticModel.__call__
        def lose(instance, request, tools):
            if instance.role == "ceo" and "signed_artifacts" in request["opportunity"]:
                with marker.open("a") as out:
                    out.write("one synthetic invocation\n")
                    out.flush()
                    os.fsync(out.fileno())
                os._exit(81)  # Broker PENDING is already durably committed.
            return original_call(instance, request, tools)
        def crash():
            with patch.object(base.SyntheticModel, "__call__", lose):
                self.poll("service-ceo")
        child_call(crash, 81)
        self.assertTrue(preflight(self.lock)["ceo_exclusion_observed"])
        saved = self.ledger()
        self.assertIn("PENDING", [r[-1] for r in saved["remote_executions"]])
        def restart():
            with patch("agents.ceo.venture_exercise.configured_provider",
                       side_effect=AssertionError("ambiguous retry forbidden")):
                with self.assertRaisesRegex(RecoveryImpossible, "PROVIDER_EXECUTION_AMBIGUOUS"):
                    self.poll("service-ceo")
        for _ in range(2):
            child_call(restart)
            self.assertEqual(self.ledger(), saved)
            self.assertEqual(self.state(), reviewed)
            self.reopen(reviewed)
        self.assertEqual(marker.read_text(), "one synthetic invocation\n")
        print(canonical(dict(scenario="PENDING_PROCESS_DEATH", restarts=2,
            outcome="HELD", quota="EXACT_ROWS_UNCHANGED", synthetic_invocations=1)), flush=True)

    def test_invalid_signed_review_not_reauthorized_on_restart(self):
        reviewed = self.round_review(1)
        # Obtain the synthetic signed packet but crash before the signed command.
        from agents.ceo import ceo_research_review
        cfg = daemon.allowed_config(self.configs["service-ceo"], self.flow, reviewed)
        packet = ceo_research_review.review(cfg, reviewed, self.client())
        path = Path(cfg["state_dir"]).parent / "research-reviews" / (self.flow + ".json")
        packet = copy.deepcopy(packet)
        packet["packet"]["assessment"]["next_internal_task"] = "Tampered synthetic task"
        self.write_json(path, packet)
        charged = self.ledger()
        def restart():
            with self.assertRaisesRegex(ValueError, "HTTP (400|503)"):
                self.poll("service-ceo")
        child_call(restart)
        self.assertEqual(self.ledger(), charged)
        self.assertEqual(self.state(), reviewed)
        self.reopen(reviewed)
        print(canonical(dict(scenario="SIGNED_REVIEW_TAMPER_RESTART",
                             outcome="DENIED", quota="EXACT_ROWS_UNCHANGED")), flush=True)

"""Isolated legacy signed histories, broker admission and periodic recovery; no live I/O."""
import copy
import json
import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from agents.ceo.escalation_inbox import EscalationInbox, canonical
from agents.ceo.venture_workflow import VentureWorkflow, hashed, research_rounds, research_session, research_tasks
from agents.ceo.hierarchy_gateway import HierarchyGateway
from agents.ceo import hierarchy_research_daemon as daemon, worker_inference as wi
from tests import test_research_broker_admission as admission
from tests.test_worker_inference import FakeQuota, FakeProvider


class LegacyWorkerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.admission = admission.ResearchBrokerAdmissionTests(methodName="runTest")
        self.admission.setUp()
        self.fx = self.admission.fx
        self.addCleanup(self.fx.doCleanups)
        self.gate = self.fx.gateway
        self.flow = self.fx.flow
        self.keys = {"service-ceo": self.fx.keys["ceo"],
                     "service-manager": self.fx.keys["manager"],
                     "service-worker": self.fx.keys["worker"]}
        for actor in ("worker-a", "worker-b", "worker-c"):
            key = Ed25519PrivateKey.generate()
            self.keys[actor] = key
            self.gate.actors[actor] = ("worker", key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
        cmd = copy.deepcopy(self.admission.command)
        cmd["payload"]["scope"]["worker_id"] = "service-worker"
        cmd["scope_hash"] = hashed(cmd["payload"]["scope"])
        # Historical events are created with the signed journal API, never snapshot edits.
        inbox = EscalationInbox(self.gate.directory / "inbox.sqlite",
                               ceo_public_key=self.gate.actors["service-ceo"][1])
        journal = self.journal()
        try:
            journal.create(cmd, self.sign(cmd), inbox=inbox, item_id=self.flow)
            delegated = self.command("delegate", "service-manager", dict(reason="Historical legacy delegation"))
            journal.apply(delegated, self.sign(delegated))
        finally:
            journal.close()
            inbox.close()
        self.resources = self.fx.base / "resources.sqlite"
        with sqlite3.connect(self.resources) as db:
            db.execute("CREATE TABLE reservations(day TEXT,identity TEXT UNIQUE,tokens INTEGER)")
        for target in ("agents.ceo.service_identity.AUTHORITY_DIRECTORY",
                       "agents.ceo.worker_inference.AUTHORITY_DIRECTORY"):
            p = patch(target, self.fx.base)
            p.start()
            self.addCleanup(p.stop)
        self.policy = dict(domain="worker-preparation-inference-v1", enabled=True, epoch=1,
            actor_ids=["worker-a", "worker-b", "worker-c"], model="gpt-6-luna",
            endpoint=FakeProvider.endpoint, maximum_requests=4, maximum_output_tokens=512)
        for p in (patch.object(wi, "current_policy", return_value=self.policy),
                  patch.object(wi, "ProviderQuota", return_value=FakeQuota())):
            p.start()
            self.addCleanup(p.stop)

    def journal(self):
        return VentureWorkflow(self.gate.directory / "workflow.sqlite", actors=self.gate.actors)

    def state(self):
        return self.gate.state(self.flow)

    def sign(self, cmd):
        return self.keys[cmd["actor_id"]].sign(canonical(cmd).encode()).hex()

    def command(self, action="recover_legacy_worker", actor="service-ceo", payload=None):
        state = self.state()
        now = datetime.now(timezone.utc)
        self.serial = getattr(self, "serial", 0) + 1
        return dict(workflow_id=self.flow, request_id="legacy-test-" + str(self.serial),
            actor_id=actor, role=self.gate.actors[actor][0], origin="control_plane",
            action=action, revision=state["revision"], previous_hash=hashed(state),
            version=state["version"], scope_hash=state["scope_hash"],
            evidence=state["last_command"]["evidence"],
            payload=payload if payload is not None else dict(reason="Retired Worker recovery"),
            issued_at=now.isoformat(), expires_at=(now+timedelta(minutes=5)).isoformat(), live=False)

    def apply(self, cmd):
        role = {"ceo": "quota-ceo", "manager": "poll", "worker": "worker"}[cmd["role"]]
        return self.gate.apply(dict(command=cmd, signature=self.sign(cmd)), role=role)

    def audit(self):
        journal = self.journal()
        try:
            journal.verify()
            return list(journal.db.execute("SELECT * FROM audit ORDER BY sequence"))
        finally:
            journal.close()

    def legacy_charge(self, count):
        # Synthetic accounting fixtures only; pre-Task02 rows lack a charge table.
        with sqlite3.connect(self.resources) as db:
            db.execute("CREATE TABLE IF NOT EXISTS worker_reservations(identity TEXT PRIMARY KEY, request TEXT NOT NULL)")
            for i in range(count):
                db.execute("INSERT INTO worker_reservations VALUES(?,?)",
                    ("retained-" + str(i), canonical(dict(workflow_id=self.flow, worker_id="service-worker", policy=dict(maximum_requests=4)))))

    def decompose(self):
        assignments = [dict(id=name, worker_id=actor, task=task, depends_on=[] if name != "C" else ["A", "B"])
            for name, actor, task in zip(("A", "B", "C"), ("worker-a", "worker-b", "worker-c"), research_tasks(self.state()))]
        self.apply(self.command("propose_decomposition", "service-manager", dict(assignments=assignments)))
        self.apply(self.command("approve_decomposition", payload=dict(proposal_hash=hashed(assignments))))

    def worker_payload(self, name, actor):
        from agents.ceo.hierarchy_model_callbacks import RESEARCH_SYSTEM
        state = self.state()
        request = dict(system=RESEARCH_SYSTEM, json_object_mode=True, opportunity=dict(
            role="worker", state="WORKER_PENDING", workflow_id=self.flow, assignment_id=name,
            snapshot_sha256=hashed(state), permitted_actions=["submit"], scope_hash=state["scope_hash"]))
        reservation = dict(domain="worker-preparation-call-v1", workflow_id=self.flow,
            worker_id=actor, assignment_id=name, snapshot_sha256=hashed(state),
            identity="recovered-" + name, attempt="a"*64, request_sha256=hashed(request), policy=self.policy)
        return dict(reservation=reservation, request=request)

    def test_signed_rev2_history_append_only_same_scope_reopen_and_exact_replay(self):
        before, rows = self.state(), self.audit()
        self.assertEqual(before["revision"], 2)
        command = self.command()
        after = self.apply(command)
        self.assertEqual(after["state"], "MANAGER_PENDING")
        for field in ("scope", "scope_hash", "version", "used_units", "handoff", "evidence", "venture_id"):
            self.assertEqual(after[field], before[field], field)
        self.assertEqual(research_rounds(after), research_rounds(before))
        self.assertEqual(research_session(after), research_session(before))
        self.assertEqual(self.audit()[:-1], rows)
        self.assertEqual(self.apply(command), after)
        reopened = HierarchyGateway(self.gate.directory, self.gate.actors)
        self.assertEqual(reopened.state(self.flow), after)
        self.assertEqual(len(self.audit()), len(rows)+1)

    def test_conflicting_duplicate_stale_replay_and_role_fail_without_new_event(self):
        command = self.command()
        self.apply(command)
        rows = self.audit()
        for altered in (dict(command, request_id="other-attempt"),
                        dict(command, payload=dict(reason="conflicting body")),
                        self.command()):
            with self.assertRaises(ValueError):
                self.apply(altered)
        self.assertEqual(self.audit(), rows)

    def test_unauthorized_signer_and_changed_approval_fail_closed(self):
        for actor in ("service-manager", "service-worker", "worker-a"):
            with self.assertRaises(ValueError):
                self.apply(self.command(actor=actor))
        command = self.command()
        with self.assertRaises(Exception):
            self.gate.apply(dict(command=command, signature=self.keys["service-manager"].sign(canonical(command).encode()).hex()),
                            role="quota-ceo")
        original = copy.deepcopy(self.fx.snapshot)
        for mutate in ("revoked", "scope", "proposal", "duplicate"):
            self.fx.snapshot = copy.deepcopy(original)
            if mutate == "revoked":
                self.fx.snapshot["records"] = []
            elif mutate == "scope":
                self.fx.snapshot["research_assignments"][0]["scope"] = "EXTERNAL"
            elif mutate == "proposal":
                self.fx.snapshot["research_assignments"][0]["proposal"] = dict(self.fx.approval["proposal"], title="Changed")
            else:
                self.fx.snapshot["research_assignments"].append(copy.deepcopy(self.fx.approval))
            self.fx.write_snapshot()
            with self.assertRaises(ValueError):
                self.apply(command)
        self.assertEqual(self.state()["revision"], 2)

    def test_legacy_charges_preserved_abc_fake_execution_and_no_duplicate_paid_call(self):
        self.legacy_charge(1)
        before = self.gate.worker_research_counts(self.flow)
        self.apply(self.command())
        after = self.gate.worker_research_counts(self.flow)
        self.assertEqual((after["round_count"], after["venture_count"]), (1, 1))
        self.assertEqual(before["round_count"], after["round_count"])
        self.decompose()
        provider = FakeProvider()
        for name, actor in zip(("A", "B", "C"), ("worker-a", "worker-b", "worker-c")):
            payload = self.worker_payload(name, actor)
            wi.reserve_worker(payload["reservation"], actor=actor, hierarchy=self.gate)
            result = wi.execute_worker(payload, actor=actor, hierarchy=self.gate, provider=provider)
            self.assertEqual(wi.execute_worker(payload, actor=actor, hierarchy=self.gate, provider=provider), result)
            self.apply(self.command("submit", actor, dict(assignment_id=name, units=1)))
        self.assertEqual(provider.calls, 3)
        self.assertEqual(self.state()["state"], "MANAGER_REVIEW")
        counts = self.gate.worker_research_counts(self.flow)
        self.assertEqual((counts["round_count"], counts["venture_count"]), (4, 4))
        self.audit()
        for field in ("operational_authority", "external_actions_allowed", "execution_performed", "money_released"):
            self.assertIs(self.state()[field], False)

    def test_insufficient_quota_missing_ledger_and_effort_fail_closed(self):
        self.legacy_charge(2)
        with self.assertRaisesRegex(ValueError, "allowance"):
            self.apply(self.command())
        self.assertEqual(self.state()["revision"], 2)
        self.resources.unlink()
        with self.assertRaises(sqlite3.OperationalError):
            self.apply(self.command())
        with sqlite3.connect(self.resources) as db:
            db.execute("CREATE TABLE reservations(day TEXT,identity TEXT UNIQUE,tokens INTEGER)")
        # A legitimate signed legacy submission and improvement consumes effort.
        journal = self.journal()
        try:
            cmd = self.command("submit", "service-worker", dict(units=3))
            journal.apply(cmd, self.sign(cmd))
            cmd = self.command("improve", "service-manager", dict(reason="Legacy correction"))
            journal.apply(cmd, self.sign(cmd))
        finally:
            journal.close()
        with self.assertRaisesRegex(ValueError, "recovery denied"):
            self.apply(self.command())
        self.assertEqual(self.state()["used_units"], 3)
        self.audit()

    def test_cumulative_ceiling_and_stale_accounting_fail_without_append(self):
        counts = self.gate.worker_research_counts(self.flow)
        rows = self.audit()
        for changed in (dict(counts, venture_count=10),
                        dict(counts, snapshot_sha256="0"*64)):
            with patch.object(self.gate, "worker_research_counts", return_value=changed):
                with self.assertRaisesRegex(ValueError, "allowance"):
                    self.apply(self.command())
        self.assertEqual(self.audit(), rows)

    def test_historical_correction_version_is_retained_without_another_correction(self):
        journal = self.journal()
        try:
            for action, payload in (
                    ("hold", dict(reason="Historical correction")),
                    ("resume", dict(reason="Historical correction")),
                    ("revise", dict(reason="Historical correction", scope=self.state()["scope"], version=2))):
                cmd = self.command(action, payload=payload)
                journal.apply(cmd, self.sign(cmd))
            cmd = self.command("delegate", "service-manager", dict(reason="Historical corrected delegation"))
            journal.apply(cmd, self.sign(cmd))
        finally:
            journal.close()
        self.assertEqual(self.state()["version"], 2)
        rows = self.audit()
        self.apply(self.command())
        self.assertEqual(self.state()["version"], 2)
        self.assertEqual(self.audit()[:-1], rows)

    def test_changed_payload_cannot_reset_scope_budget_version_or_round(self):
        for key, value in (("scope", self.state()["scope"]), ("version", 2), ("round", 2), ("used_units", 0)):
            with self.assertRaises(ValueError):
                self.apply(self.command(payload=dict(reason="repair", **{key: value})))
        self.assertEqual(self.state()["revision"], 2)

    def test_daemon_periodic_poll_response_loss_restart_and_retirement(self):
        keyfile = self.fx.base / "ceo.key"
        keyfile.write_bytes(self.keys["service-ceo"].private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        config = dict(role="ceo", actor_id="service-ceo", signing_key=str(keyfile),
            state_dir=str(self.fx.base / "ceo"), context={}, endpoint="fixture", ca_file="fixture",
            client_cert="fixture", client_key="fixture")
        client = Mock()
        client.research_list.side_effect = lambda: self.gate.research_list()
        client.read.side_effect = lambda flow: self.gate.state(flow)
        def lost_response(cmd, signature):
            self.gate.apply(dict(command=cmd, signature=signature), role="quota-ceo")
            raise OSError("lost after signed commit")
        client.apply.side_effect = lost_response
        with patch.object(daemon, "HierarchyClient", return_value=client), \
             patch.object(daemon, "role_tick") as paid_tick, \
             patch.object(daemon, "ensure_research_session") as session:
            with self.assertRaises(OSError):
                daemon.poll(config, once=True, worker_limit_override=4)
            # Fresh daemon polls see committed routing and never repeat migration.
            for _ in range(2):
                daemon.poll(config, once=True, worker_limit_override=4)
            self.assertEqual(client.apply.call_count, 1)
            self.assertEqual(session.call_count, 2)
            paid_tick.assert_not_called()
        with self.assertRaisesRegex(ValueError, "retired"):
            self.apply(self.command("delegate", "service-manager", dict(reason="Historical legacy delegation")))
        self.decompose()
        with self.assertRaises(ValueError):
            self.apply(self.command())
        self.audit()

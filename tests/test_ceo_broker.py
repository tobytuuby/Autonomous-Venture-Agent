"""Signed synthetic mTLS CEO execution; temporary existing-ledger layout only."""
import copy
import os
import signal
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from agents.ceo.ceo_broker import PROOF_PATH, EXECUTE_PATH
from agents.ceo.ceo_research_review import review
from agents.ceo.escalation_inbox import canonical
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_providers import RecoveryImpossible
from agents.ceo.owner_idea_inbox import digest as proposal_digest
from agents.ceo.venture_workflow import hashed
from tests import test_ceo_research_mtls_acceptance as base


class CEOBrokerTests(base.ResearchMtlsAcceptanceTests):
    test_r1_signed_roles_synthesis_disposition_and_checkpoint_retries = None
    test_reservation_checkpoint_worker_identity_quota_hold_is_durable = None
    test_negative_tls_role_signature_stale_identity_and_denied_operations = None

    def setUp(self):
        original = base.isolated_server
        def server(**kwargs):
            from agents.ceo.ceo_broker import execute_ceo
            kwargs["ceo_execute"] = lambda payload, *, actor: execute_ceo(
                payload, actor=actor, hierarchy=self.gate, provider=self.models["ceo"])
            self.server_kwargs = dict(kwargs)
            return original(**kwargs)
        with patch.object(base, "isolated_server", server):
            super().setUp()
        self.configs["service-ceo"]["ceo_broker"] = True

    def pending(self):
        self.ready()
        for actor in ("worker-a", "worker-b", "worker-c", "service-manager"):
            self.poll(actor)
        state = self.state()
        self.assertEqual(state["state"], "CEO_REVIEW")
        self.config = base.daemon.allowed_config(self.configs["service-ceo"], self.flow, state)
        captured = []
        def stop(client, payload):
            captured.append(copy.deepcopy(payload))
            raise OSError("synthetic crash before proof")
        with patch.object(HierarchyClient, "ceo_proof", stop):
            with self.assertRaisesRegex(OSError, "before proof"):
                review(self.config, state, self.client())
        self.payload = captured[0]
        self.original_state = state
        self.ceo_before = len(self.models["ceo"].calls)
        return self.payload

    def resume(self):
        # A broker-backed CEO needs no local provider or authority ledger.
        with patch("agents.ceo.venture_exercise.configured_provider",
                   side_effect=AssertionError("CEO local credentials forbidden")):
            return review(self.config, self.original_state, self.client())

    def reserve(self, payload=None):
        return self.client()._request("POST", "/v1/inference/reservations",
                                    (payload or self.payload)["reservation"])

    def wire(self, identity, path, payload):
        fixture = self.tls()
        fixture.srv = self.server
        return fixture.request(identity, "POST", path, body=canonical(payload))

    def ledger_bytes(self):
        return (self.authority / "resources.sqlite").read_bytes()

    def test_readonly_absent_exact_complete_proof_and_response_replay(self):
        p = self.pending()
        before = self.ledger_bytes()
        proof = self.client().ceo_proof(p)
        self.assertEqual((proof["reservation_status"], proof["execution_status"]),
                         ("ABSENT", "NOT_STARTED"))
        self.assertEqual(self.ledger_bytes(), before)
        self.assertNotIn("result", proof)
        self.assertNotIn("context", proof)
        self.assertEqual(self.wire("other", EXECUTE_PATH, p)[0], 400)
        self.assertEqual(self.ledger_bytes(), before)
        self.reserve()
        charged = self.counts()
        before = self.ledger_bytes()
        self.assertEqual(self.client().ceo_proof(p)["reservation_status"], "EXACT")
        self.assertEqual(self.ledger_bytes(), before)
        original = self.client().ceo_execute(p)
        before = self.ledger_bytes()
        self.assertEqual(self.client().ceo_proof(p)["execution_status"], "COMPLETE")
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(self.client().ceo_execute(p), original)
        self.assertEqual(self.reserve()["reserved"], True)
        packet = self.resume()
        self.assertEqual(packet["state"], "COMPLETE")
        self.assertEqual(self.resume(), packet)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before + 1)
        self.assertEqual(self.counts()["reservations"], charged["reservations"])
        self.assertEqual(self.counts()["remote_executions"], charged["remote_executions"] + 1)
        self.reopen(self.original_state)

    def test_pinned_certificates_and_manager_worker_routes_remain_isolated(self):
        p = self.pending()
        before = self.ledger_bytes()
        for identity in ("cap", "poll", "worker-a", "worker-b", "worker-c", "rogue", "rollover"):
            for path in (PROOF_PATH, EXECUTE_PATH):
                self.assertEqual(self.wire(identity, path, p)[0], 403, (identity, path))
        for path in ("/v1/inference/execute", "/v1/inference/worker-execute",
                     "/v1/inference/worker-reservations"):
            self.assertEqual(self.wire("other", path, p)[0], 403)
        manager = copy.deepcopy(p)
        manager["reservation"].update(actor="service-manager", role="manager")
        manager["request"]["opportunity"]["role"] = "manager"
        for path in (PROOF_PATH, EXECUTE_PATH):
            self.assertEqual(self.wire("other", path, manager)[0], 400)
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before)

    def test_exact_binding_tampering_and_live_revocation_fail_closed(self):
        p = self.pending()
        self.reserve()
        before = self.ledger_bytes()
        variants = []
        for field, value in (("attempt", "b"*64), ("identity", "ceo-other"),
                             ("request_sha256", "c"*64), ("execution_mode", "LEGACY")):
            changed = copy.deepcopy(p)
            changed["reservation"][field] = value
            variants.append(changed)
        changed = copy.deepcopy(p)
        changed["request"]["opportunity"]["role"] = "manager"
        changed["reservation"]["request_sha256"] = hashed(changed["request"])
        variants.append(changed)
        changed = copy.deepcopy(p)
        changed["reservation"]["context"]["rounds"] = 2
        variants.append(changed)
        changed = copy.deepcopy(p)
        changed["reservation"]["policy"]["maximum_requests"] = 7
        variants.append(changed)
        for changed in variants:
            # A fresh valid identity may prove ABSENT, but can never execute
            # the original reservation or borrow its charge.
            self.assertEqual(self.wire("other", EXECUTE_PATH, changed)[0], 400)
        self.write_json(self.authority / "authority.json",
                        dict(enabled=True, epoch=1, revoked=["service-ceo"]))
        self.assertEqual(self.wire("other", PROOF_PATH, p)[0], 400)
        self.assertEqual(self.wire("other", EXECUTE_PATH, p)[0], 400)
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before)

    def test_pending_provider_outcome_survives_restart_and_never_reexecutes(self):
        p = self.pending()
        self.reserve()
        original = base.SyntheticModel.__call__
        def lost(model, request, tools):
            result = original(model, request, tools)
            if model is self.models["ceo"]:
                raise OSError("synthetic provider outcome lost")
            return result
        with patch.object(base.SyntheticModel, "__call__", lost):
            self.assertEqual(self.wire("other", EXECUTE_PATH, p)[0], 503)
        before = self.ledger_bytes()
        self.assertEqual(self.client().ceo_proof(p)["execution_status"], "PENDING")
        self.reopen(self.original_state)
        for _ in range(2):
            with self.assertRaisesRegex(RecoveryImpossible, "PROVIDER_EXECUTION_AMBIGUOUS"):
                self.resume()
            self.assertEqual(self.wire("other", EXECUTE_PATH, p)[0], 400)
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before + 1)

    def test_concurrent_exact_retries_execute_once_and_charge_once(self):
        p = self.pending()
        self.reserve()
        charged = self.counts()
        with ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(lambda _: self.wire("other", EXECUTE_PATH, p)[0], range(4)))
        self.assertIn(200, codes)
        self.assertTrue(set(codes) <= {200, 400})
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before + 1)
        self.assertEqual(self.counts()["reservations"], charged["reservations"])
        self.assertEqual(self.counts()["remote_executions"], charged["remote_executions"] + 1)

    def test_missing_or_inconsistent_evidence_never_bootstraps_or_mutates(self):
        p = self.pending()
        ledger = self.authority / "resources.sqlite"
        with sqlite3.connect(ledger) as db:
            db.execute("DELETE FROM exchange_sessions")
        before = self.ledger_bytes()
        self.assertEqual(self.wire("other", PROOF_PATH, p)[0], 400)
        self.assertEqual(self.wire("other", EXECUTE_PATH, p)[0], 400)
        self.assertEqual(self.ledger_bytes(), before)
        ledger.unlink()
        self.assertEqual(self.wire("other", PROOF_PATH, p)[0], 503)
        self.assertFalse(ledger.exists())
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before)

    def test_two_created_signed_ventures_cannot_borrow_ceo_reservation(self):
        p = self.pending()
        self.reserve()
        before = self.counts()
        original_flow = self.flow
        other = dict(base.admission.PROPOSAL, title="Synthetic Stage7 separate venture")
        fingerprint = proposal_digest(other)
        self.flow = self.fx.flow = "research-" + fingerprint[:24]
        self.fx.fingerprint = fingerprint
        self.fx.approval = dict(self.fx.approval, proposal=other, proposal_digest=fingerprint)
        self.fx.snapshot["records"].append(dict(cycle_id="initial-test",
            proposal_digest=fingerprint, decision="APPROVE_FOR_RESEARCH"))
        self.fx.snapshot["research_assignments"].append(self.fx.approval)
        self.fx.write_snapshot()
        commit = HierarchyClient.bootstrap_commit
        def distinct(client, command, signature):
            command = dict(command, request_id="stage7-second-synthetic-create")
            return commit(client, command, self.fx.sign(command))
        with patch.object(base.admission, "PROPOSAL", other), patch.object(
                HierarchyClient, "bootstrap_commit", distinct):
            self.bootstrap()
        second = self.state()
        self.flow = original_flow
        self.assertNotEqual(second["id"], self.flow)
        cross = copy.deepcopy(p)
        cross["reservation"]["context"].update(
            session_id=second["id"], venture_id=second["id"])
        for path in (PROOF_PATH, EXECUTE_PATH):
            self.assertEqual(self.wire("other", path, cross)[0], 400)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.client().read(second["id"]), second)
        self.assertEqual(self.state(), self.original_state)
        self.reopen(self.original_state)

    def test_real_synthetic_client_exit_after_charge_and_response(self):
        if not hasattr(os, "fork"):
            self.skipTest("POSIX fixture only")
        self.pending()
        charged = self.counts()
        original = HierarchyClient._request
        # Parent serves the fake broker; only the synthetic client child exits.
        for checkpoint, code in (("/v1/inference/reservations", 71), (EXECUTE_PATH, 72)):
            def exit_at(client, method, path, payload=None):
                result = original(client, method, path, payload)
                if path == checkpoint:
                    os._exit(code)
                return result
            pid = os.fork()
            if pid == 0:
                try:
                    with patch.object(HierarchyClient, "_request", exit_at):
                        self.resume()
                except BaseException:
                    import traceback
                    traceback.print_exc()
                    os._exit(74)
                os._exit(75)
            deadline = time.monotonic() + 20
            while True:
                ended, status = os.waitpid(pid, os.WNOHANG)
                if ended:
                    break
                if time.monotonic() >= deadline:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    self.fail("synthetic client child timeout")
                time.sleep(0.02)
            self.assertTrue(os.WIFEXITED(status))
            self.assertEqual(os.WEXITSTATUS(status), code)
            self.reopen(self.original_state)
        self.assertEqual(self.resume()["state"], "COMPLETE")
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before + 1)
        self.assertEqual(self.counts()["reservations"], charged["reservations"] + 1)
        self.assertEqual(self.counts()["remote_reservations"], charged["remote_reservations"] + 1)

    def test_readonly_orphan_charge_and_changed_signed_snapshot_are_denied(self):
        p = self.pending()
        self.reserve()
        with sqlite3.connect(self.authority / "resources.sqlite") as db:
            db.execute("DELETE FROM reservations WHERE identity IN "
                       "(SELECT identity FROM remote_reservations WHERE request=?)",
                       (canonical(p["reservation"]),))
        before = self.ledger_bytes()
        for path in (PROOF_PATH, EXECUTE_PATH):
            self.assertEqual(self.wire("other", path, p)[0], 400)
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before)

    def test_proof_schema_rejects_uncorrelated_broker_reply(self):
        p = self.pending()
        client = self.client()
        valid = client.ceo_proof(p)
        for key, value in (("domain", "wrong"), ("session_sha256", "0"*64),
                           ("reservation_sha256", "0"*64), ("request_sha256", "0"*64),
                           ("reservation_status", True), ("execution_status", "COMPLETE")):
            with self.subTest(field=key), patch.object(client, "_request",
                    return_value=dict(valid, **{key: value})):
                with self.assertRaises(ValueError):
                    client.ceo_proof(p)
        with patch.object(client, "_request", return_value=dict(valid, result="private")):
            with self.assertRaises(ValueError):
                client.ceo_proof(p)

    def test_broker_listener_restart_retains_original_complete_result(self):
        import threading
        p = self.pending()
        self.reserve()
        result = self.client().ceo_execute(p)
        charged = self.counts()
        before = self.ledger_bytes()
        self.server.shutdown()
        self.server.server_close()
        self.server = base.isolated_server(**self.server_kwargs)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        def stop():
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        for config in self.configs.values():
            config["endpoint"] = "https://localhost:" + str(self.server.server_port) + "/v1/assignments/pending"
        self.config["endpoint"] = self.configs["service-ceo"]["endpoint"]
        self.assertEqual(self.client().ceo_proof(p)["execution_status"], "COMPLETE")
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(self.client().ceo_execute(p), result)
        self.assertEqual(self.resume()["state"], "COMPLETE")
        self.assertEqual(self.counts(), charged)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before + 1)

    def test_unpinned_or_malformed_proof_has_no_provider_or_ledger_effect(self):
        self.pending()
        before = self.ledger_bytes()
        fixture = self.tls()
        fixture.srv = self.server
        for raw in ('{}', '{"reservation":{},"reservation":{},"request":{}}',
                    canonical(dict(self.payload, reconcile_only=True)), '[]'):
            code, body = fixture.request("other", "POST", PROOF_PATH, body=raw)
            self.assertIn(code, (400, 503))
            self.assertNotIn("result", body)
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(len(self.models["ceo"].calls), self.ceo_before)

"""Supplemental private signed evidence + safe per-scenario decision log.

Run from project root with PYTHONPATH=.; ephemeral fixtures only. Signed command
bytes remain exclusively in ignored 0700 artifacts, in 0600 files.
"""
from copy import deepcopy
import io
import json
import sys
import unittest
from unittest.mock import patch

from agents.ceo.authenticated_handoff import AuthenticatedHandoff
from agents.ceo.control_plane import ControlPlane
from agents.ceo.escalation_inbox import ROOT, digest
from agents.ceo.scheduled_exercise import write_json
from agents.ceo.venture_workflow import hashed
from tests.test_authenticated_handoff import AuthenticatedHandoffTests

OUTPUT = ROOT / "artifacts/authenticated-handoff-work/scenarios"
NAMES = [
    "test_end_to_end_review_improvement_rejection_pivot_restart",
    "test_production_empty_trust_persists_precise_pending",
    "test_advisory_is_never_signed_or_promoted",
    "test_assignment_forgery_and_widened_scope_denied",
    "test_forged_decision_and_identity_denied",
    "test_authenticated_rejection_stops_before_assignment",
    "test_crash_after_commit_replays_exact_assignment",
    "test_budget_exhaustion_and_worker_signature_denial",
    "test_archived_signature_tampering_denied",
]


def main():
    OUTPUT.mkdir(mode=0o700, exist_ok=True)
    OUTPUT.chmod(0o700)
    logs, private, current = [], [], {}
    original_dispatch = ControlPlane.dispatch
    original_advance = AuthenticatedHandoff.advance
    original_init = AuthenticatedHandoff.__init__

    def initialize(self, state, actors):
        original_init(self, state, actors)
        private.append(dict(kind="public_pins", actors={
            actor: dict(role=role, public_key=key.hex()) for actor, (role, key) in actors.items()}))

    def dispatch(self, request):
        event = dict(kind="dispatch", operation=request["operation"], request_sha256=hashed(request))
        command = request.get("body", {}).get("command")
        if command:
            event.update(action=command["action"], role=command["role"], version=command["version"])
        try:
            result = original_dispatch(self, request)
            snapshot = result["snapshot"]
            event.update(outcome="RECORDED", state=snapshot.get("state"),
                         snapshot_sha256=hashed(snapshot))
            private.append(dict(request=deepcopy(request), result=deepcopy(result)))
            return result
        except Exception as exc:
            event.update(outcome="DENIED", error_class=type(exc).__name__)
            private.append(dict(request=deepcopy(request), error_class=type(exc).__name__))
            raise
        finally:
            current["events"].append(event)

    def advance(self, source, authorization=None):
        event = dict(kind="handoff", source_sha256=hashed(source),
                     authorization_sha256=hashed(authorization))
        try:
            result = original_advance(self, source, authorization)
            event.update(outcome=result["status"], reason=result["reason"],
                         manager_assignment=result["manager_assignment"], state=result.get("state"))
            return result
        except Exception as exc:
            event.update(outcome="DENIED", error_class=type(exc).__name__)
            raise
        finally:
            current["events"].append(event)

    class EvidenceResult(unittest.TextTestResult):
        def startTest(self, test):
            super().startTest(test)
            current.clear()
            current.update(scenario=test.id(), events=[])
            private.clear()

        def stopTest(self, test):
            failed = any(t is test for t, _ in self.failures + self.errors)
            current["result"] = "FAIL" if failed else "PASS"
            name = test._testMethodName
            raw_path = OUTPUT / (name + ".private.json")
            write_json(raw_path, dict(scenario=test.id(), records=deepcopy(private)))
            current["private_evidence_sha256"] = digest(raw_path.read_bytes())
            logs.append(deepcopy(current))
            super().stopTest(test)

    suite = unittest.TestSuite(AuthenticatedHandoffTests(name) for name in NAMES)
    with patch.object(ControlPlane, "dispatch", dispatch), patch.object(
            AuthenticatedHandoff, "advance", advance), patch.object(
            AuthenticatedHandoff, "__init__", initialize):
        result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    write_json(OUTPUT / "decision-log.json", dict(
        execution_class="EPHEMERAL_SYNTHETIC_KEYS_NO_PROVIDER_NO_OWNER",
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        scenarios=logs, independent_acceptance=False, adv_denominator=49))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

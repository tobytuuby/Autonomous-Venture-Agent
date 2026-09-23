import copy
import unittest

from kernel.p6.registry import LIVE_FIELDS, canonical, digest
from kernel.p7.worker_boundary import (
    SyntheticWorkerBoundary,
    WorkerBoundaryError,
)


POLICY = "p7.5"
CONFIG = digest(canonical({"phase": "p7.5", "fixture": "worker-boundary"}))
ENVIRONMENT = "synthetic-worker-boundary"
SOURCE_HASH = digest("synthetic-source")
SOURCE_HASH_2 = digest("synthetic-source-2")

AUTHORITIES = (
    "network",
    "broker",
    "payment",
    "credential",
    "deployment",
    "customer",
    "capital",
    "venture",
    "worker",
)
STATES = (
    "request",
    "approval",
    "dispatch",
    "response",
    "reconciliation",
    "failure",
    "freeze",
    "revoke",
    "quarantine-wind-down",
)


def provenance(source_hash=SOURCE_HASH):
    return {
        "source_ids": ["synthetic-thesis"],
        "source_hashes": [source_hash],
        "lineage": ["p7.0", "p7.5"],
    }


def boundary():
    return SyntheticWorkerBoundary(
        policy_version=POLICY,
        configuration_fingerprint=CONFIG,
        environment_identity=ENVIRONMENT,
    )


def admission(worker_id="worker-a", venture_id="venture-a", **extra):
    request = {
        "worker_id": worker_id,
        "manager_id": "manager-a",
        "venture_id": venture_id,
        "portfolio_id": "portfolio-a",
        "archetype_id": "research-shadow",
        "task_classes": ["synthetic-research"],
        "capabilities": ["read-synthetic-evidence"],
        "originating_capabilities": ["read-synthetic-evidence", "record-synthetic-result"],
        "policy_version": POLICY,
        "configuration_fingerprint": CONFIG,
        "environment_identity": ENVIRONMENT,
        "provenance": provenance(),
        "correlation_id": "corr-" + worker_id,
        "idempotency_key": "idem-" + worker_id,
        "actor": {"actor_id": "manager-a", "role": "venture-manager-shadow"},
        "synthetic_only": True,
        "effect": "none",
        **{field: False for field in LIVE_FIELDS},
    }
    request.update(extra)
    return request


def task(worker_id="worker-a", venture_id="venture-a", **extra):
    record = {
        "task_id": "task-" + worker_id,
        "worker_id": worker_id,
        "venture_id": venture_id,
        "capabilities": ["read-synthetic-evidence"],
        "provenance": provenance(),
        "idempotency_key": "task-idem-" + worker_id,
        "synthetic_only": True,
        "effect": "none",
        **{field: False for field in LIVE_FIELDS},
    }
    record.update(extra)
    return record


AUTHORITY_CASES = tuple(
    f"P7.5.AUTHORITY.{authority}.{state}"
    for authority in AUTHORITIES
    for state in STATES
)
RECOVERY_CASES = tuple(
    f"P7.5.RECOVERY.{control}.{mode}"
    for control in ("freeze", "revoke", "quarantine", "restore", "rollback", "wind-down")
    for mode in ("normal", "injected-failure")
)


class TestP75WorkerBoundary(unittest.TestCase):
    def test_authority_matrix_81_cases(self):
        fixture = boundary()
        self.assertEqual(len(AUTHORITY_CASES), 81)
        for case_id, authority, state in zip(
            AUTHORITY_CASES,
            (authority for authority in AUTHORITIES for _ in STATES),
            (state for _ in AUTHORITIES for state in STATES),
        ):
            with self.subTest(case_id=case_id):
                result = fixture.authority_case(
                    authority=authority,
                    state=state,
                    request={"synthetic_only": True, "effect": "none"},
                )
                self.assertEqual(result["decision"], "DENY")
                self.assertEqual(result["status"], "CONTAINED")
                self.assertTrue(result["synthetic_only"])
                self.assertEqual(result["effect"], "none")
                self.assertEqual(
                    {field: result[field] for field in LIVE_FIELDS},
                    {field: False for field in LIVE_FIELDS},
                )
        self.assertEqual(len(fixture.authorities()), 9)
        self.assertTrue(all(value is False for value in fixture.authorities().values()))

    def test_recovery_matrix_12_cases(self):
        self.assertEqual(len(RECOVERY_CASES), 12)
        for control, mode in (
            (control, mode)
            for control in ("freeze", "revoke", "quarantine", "restore", "rollback", "wind-down")
            for mode in ("normal", "injected-failure")
        ):
            case_id = f"P7.5.RECOVERY.{control}.{mode}"
            with self.subTest(case_id=case_id):
                fixture = boundary()
                if control == "restore":
                    fixture.admit_worker(admission())
                    snapshot = fixture.snapshot()
                    target = boundary()
                    if mode == "normal":
                        result = target.restore(snapshot)
                        self.assertEqual(result["status"], "RESTORED")
                        self.assertEqual(target.authorities(), {field: False for field in LIVE_FIELDS})
                    else:
                        target.inject_failure("recovery")
                        with self.assertRaises(WorkerBoundaryError):
                            target.restore(snapshot)
                        self.assertTrue(target.fail_closed)
                    continue

                fixture.admit_worker(admission())
                if mode == "injected-failure":
                    fixture.inject_failure("revocation" if control == "revoke" else "recovery")
                    with self.assertRaises(WorkerBoundaryError):
                        getattr(fixture, control.replace("-", "_"))("worker-a")
                    self.assertTrue(fixture.fail_closed)
                    continue

                result = getattr(fixture, control.replace("-", "_"))("worker-a")
                self.assertEqual(result["state"], {
                    "freeze": "FROZEN",
                    "revoke": "REVOKED",
                    "quarantine": "QUARANTINED",
                    "rollback": "WOUND_DOWN",
                    "wind-down": "WOUND_DOWN",
                }[control])
                with self.assertRaises(WorkerBoundaryError):
                    fixture.record_task(task())

    def test_admission_identity_capability_and_provenance_denials(self):
        cases = [
            ("policy", {"policy_version": "wrong"}),
            ("configuration", {"configuration_fingerprint": digest("wrong")}),
            ("environment", {"environment_identity": "live"}),
            ("self-admission", {"actor": {"actor_id": "worker-a", "role": "worker-shadow"}}),
            ("capability-widening", {"capabilities": ["write-live-system"]}),
            ("model-approval", {"model_output": "approve"}),
            ("missing-provenance", {"provenance": {}}),
            ("live-authority", {"live_mode": True}),
        ]
        for name, mutation in cases:
            with self.subTest(case=name):
                fixture = boundary()
                request = admission()
                request.update(mutation)
                with self.assertRaises(WorkerBoundaryError):
                    fixture.admit_worker(request)
                self.assertEqual(fixture.authorities(), {field: False for field in LIVE_FIELDS})
                self.assertEqual(fixture.quarantine_records(), [] if name != "live-authority" else [])

    def test_task_identity_scope_replay_and_revocation_denials(self):
        fixture = boundary()
        fixture.admit_worker(admission())
        recorded = fixture.record_task(task())
        duplicate = fixture.record_task(task())
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(recorded["record_hash"], duplicate["record_hash"])

        with self.assertRaises(WorkerBoundaryError):
            fixture.record_task(task(venture_id="venture-b"))
        changed = task()
        changed["capabilities"] = ["record-synthetic-result"]
        with self.assertRaises(WorkerBoundaryError):
            fixture.record_task(changed)

        fixture.revoke("worker-a")
        with self.assertRaises(WorkerBoundaryError):
            fixture.record_task(task(task_id="task-after-revoke"))
        with self.assertRaises(WorkerBoundaryError):
            fixture.rollback("worker-a")
        self.assertEqual(fixture.authorities(), {field: False for field in LIVE_FIELDS})


if __name__ == "__main__":
    unittest.main()

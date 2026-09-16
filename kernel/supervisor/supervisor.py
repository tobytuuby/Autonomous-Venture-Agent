"""Durable-job and generic recovery mechanisms for P0.7."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


def utcnow():
    return datetime.now(timezone.utc)


class JobQueue:
    def __init__(self):
        self.jobs = {}
        self.effects = set()

    def enqueue(self, job_id: str, idempotency_key: str, payload: dict[str, Any]):
        for job in self.jobs.values():
            if job["idempotency_key"] == idempotency_key:
                return job
        job = {"job_id": job_id, "idempotency_key": idempotency_key, "payload": payload,
               "status": "queued", "claimed_by": None, "attempts": 0}
        self.jobs[job_id] = job
        return job

    def claim(self, worker_id: str):
        for job in self.jobs.values():
            if job["status"] == "queued":
                job.update(status="claimed", claimed_by=worker_id, claimed_at=utcnow())
                job["attempts"] += 1
                return job
        return None

    def reclaim_stale(self, max_age: timedelta) -> int:
        count = 0
        for job in self.jobs.values():
            if job["status"] == "claimed" and utcnow() - job["claimed_at"] > max_age:
                job.update(status="queued", claimed_by=None, claimed_at=None)
                count += 1
        return count

    def complete_once(self, job_id: str, effect: Callable[[], None]) -> bool:
        job = self.jobs[job_id]
        if job["status"] == "completed":
            return False
        key = job["idempotency_key"]
        if key not in self.effects:
            effect()
            self.effects.add(key)
        job.update(status="completed", completed_at=utcnow())
        return True


@dataclass
class SupervisorState:
    status: str = "HEALTHY"
    repair_attempts: int = 0
    max_repair_attempts: int = 3
    fingerprint_quarantines: int = 0
    quarantined: bool = False


class Supervisor:
    def __init__(self, state=None, policy_check: Callable[[dict[str, Any]], bool] | None = None):
        self.state = state or SupervisorState()
        self.policy_check = policy_check or (lambda _: True)

    def signal(self, *, heartbeat_stale=False, error_rate=0, guardrail_trip=False) -> str:
        if self.state.quarantined:
            return "QUARANTINE"
        if heartbeat_stale or error_rate > 0.25 or guardrail_trip:
            self.state.status = "DEGRADED"
        return self.state.status

    def repair(self, operation: str, preincident_grant: dict[str, Any], requested_changes=None) -> str:
        if operation not in {"restart", "restore", "reprovision", "quarantine"}:
            raise ValueError("invalid repair operation")
        if requested_changes:
            raise ValueError("repair cannot change policy, manifest, prompt, capability, cost, or network")
        if not self.policy_check({"grant": preincident_grant, "operation": operation}):
            raise PermissionError("pre-incident grant is not allowed by current policy")
        self.state.repair_attempts += 1
        if operation == "quarantine" or self.state.repair_attempts > self.state.max_repair_attempts:
            self.state.quarantined = True
            self.state.status = "QUARANTINE"
            return self.state.status
        self.state.status = {"restart": "RESTART", "restore": "RESTORE", "reprovision": "REPROVISION"}[operation]
        return self.state.status

    def repeated_fingerprint_quarantine(self) -> str:
        self.state.fingerprint_quarantines += 1
        if self.state.fingerprint_quarantines >= 2:
            self.state.quarantined = True
            self.state.status = "QUARANTINE"
        return self.state.status

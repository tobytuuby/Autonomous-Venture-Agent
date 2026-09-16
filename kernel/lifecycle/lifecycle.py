"""P0.14 synthetic lifecycle fixtures; no venture-intelligence reasoning agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any


class LifecycleDenied(PermissionError):
    pass


@dataclass(frozen=True)
class RoleIdentity:
    identity_id: str
    role: str
    venture_id: str | None
    capabilities: frozenset[str]


@dataclass
class Venture:
    venture_id: str
    thesis_id: str
    tokens: set[str] = field(default_factory=set)
    obligations: set[str] = field(default_factory=set)
    reconciled: bool = True
    archived: bool = False


@dataclass(frozen=True)
class WorkerArchetype:
    name: str
    capabilities: frozenset[str]
    ttl_seconds: int


class LifecycleKernel:
    def __init__(self, max_spawn_depth: int = 2, max_ventures: int = 2):
        self.max_spawn_depth = max_spawn_depth
        self.max_ventures = max_ventures
        self.ventures: dict[str, Venture] = {}
        self.roles: dict[str, RoleIdentity] = {}
        self.spawned: dict[str, tuple[str, int]] = {}
        self.cooldowns: dict[str, datetime] = {}
        self.repair_requests: list[tuple[str, str]] = []
        self.workers: dict[str, tuple[WorkerArchetype, datetime, str]] = {}
        self.shared_services: dict[str, set[str]] = {}
        self.shared_context: dict[str, dict[str, Any]] = {}
        self.quarantined_shared: set[str] = set()
        self.archetypes = {
            "research": WorkerArchetype("research", frozenset({"research.read", "evidence.submit"}), 300),
            "builder": WorkerArchetype("builder", frozenset({"sandbox.write", "artifact.submit"}), 300),
        }

    def bind_role(self, identity_id: str, role: str, venture_id: str | None, capabilities: set[str]) -> RoleIdentity:
        if role not in {"portfolio-ceo", "venture-manager"}:
            raise LifecycleDenied("only synthetic CEO/VM role identities are permitted")
        identity = RoleIdentity(identity_id, role, venture_id, frozenset(capabilities))
        self.roles[identity_id] = identity
        return identity

    def _role(self, identity_id: str, role: str) -> RoleIdentity:
        identity = self.roles.get(identity_id)
        if not identity or identity.role != role:
            raise LifecycleDenied("role-bound identity required")
        return identity

    @staticmethod
    def thesis_fingerprint(category: str, segment: str, offer: str, channel: str) -> str:
        return sha256("|".join((category, segment, offer, channel)).encode()).hexdigest()

    def provision(self, identity_id: str, venture_id: str, thesis_id: str) -> Venture:
        self._role(identity_id, "portfolio-ceo")
        if len(self.ventures) >= self.max_ventures:
            raise LifecycleDenied("venture ceiling reached")
        cooldown = self.cooldowns.get(thesis_id)
        if cooldown and datetime.now(timezone.utc) < cooldown:
            raise LifecycleDenied("thesis cooldown active")
        if venture_id in self.ventures:
            raise LifecycleDenied("venture id already exists")
        venture = Venture(venture_id, thesis_id)
        self.ventures[venture_id] = venture
        return venture

    def grant_token(self, identity_id: str, venture_id: str, token_id: str) -> None:
        identity = self._role(identity_id, "portfolio-ceo")
        if identity.venture_id not in (None, venture_id) or venture_id not in self.ventures:
            raise LifecycleDenied("venture scope mismatch")
        self.ventures[venture_id].tokens.add(token_id)

    def read_venture(self, identity_id: str, venture_id: str) -> Venture:
        identity = self.roles.get(identity_id)
        if not identity or identity.venture_id != venture_id:
            raise LifecycleDenied("venture isolation denied")
        return self.ventures[venture_id]

    def spawn(self, identity_id: str, child_id: str, depth: int, kind: str) -> None:
        identity = self.roles.get(identity_id)
        if not identity or kind != "worker" or identity.role != "venture-manager":
            raise LifecycleDenied("spawn tier denied")
        if depth > self.max_spawn_depth:
            raise LifecycleDenied("spawn depth exceeded")
        self.spawned[child_id] = (identity_id, depth)

    def request_capital(self, identity_id: str) -> None:
        if self.roles.get(identity_id, RoleIdentity("", "", None, frozenset())).role != "portfolio-ceo":
            raise LifecycleDenied("portfolio capital requires the CEO role")

    def corrective_attempt(self, identity_id: str, venture_id: str, validation_score: float) -> None:
        self._role(identity_id, "portfolio-ceo")
        venture = self.ventures[venture_id]
        if not venture.reconciled or validation_score < 0.8:
            raise LifecycleDenied("corrective attempt verification failed")

    def wind_down(self, identity_id: str, venture_id: str, thesis_id: str, cooldown_seconds: int = 3600) -> None:
        self._role(identity_id, "portfolio-ceo")
        venture = self.ventures[venture_id]
        if venture.tokens or venture.obligations:
            raise LifecycleDenied("live tokens or obligations remain")
        venture.archived = True
        self.cooldowns[thesis_id] = datetime.now(timezone.utc) + timedelta(seconds=cooldown_seconds)

    def repair_request(self, requester_id: str, target_id: str) -> None:
        requester = self._role(requester_id, "portfolio-ceo")
        target = self._role(target_id, "venture-manager")
        if target.venture_id not in self.ventures or self.ventures[target.venture_id].archived:
            raise LifecycleDenied("repair requires an active parent relationship")
        self.repair_requests.append((requester.identity_id, target.identity_id))

    def spawn_worker(self, manager_id: str, worker_id: str, archetype: str, requested: set[str], now: datetime | None = None) -> WorkerArchetype:
        manager = self._role(manager_id, "venture-manager")
        definition = self.archetypes.get(archetype)
        if not definition:
            raise LifecycleDenied("unknown worker archetype")
        if not requested.issubset(definition.capabilities):
            raise LifecycleDenied("requested worker capability exceeds fixed envelope")
        self.workers[worker_id] = (definition, (now or datetime.now(timezone.utc)) + timedelta(seconds=definition.ttl_seconds), manager.venture_id or "")
        return definition

    def reap_workers(self, now: datetime | None = None) -> list[str]:
        current = now or datetime.now(timezone.utc)
        expired = [worker_id for worker_id, (_, expires, _) in self.workers.items() if expires <= current]
        for worker_id in expired:
            del self.workers[worker_id]
        return expired

    def request_shared_service(self, ceo_id: str, service_id: str, venture_ids: set[str]) -> None:
        self._role(ceo_id, "portfolio-ceo")
        if len(venture_ids) < 2 or not venture_ids.issubset(self.ventures):
            raise LifecycleDenied("independent demand evidence is insufficient")
        self.shared_services[service_id] = set(venture_ids)

    def task_packet(self, service_id: str, venture_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if service_id in self.quarantined_shared or venture_id not in self.shared_services.get(service_id, set()):
            raise LifecycleDenied("shared service unavailable or venture not admitted")
        self.shared_context[service_id] = {"venture_id": venture_id, "payload": dict(payload)}
        result = {"accepted": True, "venture_id": venture_id}
        self.shared_context.pop(service_id, None)
        return result

    def promote_finding(self, service_id: str, contributing_ventures: set[str]) -> None:
        admitted = self.shared_services.get(service_id, set())
        if len(contributing_ventures) < 2 or not contributing_ventures.issubset(admitted):
            raise LifecycleDenied("portfolio knowledge requires multi-venture evidence")

    def shared_signal(self, manager_id: str, service_id: str) -> dict[str, Any]:
        manager = self._role(manager_id, "venture-manager")
        if service_id not in self.shared_services:
            raise LifecycleDenied("shared service is not registered")
        return {"service_id": service_id, "available": True, "venture_id": manager.venture_id}

    def durable_state(self) -> dict[str, Any]:
        return {"ventures": {key: {"venture_id": value.venture_id, "thesis_id": value.thesis_id, "tokens": sorted(value.tokens), "obligations": sorted(value.obligations), "reconciled": value.reconciled, "archived": value.archived} for key, value in self.ventures.items()}}

    def restore_durable_state(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict) or not isinstance(state.get("ventures"), dict):
            raise LifecycleDenied("durable portfolio state is invalid")
        restored = {}
        for venture_id, value in state["ventures"].items():
            if value.get("venture_id") != venture_id or not isinstance(value.get("thesis_id"), str):
                raise LifecycleDenied("durable portfolio state failed integrity checks")
            restored[venture_id] = Venture(venture_id, value["thesis_id"], set(value.get("tokens", [])), set(value.get("obligations", [])), bool(value.get("reconciled", True)), bool(value.get("archived", False)))
        self.ventures = restored

    def quarantine_shared(self, service_id: str) -> None:
        self.quarantined_shared.add(service_id)

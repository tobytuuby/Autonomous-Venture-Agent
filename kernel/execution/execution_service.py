"""Broker-approved execution without exposing raw credentials to agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol


class ExecutionDenied(PermissionError):
    """Raised when the internal execution boundary is not satisfied."""


@dataclass(frozen=True)
class Lease:
    value: str
    lease_id: str
    expires_at: datetime

    def valid(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return current < self.expires_at


class LeaseProvider(Protocol):
    def issue(self, service: str) -> Lease: ...


@dataclass(frozen=True)
class ExecutionResult:
    request_id: str
    status: str
    provider_ref: str | None
    data: dict[str, Any]

    def as_agent_result(self) -> dict[str, Any]:
        # Deliberately no lease, token, secret, or provider credential is returned.
        return {
            "request_id": self.request_id,
            "status": self.status,
            "provider_ref": self.provider_ref,
            "data": self.data,
        }


class ExecutionService:
    """Internal-only adapter: broker approval -> leased secret -> external call."""

    def __init__(self, lease_provider: LeaseProvider, adapters: dict[str, Callable[[str, dict[str, Any]], ExecutionResult]]):
        self._lease_provider = lease_provider
        self._adapters = adapters

    def execute(self, *, request_id: str, service: str, payload: dict[str, Any], broker_approved: bool, caller: str) -> ExecutionResult:
        if caller.startswith("agent:"):
            raise ExecutionDenied("execution service is not exposed to agent identities")
        if not broker_approved:
            raise ExecutionDenied("broker approval is required")
        adapter = self._adapters.get(service)
        if adapter is None:
            raise ExecutionDenied("service is not allow-listed")
        lease = self._lease_provider.issue(service)
        if not lease.valid():
            raise ExecutionDenied("leased credential is expired")
        # The value exists only in this call frame and is never part of the result.
        result = adapter(lease.value, payload)
        if not isinstance(result, ExecutionResult) or result.request_id != request_id:
            raise ExecutionDenied("adapter returned an invalid result envelope")
        return result

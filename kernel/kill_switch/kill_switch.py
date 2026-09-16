"""Human-only soft/hard stop controls and irreversible-action latency gate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol


class Revocable(Protocol):
    def revoke(self, lease_id: str) -> None: ...


class SoftStop(RuntimeError):
    pass


class HardStop(RuntimeError):
    pass


@dataclass
class PendingAction:
    action_id: str
    execute_at: datetime
    callback: Callable[[], object]
    intercepted: bool = False


class IrreversibleActionGate:
    def __init__(self, delay_seconds: int = 30):
        self.delay = timedelta(seconds=delay_seconds)
        self.pending: dict[str, PendingAction] = {}
        self.hard_stopped = False

    def schedule(self, action_id: str, callback: Callable[[], object], now: datetime | None = None) -> PendingAction:
        if self.hard_stopped:
            raise HardStop("hard stop is active")
        item = PendingAction(action_id, (now or datetime.now(timezone.utc)) + self.delay, callback)
        self.pending[action_id] = item
        return item

    def fire(self, action_id: str, now: datetime | None = None) -> object:
        item = self.pending[action_id]
        if self.hard_stopped or item.intercepted:
            raise HardStop("action intercepted by hard stop")
        if (now or datetime.now(timezone.utc)) < item.execute_at:
            raise SoftStop("irreversible action is still inside its latency window")
        del self.pending[action_id]
        return item.callback()

    def intercept(self) -> None:
        self.hard_stopped = True
        for item in self.pending.values():
            item.intercepted = True


class KillSwitch:
    """Only an explicitly human-labelled caller may trigger these controls."""

    def __init__(self, gate: IrreversibleActionGate | None = None):
        self.gate = gate or IrreversibleActionGate()
        self.soft_stopped = False
        self.hard_stopped = False

    def _human(self, caller: str) -> None:
        if not caller.startswith("human:"):
            raise PermissionError("kill switch is human-operator-only")

    def soft_stop(self, caller: str) -> None:
        self._human(caller)
        self.soft_stopped = True

    def hard_stop(self, caller: str, leases: list[tuple[Revocable, str]] = ()) -> None:
        self._human(caller)
        self.hard_stopped = True
        self.soft_stopped = True
        self.gate.intercept()
        for integration, lease_id in leases:
            integration.revoke(lease_id)

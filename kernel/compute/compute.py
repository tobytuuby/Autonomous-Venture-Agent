"""Real-time multi-level compute budget enforcement for P0.8."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Iterable


@dataclass(frozen=True)
class ComputeRequest:
    agent_id: str
    venture_id: str
    experiment_id: str
    model_id: str
    cost_units: float
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class _Window:
    limit: float
    used: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration: timedelta = timedelta(hours=1)

    def available(self, amount, at):
        if at - self.started_at >= self.duration:
            return self.limit >= amount
        return self.limit - self.used >= amount

    def debit(self, amount, at):
        if at - self.started_at >= self.duration:
            self.used, self.started_at = 0.0, at
        self.used += amount


class ComputeGovernor:
    LEVELS = ("agent", "venture", "experiment", "model", "hour", "day", "global")

    def __init__(self, limits: dict[str, float]):
        missing = set(self.LEVELS) - set(limits)
        if missing or any(value <= 0 for value in limits.values()):
            raise ValueError("positive limits are required for every compute level")
        self.limits = dict(limits)
        self.windows = {}
        self.lock = Lock()

    def _keyed_windows(self, request: ComputeRequest):
        keys = {
            "agent": request.agent_id, "venture": request.venture_id,
            "experiment": request.experiment_id, "model": request.model_id,
            "hour": "global-hour", "day": "global-day", "global": "global",
        }
        durations = {"hour": timedelta(hours=1), "day": timedelta(days=1),
                     "global": timedelta(days=36500)}
        for level in self.LEVELS:
            key = (level, keys[level])
            if key not in self.windows:
                self.windows[key] = _Window(self.limits[level], duration=durations.get(level, timedelta(hours=1)))
            yield self.windows[key]

    def admit(self, request: ComputeRequest) -> bool:
        if request.cost_units <= 0:
            return False
        with self.lock:
            windows = list(self._keyed_windows(request))
            if not all(window.available(request.cost_units, request.requested_at) for window in windows):
                return False
            for window in windows:
                window.debit(request.cost_units, request.requested_at)
            return True

    def remaining(self, level: str, key: str = "global") -> float:
        with self.lock:
            window = self.windows.get((level, key))
            return self.limits[level] if window is None else max(0.0, window.limit - window.used)

"""Platform manifest and guardrail breaker controls for P0.10."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import secrets


@dataclass(frozen=True)
class Manifest:
    channel: str
    source: str
    policy_version: str
    verified_at: datetime
    expires_at: datetime
    permitted_actions: frozenset[str]
    prohibited_actions: frozenset[str]

    def permits(self, action: str, at: datetime | None = None) -> bool:
        at = at or datetime.now(timezone.utc)
        return at < self.expires_at and action in self.permitted_actions and action not in self.prohibited_actions


@dataclass
class Breaker:
    reset_class: str
    state: str = "CLOSED"
    clean_events: int = 0
    progressive_level: int = 0

    def __post_init__(self):
        if self.reset_class not in {"latching", "cooldown", "progressive"}:
            raise ValueError("invalid breaker reset class")

    def trip(self):
        self.state = "OPEN"
        self.clean_events = 0
        self.progressive_level += 1

    def observe_clean(self):
        if self.state != "OPEN":
            return self.state
        if self.reset_class == "latching":
            return self.state
        self.clean_events += 1
        required = 2 if self.reset_class == "cooldown" else 3
        if self.clean_events >= required:
            self.state = "HALF_OPEN" if self.reset_class == "progressive" else "CLOSED"
        return self.state

    def reset(self, human_operator: bool = False):
        if self.reset_class == "latching" and not human_operator:
            raise PermissionError("latching breaker requires human reset")
        self.state = "CLOSED"
        self.clean_events = 0
        return self.state


@dataclass
class AuditSampler:
    population: tuple[str, ...]
    samples: list[tuple[str, ...]] = field(default_factory=list)

    def sample(self, size: int) -> tuple[str, ...]:
        if size <= 0 or size > len(self.population):
            raise ValueError("invalid sample size")
        selected = tuple(secrets.SystemRandom().sample(self.population, size))
        self.samples.append(selected)
        return selected

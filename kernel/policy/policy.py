"""Versioned policy-exception boundary."""
from __future__ import annotations
from datetime import datetime, timezone
class PolicyExceptionDenied(PermissionError): pass
class TemporaryPolicyGuard:
    def request(self, actor_role: str, reason: str, expires_at: datetime | None = None) -> None:
        if actor_role != "human-operator":
            raise PolicyExceptionDenied("temporary policy exceptions require a human operator")
        if not reason or expires_at is None or expires_at <= datetime.now(timezone.utc):
            raise PolicyExceptionDenied("policy exception must be justified and time-bounded")
        raise PolicyExceptionDenied("temporary exceptions require an independently versioned policy change")

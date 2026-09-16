"""Fail-closed capability broker for P0.5.

The state object is deliberately injectable so the eleven CAP checks can be tested
without granting the test process ambient credentials. Production persistence is
provided by the authoritative database integration in a later increment.
"""
from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class BrokerState:
    requests: list[dict[str, Any]] = field(default_factory=list)
    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    revoked: set[str] = field(default_factory=set)
    known_capabilities: set[tuple[str, str]] = field(default_factory=set)
    baselines: dict[tuple[str, str], float] = field(default_factory=dict)

    def record(self, request: dict[str, Any], grant: dict[str, Any] | None) -> None:
        self.requests.append(request)
        if grant:
            self.grants[grant["grant_id"]] = grant
            self.known_capabilities.add((request["agent_id"], request["capability"]))


class OPAClient:
    def __init__(self, url: str = "http://127.0.0.1:8181/v1/data/venture/capability/allow", timeout: float = 1.5):
        self.url, self.timeout = url, timeout

    def __call__(self, policy_input: dict[str, Any]) -> bool:
        body = json.dumps({"input": policy_input}).encode()
        request = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
            return result.get("result") is True
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return False


class Broker:
    FORBIDDEN_GRAPH = (
        "create_file", "upload", "generate_public_link", "send_message"
    )

    def __init__(
        self,
        state: BrokerState | None = None,
        policy_evaluator: Callable[[dict[str, Any]], bool] | None = None,
        *,
        velocity_limit: int = 3,
        aggregate_limit: float = 1000.0,
        structuring_threshold: float = 1000.0,
        single_action_limit: float = 500.0,
        max_ttl_seconds: int = 3600,
    ):
        self.state = state or BrokerState()
        self.policy_evaluator = policy_evaluator or OPAClient()
        self.velocity_limit = velocity_limit
        self.aggregate_limit = aggregate_limit
        self.structuring_threshold = structuring_threshold
        self.single_action_limit = single_action_limit
        self.max_ttl_seconds = max_ttl_seconds

    def _hard(self, reasons: list[str], code: str, condition: bool) -> None:
        if condition:
            reasons.append(code)

    def _recent(self, request: dict[str, Any], window: timedelta) -> list[dict[str, Any]]:
        cutoff = parse_time(request["requested_at"]) - window
        return [
            item for item in self.state.requests
            if item.get("agent_id") == request["agent_id"]
            and parse_time(item["requested_at"]) >= cutoff
        ]

    def check_cap_001(self, request: dict[str, Any]) -> str | None:
        forbidden = {"password", "secret", "private_key", "credential", "access_token"}
        present = forbidden.intersection(request.keys()) | forbidden.intersection(request.get("requested_constraints", {}).keys())
        return "CAP-001 ambient credential material present" if present else None

    def check_cap_002(self, request: dict[str, Any]) -> str | None:
        hits = [x for x in self._recent(request, timedelta(hours=1)) if x.get("capability") == request["capability"]]
        return "CAP-002 per-agent capability velocity exceeded" if len(hits) >= self.velocity_limit else None

    def check_cap_003(self, request: dict[str, Any]) -> str | None:
        items = self._recent(request, timedelta(hours=24)) + [request]
        total = sum(float(a.get("amount", 0)) for item in items for a in item.get("action_graph", []))
        return "CAP-003 rolling aggregate across counterparties exceeded" if total > self.aggregate_limit else None

    def check_cap_004(self, request: dict[str, Any]) -> str | None:
        items = self._recent(request, timedelta(hours=24)) + [request]
        amounts = [float(a.get("amount", 0)) for item in items for a in item.get("action_graph", [])]
        return "CAP-004 structuring threshold crossed by individually-compliant actions" if (
            len(amounts) >= 2 and max(amounts) < self.single_action_limit and sum(amounts) > self.structuring_threshold
        ) else None

    def check_cap_005(self, request: dict[str, Any]) -> str | None:
        spend = any(a.get("action") in {"spend", "transfer", "purchase"} for a in request.get("action_graph", []))
        missing = spend and any(not a.get("counterparty_key") for a in request.get("action_graph", []))
        return "CAP-005 ultimate-beneficiary counterparty key required" if missing else None

    def check_cap_006(self, request: dict[str, Any]) -> str | None:
        return "CAP-006 unprecedented capability is novel" if (
            request["agent_id"], request["capability"]
        ) not in self.state.known_capabilities else None

    def check_cap_007(self, request: dict[str, Any]) -> str | None:
        amounts = [float(a.get("amount", 0)) for a in request.get("action_graph", [])]
        baseline = self.state.baselines.get((request["agent_id"], request["capability"]))
        return "CAP-007 behavioral baseline deviation requires step-up" if (
            baseline is not None and amounts and max(amounts) > baseline * 2
        ) else None

    def check_cap_008(self, request: dict[str, Any]) -> str | None:
        soft = {self.check_cap_006(request), self.check_cap_007(request)}
        return "CAP-008 anomaly or high novelty escalates" if any(soft) else None

    def check_cap_009(self, request: dict[str, Any]) -> str | None:
        actions = [a.get("action") for item in self._recent(request, timedelta(hours=24)) + [request]
                  for a in item.get("action_graph", [])]
        for action in self.FORBIDDEN_GRAPH:
            if action not in actions:
                return None
        return "CAP-009 forbidden composite action graph detected"

    def check_cap_010(self, request: dict[str, Any]) -> str | None:
        constraints = request.get("requested_constraints", {})
        return "CAP-010 delegation beyond policy denied" if (
            request.get("delegated_from") is not None
            or constraints.get("delegated_from") is not None
            or constraints.get("delegable") is True
        ) else None

    def check_cap_011(self, request: dict[str, Any]) -> str | None:
        ttl = request.get("requested_constraints", {}).get("ttl_seconds")
        return "CAP-011 token must be bounded and reissued per request" if (
            not isinstance(ttl, int) or ttl <= 0 or ttl > self.max_ttl_seconds
        ) else None

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        decision_id = secrets.token_hex(16)
        reasons: list[str] = []
        hard_checks = (
            self.check_cap_001, self.check_cap_002, self.check_cap_003,
            self.check_cap_004, self.check_cap_005, self.check_cap_009,
            self.check_cap_010, self.check_cap_011,
        )
        soft_checks = (self.check_cap_006, self.check_cap_007, self.check_cap_008)
        for check in hard_checks + soft_checks:
            reason = check(request)
            if reason:
                reasons.append(reason)

        ttl = request.get("requested_constraints", {}).get("ttl_seconds", 0)
        opa_input = {
            "capability": request.get("capability"),
            "policy_allowed": not any(r.startswith(("CAP-001", "CAP-002", "CAP-003", "CAP-004", "CAP-005", "CAP-009", "CAP-010", "CAP-011")) for r in reasons),
            "delegated_from": request.get("delegated_from", request.get("requested_constraints", {}).get("delegated_from")),
            "ttl_seconds": ttl,
            "max_ttl_seconds": self.max_ttl_seconds,
        }
        if not self.policy_evaluator(opa_input):
            reasons.append("OPA policy unavailable or denied")
        hard = any(r.startswith(tuple(f"CAP-{x:03d}" for x in (1,2,3,4,5,9,10,11))) or r.startswith("OPA ") for r in reasons)
        escalated = any(r.startswith("CAP-006") or r.startswith("CAP-007") or r.startswith("CAP-008") for r in reasons)
        decision = "deny" if hard else ("escalate" if escalated else "allow")
        grant = None
        if decision == "allow":
            issued = now()
            grant = {
                "grant_id": secrets.token_hex(16), "request_id": request["request_id"],
                "agent_id": request["agent_id"], "venture_id": request["venture_id"],
                "capability": request["capability"], "constraints": dict(request["requested_constraints"]),
                "issued_at": issued.isoformat().replace("+00:00", "Z"),
                "expires_at": (issued + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z"),
                "revoked_at": None, "single_use": True, "issuer": "broker",
            }
        result = {
            "decision_id": decision_id, "request_id": request["request_id"], "decision": decision,
            "reasons": reasons, "risk_score": min(100, len(reasons) * 15),
            "evaluated_at": now().isoformat().replace("+00:00", "Z"), "grant": grant,
        }
        self.state.record(request, grant)
        return result

    def revoke(self, grant_id: str) -> bool:
        grant = self.state.grants.get(grant_id)
        if not grant:
            return False
        self.state.revoked.add(grant_id)
        grant["revoked_at"] = now().isoformat().replace("+00:00", "Z")
        return True

    def consume(self, grant_id: str) -> bool:
        grant = self.state.grants.get(grant_id)
        if not grant or grant_id in self.state.revoked or not grant["single_use"]:
            return False
        if parse_time(grant["expires_at"]) <= now() or grant.get("consumed_at"):
            return False
        grant["consumed_at"] = now().isoformat().replace("+00:00", "Z")
        return True

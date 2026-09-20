"""P6.2 synthetic shared-service demand and stateless execution boundary."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .coordination import CoordinationDenied
from .registry import LIVE_FIELDS, SyntheticPortfolioRegistry, canonical, digest


class DemandDenied(CoordinationDenied):
    """Raised when a shared-service demand fails closed."""


REQUIRED_DEMAND_FIELDS = {
    "demand_id",
    "portfolio_id",
    "venture_id",
    "coordination_request_id",
    "requester_actor",
    "service_class",
    "requested_units",
    "scope",
    "eligibility",
    "quota",
    "policy_version",
    "configuration_fingerprint",
    "source_ids",
    "source_hashes",
    "lineage",
    "taint",
    "created_at",
    "expiry_at",
    "synthetic_only",
    "effect",
    "canonical_hash",
}


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise DemandDenied("INVALID_TIME", f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DemandDenied("INVALID_TIME", f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise DemandDenied("INVALID_TIME", f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _without_hash(record: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(record)
    material.pop("canonical_hash", None)
    return material


def compute_demand_hash(demand: Mapping[str, Any]) -> str:
    return digest(canonical(_without_hash(demand)))


def build_demand(
    *,
    demand_id: str,
    portfolio_id: str,
    venture_id: str,
    coordination_request_id: str,
    requester_actor: Mapping[str, Any],
    service_class: str,
    requested_units: int,
    policy_version: str,
    configuration_fingerprint: str,
    created_at: str,
    expiry_at: str,
    source_ids: list[str],
    source_hashes: list[str],
    lineage: list[str],
    taint: list[str],
    quota_max_units: int,
    scope: Mapping[str, Any] | None = None,
    eligibility: Mapping[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    demand = {
        "demand_id": demand_id,
        "portfolio_id": portfolio_id,
        "venture_id": venture_id,
        "coordination_request_id": coordination_request_id,
        "requester_actor": dict(requester_actor),
        "service_class": service_class,
        "requested_units": requested_units,
        "scope": dict(scope or {
            "portfolio_id": portfolio_id,
            "venture_id": venture_id,
        }),
        "eligibility": dict(eligibility or {"eligible": True}),
        "quota": {"max_units": quota_max_units},
        "policy_version": policy_version,
        "configuration_fingerprint": configuration_fingerprint,
        "source_ids": list(source_ids),
        "source_hashes": list(source_hashes),
        "lineage": list(lineage),
        "taint": list(taint),
        "created_at": created_at,
        "expiry_at": expiry_at,
        "synthetic_only": True,
        "effect": "none",
        **extra,
    }
    demand["canonical_hash"] = compute_demand_hash(demand)
    return demand


class SyntheticSharedServiceRunner:
    """Stateless, effect-free shared-service demand evaluator."""

    def __init__(
        self,
        registry: SyntheticPortfolioRegistry,
        *,
        policy_version: str,
        configuration_fingerprint: str,
        service_limits: Mapping[str, int],
        clock: Callable[[], datetime],
        max_clock_skew_seconds: int = 300,
    ):
        if configuration_fingerprint != registry.configuration_fingerprint:
            raise DemandDenied("FINGERPRINT_MISMATCH", "registry fingerprint mismatch")
        if not service_limits or any(
            not isinstance(key, str) or not key or not isinstance(value, int) or value <= 0
            for key, value in service_limits.items()
        ):
            raise DemandDenied("INVALID_QUOTA", "service limits must be positive integers")
        self.registry = registry
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.service_limits = dict(service_limits)
        self.clock = clock
        self.max_clock_skew_seconds = max_clock_skew_seconds

    def run(self, demand: Mapping[str, Any]) -> dict[str, Any]:
        demand_hash = self._validate(demand)
        output_material = {
            "demand_hash": demand_hash,
            "demand_id": demand["demand_id"],
            "portfolio_id": demand["portfolio_id"],
            "venture_id": demand["venture_id"],
            "coordination_request_id": demand["coordination_request_id"],
            "service_class": demand["service_class"],
            "requested_units": demand["requested_units"],
            "configuration_fingerprint": self.configuration_fingerprint,
            "policy_version": self.policy_version,
            "synthetic_only": True,
            "effect": "none",
        }
        return {
            "output_id": "synthetic-output-" + digest(canonical(output_material))[:24],
            "output_hash": digest(canonical(output_material)),
            "demand_id": demand["demand_id"],
            "portfolio_id": demand["portfolio_id"],
            "venture_id": demand["venture_id"],
            "coordination_request_id": demand["coordination_request_id"],
            "service_class": demand["service_class"],
            "requested_units": demand["requested_units"],
            "source_ids": list(demand["source_ids"]),
            "source_hashes": list(demand["source_hashes"]),
            "lineage": list(demand["lineage"]) + [demand["canonical_hash"]],
            "taint": list(demand["taint"]),
            "policy_version": self.policy_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "synthetic_only": True,
            "effect": "none",
            "stateless": True,
        }

    def _validate(self, demand: Mapping[str, Any]) -> str:
        missing = REQUIRED_DEMAND_FIELDS.difference(demand)
        if missing:
            raise DemandDenied("MISSING_FIELD", "missing fields: " + ",".join(sorted(missing)))
        if demand["synthetic_only"] is not True or demand["effect"] != "none":
            raise DemandDenied("EFFECTFUL_DEMAND", "shared-service demand is synthetic and effect-free")
        if any(bool(demand.get(field)) for field in LIVE_FIELDS):
            raise DemandDenied("LIVE_AUTHORITY", "live authority is denied")
        if demand["policy_version"] != self.policy_version:
            raise DemandDenied("POLICY_MISMATCH", "policy version mismatch")
        if demand["configuration_fingerprint"] != self.configuration_fingerprint:
            raise DemandDenied("FINGERPRINT_MISMATCH", "configuration fingerprint mismatch")
        for field in ("demand_id", "portfolio_id", "venture_id", "coordination_request_id", "service_class"):
            if not isinstance(demand[field], str) or not demand[field]:
                raise DemandDenied("INVALID_IDENTITY", f"{field} is required")
        actor = demand["requester_actor"]
        if not isinstance(actor, Mapping) or not actor.get("actor_id"):
            raise DemandDenied("INVALID_ACTOR", "requester_actor.actor_id is required")
        scope = demand["scope"]
        if not isinstance(scope, Mapping):
            raise DemandDenied("INVALID_SCOPE", "scope must be an object")
        if scope.get("portfolio_id") != demand["portfolio_id"]:
            raise DemandDenied("CROSS_PORTFOLIO", "scope portfolio does not match demand")
        if scope.get("venture_id") != demand["venture_id"]:
            raise DemandDenied("CROSS_VENTURE", "scope venture does not match demand")
        if demand["service_class"] not in self.service_limits:
            raise DemandDenied("INELIGIBLE_SERVICE", "service class is not configured")
        units = demand["requested_units"]
        if not isinstance(units, int) or isinstance(units, bool) or units <= 0:
            raise DemandDenied("INVALID_QUOTA", "requested_units must be positive")
        quota = demand["quota"]
        if not isinstance(quota, Mapping) or quota.get("max_units") != self.service_limits[demand["service_class"]]:
            raise DemandDenied("QUOTA_MISMATCH", "demand quota does not match service policy")
        if units > quota["max_units"]:
            raise DemandDenied("QUOTA_EXCEEDED", "requested units exceed service quota")
        eligibility = demand["eligibility"]
        if not isinstance(eligibility, Mapping) or eligibility.get("eligible") is not True:
            raise DemandDenied("INELIGIBLE_DEMAND", "demand is not eligible")
        if not isinstance(demand["source_ids"], list) or not demand["source_ids"]:
            raise DemandDenied("MISSING_PROVENANCE", "source_ids are required")
        if not isinstance(demand["source_hashes"], list) or not demand["source_hashes"]:
            raise DemandDenied("MISSING_PROVENANCE", "source_hashes are required")
        if len(demand["source_ids"]) != len(demand["source_hashes"]):
            raise DemandDenied("MISSING_PROVENANCE", "source ids and hashes must align")
        if not isinstance(demand["lineage"], list) or not demand["lineage"]:
            raise DemandDenied("MISSING_PROVENANCE", "lineage is required")
        if not isinstance(demand["taint"], list):
            raise DemandDenied("MISSING_PROVENANCE", "taint must be a list")
        created = _parse_time(demand["created_at"], "created_at")
        expiry = _parse_time(demand["expiry_at"], "expiry_at")
        now = self.clock().astimezone(timezone.utc)
        if created > now and (created - now).total_seconds() > self.max_clock_skew_seconds:
            raise DemandDenied("STALE_TIME", "created_at is too far in the future")
        if expiry <= now:
            raise DemandDenied("EXPIRED", "demand has expired")
        if expiry <= created:
            raise DemandDenied("INVALID_TIME", "expiry_at must follow created_at")
        expected_hash = compute_demand_hash(demand)
        if demand["canonical_hash"] != expected_hash:
            raise DemandDenied("CANONICAL_HASH", "canonical hash mismatch")
        memberships = self.registry.get_memberships(demand["portfolio_id"])
        membership = next(
            (item for item in memberships if item.get("venture_id") == demand["venture_id"]),
            None,
        )
        if membership is None:
            raise DemandDenied("CROSS_VENTURE", "venture is not in portfolio registry")
        if membership.get("venture_scope", {}).get("portfolio_id") != demand["portfolio_id"]:
            raise DemandDenied("CROSS_PORTFOLIO", "venture registry scope mismatch")
        return expected_hash

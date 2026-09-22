"""Synthetic P7.1 topology, release admission, and rollback boundary.

This module is intentionally effect-free. It models production-shaped release
controls without a provider, network, credential, deployment, or external side
effect capability.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

LIVE_AUTHORITIES = (
    "network", "broker", "payment", "credential", "deployment",
    "customer", "capital", "venture", "worker",
)
ALLOWED_EXECUTION_CLASSES = frozenset({"synthetic", "shadow", "isolated-pre-production"})


class TopologyDenied(RuntimeError):
    """Raised when topology or release admission fails closed."""


class RollbackDenied(RuntimeError):
    """Raised when a rollback cannot safely restore a known-safe release."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fingerprint(value: Any) -> str:
    return sha256(canonical(value))


def compute_topology_fingerprint(manifest: Mapping[str, Any]) -> str:
    return _fingerprint(manifest)


def validate_topology(manifest: Mapping[str, Any]) -> str:
    required = {"schema_version", "topology_id", "execution_class", "components", "allowed_edges"}
    missing = required - set(manifest)
    if missing:
        raise TopologyDenied("missing topology fields: " + ",".join(sorted(missing)))
    if manifest["execution_class"] not in ALLOWED_EXECUTION_CLASSES:
        raise TopologyDenied("topology execution class is not isolated")
    components = manifest["components"]
    if not isinstance(components, list) or not components:
        raise TopologyDenied("components must be a non-empty list")
    ids = set()
    for component in components:
        if not isinstance(component, dict):
            raise TopologyDenied("component must be an object")
        for field in ("component_id", "owner", "trust_zone", "synthetic_only"):
            if field not in component:
                raise TopologyDenied("component missing " + field)
        component_id = component["component_id"]
        if component_id in ids:
            raise TopologyDenied("duplicate component identity")
        ids.add(component_id)
        if component["synthetic_only"] is not True:
            raise TopologyDenied("non-synthetic component denied")
        capabilities = set(component.get("capabilities", []))
        if capabilities & set(LIVE_AUTHORITIES):
            raise TopologyDenied("component declares live authority")
    for edge in manifest["allowed_edges"]:
        if not isinstance(edge, dict) or not {"from", "to"} <= set(edge):
            raise TopologyDenied("malformed topology edge")
        if edge["from"] not in ids or edge["to"] not in ids:
            raise TopologyDenied("topology edge references unknown component")
        if edge.get("external") is True:
            raise TopologyDenied("external topology edge denied")
    if manifest.get("forbidden_edges") is not None and not isinstance(manifest["forbidden_edges"], list):
        raise TopologyDenied("forbidden_edges must be a list")
    return compute_topology_fingerprint(manifest)


def build_release_identity(
    *,
    source_hash: str,
    policy_hash: str,
    configuration_hash: str,
    topology_hash: str,
    synthetic_secret_id: str,
    authoritative_state_hash: str,
    environment_identity: str,
) -> dict[str, str]:
    values = {
        "source_hash": source_hash,
        "policy_hash": policy_hash,
        "configuration_hash": configuration_hash,
        "topology_hash": topology_hash,
        "synthetic_secret_id": synthetic_secret_id,
        "authoritative_state_hash": authoritative_state_hash,
        "environment_identity": environment_identity,
    }
    for name, value in values.items():
        if not isinstance(value, str) or not value:
            raise TopologyDenied(name + " is required")
        if name.endswith("_hash") and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise TopologyDenied(name + " must be SHA-256")
    values["release_fingerprint"] = _fingerprint(values)
    return values


@dataclass(frozen=True)
class DeploymentResult:
    case_id: str
    disposition: str
    release_fingerprint: str | None
    rollback_target: str | None
    evidence: dict[str, Any]


class SyntheticDeploymentController:
    """Fail-closed release controller with synthetic deployment state only."""

    def __init__(
        self,
        *,
        topology: Mapping[str, Any],
        reviewer_identity: str,
        environment_identity: str,
    ) -> None:
        self.topology = dict(topology)
        self.topology_fingerprint = validate_topology(self.topology)
        if not reviewer_identity:
            raise ValueError("reviewer_identity is required")
        self.reviewer_identity = reviewer_identity
        self.environment_identity = environment_identity
        self.current_release: dict[str, str] | None = None
        self.previous_release: dict[str, str] | None = None
        self.history: list[dict[str, str]] = []

    def _evidence(self, case_id: str, disposition: str, **details: Any) -> dict[str, Any]:
        envelope = {
            "case_id": case_id,
            "disposition": disposition,
            "topology_fingerprint": self.topology_fingerprint,
            "environment_identity": self.environment_identity,
            "reviewer_classification": "INDEPENDENT_REVIEW_REQUIRED",
            "independent_reviewer": self.reviewer_identity,
            "synthetic_only": True,
            "external_action": False,
            "effect": "none",
            **details,
        }
        envelope["evidence_sha256"] = sha256(canonical(envelope))
        return envelope

    def admit(self, request: Mapping[str, Any]) -> DeploymentResult:
        case_id = str(request.get("case_id", "P7.1.ADMISSION.unknown"))
        reasons: list[str] = []
        if request.get("execution_class") not in ALLOWED_EXECUTION_CLASSES:
            reasons.append("execution class is not isolated")
        if request.get("synthetic_only") is not True:
            reasons.append("release is not synthetic")
        if request.get("immutable") is not True:
            reasons.append("release is mutable")
        if request.get("model_output_approval") is True:
            reasons.append("model output cannot authorize release")
        if request.get("human_approval") is not True:
            reasons.append("independent human approval missing")
        if request.get("live_deployment") is True:
            reasons.append("live deployment denied")
        if request.get("live_credential") is True:
            reasons.append("live credential denied")
        authorities = request.get("authorities", {})
        for authority in LIVE_AUTHORITIES:
            if authorities.get(authority) is not False:
                reasons.append(authority + " authority denied")
        release = request.get("release_identity")
        if not isinstance(release, dict):
            reasons.append("release identity missing")
        else:
            if release.get("topology_hash") != self.topology_fingerprint:
                reasons.append("topology fingerprint mismatch")
            if release.get("environment_identity") != self.environment_identity:
                reasons.append("environment mismatch")
        if reasons:
            evidence = self._evidence(case_id, "DENIED", reasons=reasons)
            return DeploymentResult(case_id, "DENIED", None, None, evidence)
        self.previous_release = self.current_release
        self.current_release = dict(release)
        self.history.append(dict(release))
        evidence = self._evidence(case_id, "ADMITTED", release_fingerprint=release["release_fingerprint"])
        return DeploymentResult(case_id, "ADMITTED", release["release_fingerprint"], None, evidence)

    def rollback(self, case_id: str, target: Mapping[str, str] | None = None, *, inject_failure: bool = False) -> DeploymentResult:
        if target is None or not target.get("release_fingerprint"):
            raise RollbackDenied("rollback target is missing")
        if inject_failure:
            evidence = self._evidence(case_id, "ROLLBACK_FAILED", rollback_target=target["release_fingerprint"], reason="injected failure")
            return DeploymentResult(case_id, "ROLLBACK_FAILED", None, target["release_fingerprint"], evidence)
        if target.get("topology_hash") != self.topology_fingerprint:
            raise RollbackDenied("rollback target topology mismatch")
        if target.get("environment_identity") != self.environment_identity:
            raise RollbackDenied("rollback target environment mismatch")
        self.current_release = dict(target)
        evidence = self._evidence(case_id, "ROLLED_BACK", release_fingerprint=target["release_fingerprint"], rollback_target=target["release_fingerprint"])
        return DeploymentResult(case_id, "ROLLED_BACK", target["release_fingerprint"], target["release_fingerprint"], evidence)


def verify_evidence_hash(evidence: Mapping[str, Any]) -> bool:
    claimed = evidence.get("evidence_sha256")
    if not isinstance(claimed, str):
        return False
    material = dict(evidence)
    material.pop("evidence_sha256", None)
    return claimed == sha256(canonical(material))

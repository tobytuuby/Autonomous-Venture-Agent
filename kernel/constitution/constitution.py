"""Fail-closed constitution and action-purpose checks for P0."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

class ConstitutionViolation(PermissionError):
    pass

@dataclass(frozen=True)
class Constitution:
    forbidden_actions: frozenset[str] = frozenset({"kernel.modify", "policy.weaken", "credential.exfiltrate", "autonomous_irreversible_action"})
    protected_capabilities: frozenset[str] = frozenset({"shell.exec", "browser.navigate", "file.write", "payment.capture", "deployment.apply"})

    def authorize(self, *, action: str, capability: str, purpose: str, provenance_tainted: bool = False, external_content: bool = False) -> bool:
        if not action or not capability or not purpose:
            raise ConstitutionViolation("action, capability, and purpose are required")
        if action in self.forbidden_actions:
            raise ConstitutionViolation("constitution forbids the requested action")
        if capability in self.protected_capabilities and (provenance_tainted or external_content):
            raise ConstitutionViolation("untrusted or external content cannot authorize a protected capability")
        normalized_purpose = purpose.strip().lower()
        if normalized_purpose in {"", "unspecified", "personal", "unknown"}:
            raise ConstitutionViolation("capability purpose is not sufficiently specific")
        purpose_requirements = {
            "payment.capture": ("purchase", "payment", "charge"),
            "deployment.apply": ("deploy", "release"),
            "shell.exec": ("diagnostic", "maintenance"),
            "browser.navigate": ("research", "review"),
        }
        required_terms = purpose_requirements.get(capability)
        if required_terms and not any(term in normalized_purpose for term in required_terms):
            raise ConstitutionViolation("capability purpose does not match the requested capability")
        return True

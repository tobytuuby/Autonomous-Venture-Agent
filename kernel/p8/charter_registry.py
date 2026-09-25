"""Synthetic registry for binding P8.1 requests to P8.0 preflight records."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS


class CharterRegistryDenied(ValueError):
    """Raised when a P8.0 charter record cannot be approved or resolved."""


class SyntheticCharterRegistry:
    """In-memory, synthetic-only registry of validated P8.0 charter results."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise CharterRegistryDenied(f"{field} must be non-empty")
        return value

    def approve(self, preflight: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(preflight, Mapping):
            raise CharterRegistryDenied("P8.0 preflight must be an object")
        if preflight.get("status") != "PREFLIGHT_READY":
            raise CharterRegistryDenied("only PREFLIGHT_READY records may be approved")
        if preflight.get("synthetic_only") is not True or preflight.get("effect") != "none":
            raise CharterRegistryDenied("charter must be synthetic and effect-free")
        if preflight.get("live_action_permitted") is not False:
            raise CharterRegistryDenied("live action must remain denied")
        approval = preflight.get("written_live_action_approval")
        if not isinstance(approval, Mapping) or approval.get("status") != "PENDING":
            raise CharterRegistryDenied("written live-action approval must remain pending")
        flags = preflight.get("authority_flags")
        if flags != {field: False for field in LIVE_FIELDS}:
            raise CharterRegistryDenied("all nine live authorities must be explicitly false")
        charter_hash = self._text(preflight.get("record_hash"), "record_hash")
        if len(charter_hash) != 64 or any(c not in "0123456789abcdef" for c in charter_hash):
            raise CharterRegistryDenied("record_hash must be a SHA-256 digest")
        record = {
            "charter_hash": charter_hash,
            "venture_id": self._text(preflight.get("venture_id"), "venture_id"),
            "authority_class": self._text(preflight.get("authority_class"), "authority_class"),
            "status": "APPROVED_SYNTHETIC_PREFLIGHT",
            "synthetic_only": True,
            "effect": "none",
            "authority_flags": dict(flags),
        }
        prior = self._records.get(charter_hash)
        if prior is not None and prior != record:
            raise CharterRegistryDenied("charter hash collision")
        self._records[charter_hash] = copy.deepcopy(record)
        return copy.deepcopy(record)

    def resolve(self, charter_hash: str) -> dict[str, Any] | None:
        if not isinstance(charter_hash, str):
            return None
        record = self._records.get(charter_hash)
        return copy.deepcopy(record) if record is not None else None

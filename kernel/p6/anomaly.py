"""P6.3 synthetic aggregate anomaly controls."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping

from .coordination import CoordinationDenied
from .registry import LIVE_FIELDS, canonical, digest


class AnomalyDenied(CoordinationDenied):
    """Raised when aggregate analysis fails closed."""


REQUIRED_REQUEST_FIELDS = {
    "analysis_id",
    "portfolio_id",
    "records",
    "policy_version",
    "configuration_fingerprint",
    "source_ids",
    "source_hashes",
    "lineage",
    "taint",
    "analyzed_at",
    "synthetic_only",
    "effect",
    "canonical_hash",
}

REQUIRED_RECORD_FIELDS = {
    "record_id",
    "demand_id",
    "portfolio_id",
    "venture_id",
    "coordination_request_id",
    "service_class",
    "requested_units",
    "quota_max_units",
    "aggregate_quota_minor",
    "created_at",
    "expiry_at",
    "configuration_fingerprint",
    "source_ids",
    "source_hashes",
    "lineage",
    "taint",
    "synthetic_only",
    "effect",
    "record_hash",
}

DEFAULT_RULES = {
    "drift_threshold_units": 5,
    "structuring_min_records": 3,
    "structuring_total_units": 10,
    "structuring_unit_ceiling": 4,
}


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise AnomalyDenied("INVALID_TIME", f"{field} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnomalyDenied("INVALID_TIME", f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AnomalyDenied("INVALID_TIME", f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _without_hash(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    material = dict(value)
    material.pop(field, None)
    return material


def compute_record_hash(record: Mapping[str, Any]) -> str:
    return digest(canonical(_without_hash(record, "record_hash")))


def compute_analysis_hash(request: Mapping[str, Any]) -> str:
    material = _without_hash(request, "canonical_hash")
    if isinstance(material.get("records"), list):
        material["records"] = sorted(
            material["records"],
            key=lambda item: item.get("record_id", ""),
        )
    return digest(canonical(material))


def build_analysis_request(
    *,
    analysis_id: str,
    portfolio_id: str,
    records: list[Mapping[str, Any]],
    policy_version: str,
    configuration_fingerprint: str,
    source_ids: list[str],
    source_hashes: list[str],
    lineage: list[str],
    taint: list[str],
    analyzed_at: str,
    rules: Mapping[str, int] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    normalized_records = []
    for raw in records:
        record = dict(raw)
        record["record_hash"] = compute_record_hash(record)
        normalized_records.append(record)
    request = {
        "analysis_id": analysis_id,
        "portfolio_id": portfolio_id,
        "records": normalized_records,
        "policy_version": policy_version,
        "configuration_fingerprint": configuration_fingerprint,
        "source_ids": list(source_ids),
        "source_hashes": list(source_hashes),
        "lineage": list(lineage),
        "taint": list(taint),
        "analyzed_at": analyzed_at,
        "rules": dict(rules or DEFAULT_RULES),
        "synthetic_only": True,
        "effect": "none",
        **extra,
    }
    request["canonical_hash"] = compute_analysis_hash(request)
    return request


class SyntheticAnomalyAnalyzer:
    """Stateless analyzer producing review/quarantine evidence only."""

    def __init__(
        self,
        *,
        policy_version: str,
        configuration_fingerprint: str,
        rules: Mapping[str, int] | None = None,
    ):
        self.policy_version = policy_version
        self.configuration_fingerprint = configuration_fingerprint
        self.rules = dict(DEFAULT_RULES)
        self.rules.update(dict(rules or {}))
        if any(not isinstance(v, int) or v <= 0 for v in self.rules.values()):
            raise AnomalyDenied("INVALID_RULES", "anomaly rules must be positive integers")

    def analyze(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self._validate_request(request)
        findings = []
        records = list(request["records"])
        now = _parse_time(request["analyzed_at"], "analyzed_at")
        rules = dict(self.rules)
        rules.update(request.get("rules", {}))

        self._detect_cross_venture_leakage(records, findings)
        self._detect_drift(records, findings, rules)
        self._detect_duplicate_and_structuring(records, findings, rules)
        self._detect_stale(records, findings, now)
        self._detect_quota(records, findings)
        self._detect_reuse(records, findings)

        if not findings:
            findings.append(self._finding(
                "NO_ANOMALY", "NO_ANOMALY", request["portfolio_id"], records
            ))
        findings.sort(key=lambda item: (item["code"], item["target_id"]))
        result = {
            "analysis_id": request["analysis_id"],
            "portfolio_id": request["portfolio_id"],
            "finding_count": len(findings),
            "findings": findings,
            "finding_hashes": [item["finding_hash"] for item in findings],
            "analysis_hash": compute_analysis_hash(request),
            "configuration_fingerprint": self.configuration_fingerprint,
            "policy_version": self.policy_version,
            "synthetic_only": True,
            "effect": "none",
            "execution_requested": False,
            "capability_granted": False,
            "stateless": True,
        }
        result["result_hash"] = digest(canonical(result))
        return result

    def _validate_request(self, request: Mapping[str, Any]) -> None:
        missing = REQUIRED_REQUEST_FIELDS.difference(request)
        if missing:
            raise AnomalyDenied("MISSING_FIELD", "missing fields: " + ",".join(sorted(missing)))
        if request["synthetic_only"] is not True or request["effect"] != "none":
            raise AnomalyDenied("EFFECTFUL_INPUT", "analysis is synthetic and effect-free")
        if any(bool(request.get(field)) for field in LIVE_FIELDS):
            raise AnomalyDenied("LIVE_AUTHORITY", "live authority is denied")
        if request["policy_version"] != self.policy_version:
            raise AnomalyDenied("POLICY_MISMATCH", "policy version mismatch")
        if request["configuration_fingerprint"] != self.configuration_fingerprint:
            raise AnomalyDenied("FINGERPRINT_MISMATCH", "configuration fingerprint mismatch")
        if not isinstance(request["analysis_id"], str) or not request["analysis_id"]:
            raise AnomalyDenied("INVALID_IDENTITY", "analysis_id is required")
        if not isinstance(request["portfolio_id"], str) or not request["portfolio_id"]:
            raise AnomalyDenied("INVALID_SCOPE", "portfolio_id is required")
        self._validate_provenance(request)
        _parse_time(request["analyzed_at"], "analyzed_at")
        if not isinstance(request["records"], list) or not request["records"]:
            raise AnomalyDenied("EMPTY_INPUT", "at least one record is required")
        if request["canonical_hash"] != compute_analysis_hash(request):
            raise AnomalyDenied("CANONICAL_HASH", "analysis canonical hash mismatch")
        for record in request["records"]:
            self._validate_record(record, request)

    def _validate_record(self, record: Mapping[str, Any], request: Mapping[str, Any]) -> None:
        missing = REQUIRED_RECORD_FIELDS.difference(record)
        if missing:
            raise AnomalyDenied("MISSING_RECORD_FIELD", "missing fields: " + ",".join(sorted(missing)))
        if record["portfolio_id"] != request["portfolio_id"]:
            raise AnomalyDenied("CROSS_PORTFOLIO", "record portfolio does not match request")
        if record["configuration_fingerprint"] != self.configuration_fingerprint:
            raise AnomalyDenied("FINGERPRINT_MISMATCH", "record fingerprint mismatch")
        if record["synthetic_only"] is not True or record["effect"] != "none":
            raise AnomalyDenied("EFFECTFUL_RECORD", "source record is not synthetic and effect-free")
        if any(bool(record.get(field)) for field in LIVE_FIELDS):
            raise AnomalyDenied("LIVE_AUTHORITY", "source record carries live authority")
        if record["record_hash"] != compute_record_hash(record):
            raise AnomalyDenied("RECORD_HASH", "source record hash mismatch")
        if not isinstance(record["venture_id"], str) or not record["venture_id"]:
            raise AnomalyDenied("INVALID_SCOPE", "venture_id is required")
        if not isinstance(record["requested_units"], int) or record["requested_units"] <= 0:
            raise AnomalyDenied("INVALID_VALUE", "requested_units must be positive")
        if not isinstance(record["quota_max_units"], int) or record["quota_max_units"] <= 0:
            raise AnomalyDenied("INVALID_VALUE", "quota_max_units must be positive")
        if not isinstance(record["aggregate_quota_minor"], int) or record["aggregate_quota_minor"] <= 0:
            raise AnomalyDenied("INVALID_VALUE", "aggregate_quota_minor must be positive")
        self._validate_provenance(record)
        _parse_time(record["created_at"], "record.created_at")
        _parse_time(record["expiry_at"], "record.expiry_at")

    @staticmethod
    def _validate_provenance(value: Mapping[str, Any]) -> None:
        if not isinstance(value["source_ids"], list) or not value["source_ids"]:
            raise AnomalyDenied("MISSING_PROVENANCE", "source_ids are required")
        if not isinstance(value["source_hashes"], list) or not value["source_hashes"]:
            raise AnomalyDenied("MISSING_PROVENANCE", "source_hashes are required")
        if len(value["source_ids"]) != len(value["source_hashes"]):
            raise AnomalyDenied("MISSING_PROVENANCE", "source ids and hashes must align")
        if not isinstance(value["lineage"], list) or not value["lineage"]:
            raise AnomalyDenied("MISSING_PROVENANCE", "lineage is required")
        if not isinstance(value["taint"], list):
            raise AnomalyDenied("MISSING_PROVENANCE", "taint must be a list")

    @staticmethod
    def _finding(code: str, status: str, target_id: str, records: list[Mapping[str, Any]], reason: str = "") -> dict[str, Any]:
        source_hashes = sorted({item["record_hash"] for item in records})
        finding = {
            "code": code,
            "status": status,
            "target_id": target_id,
            "reason": reason or code.lower().replace("_", " "),
            "source_record_ids": sorted(item["record_id"] for item in records),
            "source_hashes": source_hashes,
            "venture_ids": sorted({item["venture_id"] for item in records}),
            "taint": sorted({tag for item in records for tag in item["taint"]}),
            "effect": "none",
            "capability_granted": False,
        }
        finding["finding_hash"] = digest(canonical(finding))
        return finding

    def _detect_cross_venture_leakage(self, records, findings):
        grouped = defaultdict(list)
        for record in records:
            grouped[record["demand_id"]].append(record)
        for demand_id, items in grouped.items():
            if len({item["venture_id"] for item in items}) > 1:
                findings.append(self._finding(
                    "CROSS_VENTURE_LEAKAGE", "QUARANTINED", demand_id, items
                ))

    def _detect_drift(self, records, findings, rules):
        grouped = defaultdict(list)
        for record in records:
            grouped[(record["venture_id"], record["service_class"])].append(record)
        for target, items in grouped.items():
            if max(item["requested_units"] for item in items) - min(item["requested_units"] for item in items) >= rules["drift_threshold_units"]:
                findings.append(self._finding(
                    "SLOW_DRIFT", "REVIEW_REQUIRED", ":".join(target), items
                ))

    def _detect_duplicate_and_structuring(self, records, findings, rules):
        duplicate_groups = defaultdict(list)
        for record in records:
            duplicate_groups[(record["venture_id"], record["demand_id"])].append(record)
        for target, items in duplicate_groups.items():
            if len(items) > 1 and len({item["venture_id"] for item in items}) == 1:
                findings.append(self._finding(
                    "DUPLICATE_PATTERN", "REVIEW_REQUIRED", ":".join(target), items
                ))
        grouped = defaultdict(list)
        for record in records:
            grouped[(record["venture_id"], record["service_class"])].append(record)
        for target, items in grouped.items():
            if (
                len(items) >= rules["structuring_min_records"]
                and sum(item["requested_units"] for item in items) >= rules["structuring_total_units"]
                and all(item["requested_units"] <= rules["structuring_unit_ceiling"] for item in items)
            ):
                findings.append(self._finding(
                    "STRUCTURING_PATTERN", "REVIEW_REQUIRED", ":".join(target), items
                ))

    def _detect_stale(self, records, findings, now):
        for record in records:
            if _parse_time(record["expiry_at"], "record.expiry_at") <= now:
                findings.append(self._finding(
                    "STALE_EVIDENCE", "QUARANTINED", record["record_id"], [record]
                ))

    def _detect_quota(self, records, findings):
        grouped = defaultdict(list)
        for record in records:
            grouped[record["venture_id"]].append(record)
        for venture_id, items in grouped.items():
            if sum(item["requested_units"] for item in items) > min(item["aggregate_quota_minor"] for item in items):
                findings.append(self._finding(
                    "QUOTA_EXHAUSTION", "REVIEW_REQUIRED", venture_id, items
                ))

    def _detect_reuse(self, records, findings):
        for field, code in (("counterparty_id", "COUNTERPARTY_REUSE"), ("beneficiary_id", "BENEFICIARY_REUSE")):
            grouped = defaultdict(list)
            for record in records:
                if record.get(field):
                    grouped[record[field]].append(record)
            for value, items in grouped.items():
                if len({item["venture_id"] for item in items}) > 1:
                    findings.append(self._finding(
                        code, "REVIEW_REQUIRED", value, items
                    ))

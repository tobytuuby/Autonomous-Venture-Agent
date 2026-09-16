"""Causal provenance and taint propagation primitives for P0.6."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


class ProvenanceError(PermissionError):
    pass


@dataclass(frozen=True)
class ProvenanceRecord:
    record_id: str
    kind: str
    parent_ids: tuple[str, ...] = ()
    taint_status: str = "unknown"
    evidence_ids: tuple[str, ...] = ()
    human_declassification_id: str | None = None

    @property
    def tainted(self) -> bool:
        return self.taint_status == "tainted"


@dataclass
class ProvenanceTracker:
    records: dict[str, ProvenanceRecord] = field(default_factory=dict)

    def add_evidence(self, record_id: str, evidence_ids: tuple[str, ...], tainted: bool) -> ProvenanceRecord:
        record = ProvenanceRecord(
            record_id=record_id, kind="evidence", evidence_ids=evidence_ids,
            taint_status="tainted" if tainted else "trusted",
        )
        self.records[record_id] = record
        return record

    def derive(self, record_id: str, kind: str, parent_ids: tuple[str, ...]) -> ProvenanceRecord:
        if not parent_ids or any(parent_id not in self.records for parent_id in parent_ids):
            raise ValueError("every derived record must name existing parents")
        parents = [self.records[parent_id] for parent_id in parent_ids]
        evidence_ids = tuple(sorted({e for parent in parents for e in parent.evidence_ids}))
        tainted = any(parent.tainted for parent in parents)
        record = ProvenanceRecord(
            record_id=record_id, kind=kind, parent_ids=parent_ids,
            taint_status="tainted" if tainted else "trusted", evidence_ids=evidence_ids,
        )
        self.records[record_id] = record
        return record

    def declassify(
        self, record_id: str, actor_type: str, operator_authenticator: Callable[[str], bool],
        declassification_id: str,
    ) -> ProvenanceRecord:
        record = self.records[record_id]
        if actor_type != "human_operator" or not operator_authenticator(declassification_id):
            raise ProvenanceError("only authenticated human operators may declassify")
        updated = ProvenanceRecord(
            record_id=record.record_id, kind=record.kind, parent_ids=record.parent_ids,
            taint_status="declassified", evidence_ids=record.evidence_ids,
            human_declassification_id=declassification_id,
        )
        self.records[record_id] = updated
        return updated

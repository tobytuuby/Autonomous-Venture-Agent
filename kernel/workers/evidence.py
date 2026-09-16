"""Worker result taint boundary."""
from kernel.provenance import ProvenanceTracker
class WorkerEvidenceBoundary:
    def __init__(self): self.tracker = ProvenanceTracker()
    def accept(self, worker_id: str, evidence_ids: tuple[str, ...], instruction_tainted: bool):
        return self.tracker.add_evidence(worker_id, evidence_ids, tainted=instruction_tainted)
    def manager_may_treat_as_clean(self, worker_id: str) -> bool:
        return not self.tracker.records[worker_id].tainted

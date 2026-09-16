"""Hash-chained append-only ledger used for certification and recovery fixtures."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any

class LedgerIntegrityError(RuntimeError):
    pass

@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    event: str
    payload: dict[str, Any]
    previous_hash: str
    entry_hash: str

class TamperEvidentLedger:
    def __init__(self):
        self.entries: list[LedgerEntry] = []

    @staticmethod
    def _digest(sequence: int, event: str, payload: dict[str, Any], previous_hash: str) -> str:
        body = json.dumps({"sequence": sequence, "event": event, "payload": payload, "previous_hash": previous_hash}, sort_keys=True, separators=(",", ":"))
        return sha256(body.encode("utf-8")).hexdigest()

    def append(self, event: str, payload: dict[str, Any]) -> LedgerEntry:
        previous = self.entries[-1].entry_hash if self.entries else "GENESIS"
        sequence = len(self.entries) + 1
        entry = LedgerEntry(sequence, event, dict(payload), previous, self._digest(sequence, event, payload, previous))
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        previous = "GENESIS"
        for expected_sequence, entry in enumerate(self.entries, 1):
            if entry.sequence != expected_sequence or entry.previous_hash != previous:
                raise LedgerIntegrityError("ledger sequence or predecessor hash was modified")
            expected = self._digest(entry.sequence, entry.event, entry.payload, entry.previous_hash)
            if entry.entry_hash != expected:
                raise LedgerIntegrityError("ledger entry hash mismatch")
            previous = entry.entry_hash
        return True

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        self.verify()
        return tuple(asdict(entry) for entry in self.entries)

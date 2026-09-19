"""P5.2 synthetic, non-spendable treasury simulation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping

from .revenue import LIVE_FIELDS
from .reconciliation import canonical, digest


class TreasuryDenied(ValueError):
    """Raised when a treasury input or result violates a P5.2 invariant."""


class SyntheticTreasury:
    """Durable treasury simulation with no payment or capital authority."""

    def __init__(
        self,
        configuration_fingerprint: str,
        reserve_floor_minor: int,
        deployable_ceiling_minor: int,
        database: str = ":memory:",
    ):
        if not isinstance(reserve_floor_minor, int) or reserve_floor_minor < 0:
            raise TreasuryDenied("reserve floor must be a non-negative integer")
        if not isinstance(deployable_ceiling_minor, int) or deployable_ceiling_minor < 0:
            raise TreasuryDenied("deployable ceiling must be a non-negative integer")
        if reserve_floor_minor > deployable_ceiling_minor:
            raise TreasuryDenied("reserve floor cannot exceed deployable ceiling")
        self.configuration_fingerprint = configuration_fingerprint
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS treasury_receipts (
                simulation_hash TEXT PRIMARY KEY,
                receipt_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS treasury_constraints (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                reserve_floor_minor INTEGER NOT NULL,
                deployable_ceiling_minor INTEGER NOT NULL,
                committed_allocation_minor INTEGER NOT NULL
            )"""
        )
        self.connection.execute(
            """INSERT OR IGNORE INTO treasury_constraints
               VALUES (1, ?, ?, 0)""",
            (reserve_floor_minor, deployable_ceiling_minor),
        )
        self.connection.commit()

    def ratchet(
        self,
        *,
        reserve_floor_minor: int | None = None,
        deployable_ceiling_minor: int | None = None,
    ) -> dict[str, int]:
        current = self._constraints()
        new_floor = current["reserve_floor_minor"] if reserve_floor_minor is None else reserve_floor_minor
        new_ceiling = current["deployable_ceiling_minor"] if deployable_ceiling_minor is None else deployable_ceiling_minor
        if not isinstance(new_floor, int) or new_floor < current["reserve_floor_minor"]:
            raise TreasuryDenied("reserve floor ratchet cannot loosen")
        if not isinstance(new_ceiling, int) or new_ceiling > current["deployable_ceiling_minor"] or new_ceiling < new_floor:
            raise TreasuryDenied("deployable ceiling ratchet cannot loosen or cross reserve floor")
        self.connection.execute(
            "UPDATE treasury_constraints SET reserve_floor_minor = ?, deployable_ceiling_minor = ? WHERE singleton = 1",
            (new_floor, new_ceiling),
        )
        self.connection.commit()
        return self._constraints()

    def simulate(
        self,
        receipts: list[Mapping[str, Any]],
        *,
        requested_allocation_minor: int = 0,
    ) -> tuple[dict[str, Any], bool]:
        self._validate_receipts(receipts)
        if not isinstance(requested_allocation_minor, int) or requested_allocation_minor < 0:
            raise TreasuryDenied("requested allocation must be a non-negative integer")
        constraints = self._constraints()
        source_hashes = sorted(receipt["reconciliation_hash"] for receipt in receipts)
        total = sum(receipt["total_amount_minor"] for receipt in receipts)
        reserve = max(constraints["reserve_floor_minor"], total)
        deployable = min(
            constraints["deployable_ceiling_minor"],
            max(0, total - constraints["reserve_floor_minor"]),
        )
        if requested_allocation_minor > deployable:
            raise TreasuryDenied("requested allocation exceeds synthetic deployable ceiling")
        material = {
            "configuration_fingerprint": self.configuration_fingerprint,
            "venture_id": receipts[0]["venture_id"],
            "source_reconciliation_hashes": source_hashes,
            "total_reconciled_amount_minor": total,
            "provenance": sorted(
                [item for receipt in receipts for item in receipt["provenance"]],
                key=canonical,
            ),
            "reserve_floor_minor": constraints["reserve_floor_minor"],
            "deployable_ceiling_minor": constraints["deployable_ceiling_minor"],
            "reserve_balance_minor": reserve,
            "deployable_balance_minor": deployable,
            "requested_allocation_minor": requested_allocation_minor,
        }
        simulation_hash = digest(canonical(material))
        existing = self.connection.execute(
            "SELECT receipt_json FROM treasury_receipts WHERE simulation_hash = ?",
            (simulation_hash,),
        ).fetchone()
        if existing:
            return json.loads(existing["receipt_json"]), True
        receipt = dict(material)
        receipt.update({
            "simulation_hash": simulation_hash,
            "status": "SIMULATED",
            "capability": "synthetic-treasury",
            "effect": "none",
            "spendable": False,
            "external_action_authorized": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self.connection.execute(
            "INSERT INTO treasury_receipts VALUES (?, ?, ?)",
            (simulation_hash, canonical(receipt), receipt["created_at"]),
        )
        self.connection.commit()
        return receipt, False

    def get(self, simulation_hash: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT receipt_json FROM treasury_receipts WHERE simulation_hash = ?",
            (simulation_hash,),
        ).fetchone()
        return None if row is None else json.loads(row["receipt_json"])

    def close(self) -> None:
        self.connection.close()

    def _constraints(self) -> dict[str, int]:
        row = self.connection.execute(
            "SELECT reserve_floor_minor, deployable_ceiling_minor, committed_allocation_minor "
            "FROM treasury_constraints WHERE singleton = 1"
        ).fetchone()
        return dict(row)

    def _validate_receipts(self, receipts: list[Mapping[str, Any]]) -> None:
        if not receipts:
            raise TreasuryDenied("at least one reconciliation receipt is required")
        hashes = [receipt.get("reconciliation_hash") for receipt in receipts]
        if any(not value for value in hashes) or len(set(hashes)) != len(hashes):
            raise TreasuryDenied("reconciliation receipt identities must be unique")
        for receipt in receipts:
            required = {
                "configuration_fingerprint", "source_event_ids", "source_event_hashes",
                "total_amount_minor", "reconciliation_hash", "status", "effect",
            }
            if not required.issubset(receipt):
                raise TreasuryDenied("incomplete reconciliation receipt")
            if receipt["configuration_fingerprint"] != self.configuration_fingerprint:
                raise TreasuryDenied("cross-configuration treasury input denied")
            if not receipt.get("venture_id"):
                raise TreasuryDenied("venture scope is required")
            if receipt.get("venture_id") != receipts[0].get("venture_id"):
                raise TreasuryDenied("cross-venture treasury input denied")
            if receipt["status"] != "RECONCILED" or receipt["effect"] != "none":
                raise TreasuryDenied("non-synthetic treasury input denied")
            expected_hash = digest(canonical({
                "configuration_fingerprint": receipt["configuration_fingerprint"],
                "venture_id": receipt["venture_id"],
                "source_event_ids": receipt["source_event_ids"],
                "source_event_hashes": receipt["source_event_hashes"],
                "total_amount_minor": receipt["total_amount_minor"],
                "provenance": receipt.get("provenance", []),
            }))
            if receipt["reconciliation_hash"] != expected_hash:
                raise TreasuryDenied("reconciliation receipt hash mismatch")
            if any(bool(receipt.get(field)) for field in LIVE_FIELDS):
                raise TreasuryDenied("live authority in treasury input denied")
            if not isinstance(receipt["total_amount_minor"], int) or receipt["total_amount_minor"] < 0:
                raise TreasuryDenied("reconciled amount is invalid")
            if not receipt.get("source_event_ids") or not receipt.get("source_event_hashes") or not receipt.get("provenance"):
                raise TreasuryDenied("reconciliation sources and provenance are required")
            if len(receipt["source_event_ids"]) != len(receipt["source_event_hashes"]):
                raise TreasuryDenied("reconciliation source identity and hash counts differ")

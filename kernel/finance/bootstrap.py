"""Durable bootstrap treasury state machine for FIN-010/P0.16.

The state is persisted in SQLite for the local kernel fixture. Production deployments
may replace the connection factory with the authoritative PostgreSQL store, but the
transition protocol and idempotency rules are identical: one state row, unique event
identifiers, and committed allocations that are never rewritten on ratchet.
"""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3
from threading import RLock
from typing import Any

STANDARD_POLICY = {"protected_cash_floor_pct": 0.50, "operating_reserve_pct": 0.20, "max_portfolio_deployable_pct": 0.30, "max_new_venture_funding_pct": 0.10}
BOOTSTRAP_POLICY = {"protected_cash_floor_pct": 0.0, "operating_reserve_pct": 0.0, "max_portfolio_deployable_pct": 1.0, "max_new_venture_funding_pct": 0.10}

class BootstrapTreasuryError(ValueError):
    """Raised when a bootstrap transition or allocation is not policy-valid."""

@dataclass(frozen=True)
class TreasuryState:
    mode: str
    seed_balance: float
    eligible_balance: float
    available_profit: float
    deployed: float
    new_venture_deployed: float
    entry_event_id: str
    exit_event_id: str | None
    exit_sweep_id: str | None
    transition_version: int

class BootstrapTreasury:
    """A durable, idempotent bootstrap-to-standard treasury state machine."""

    def __init__(self, database: str = ":memory:", *, seed_balance: float | None = None):
        self.database = database
        self._lock = RLock()
        self._conn = sqlite3.connect(database, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        row = self._conn.execute("SELECT mode FROM bootstrap_state WHERE singleton = 1").fetchone()
        if row is None:
            if seed_balance is None or float(seed_balance) <= 0:
                raise BootstrapTreasuryError("positive initial seed balance is required")
            self._enter_once(float(seed_balance), "bootstrap-entry")
        elif seed_balance is not None and float(seed_balance) != self.state.seed_balance:
            raise BootstrapTreasuryError("durable bootstrap seed cannot be changed")

    def _create_schema(self) -> None:
        with self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS bootstrap_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    mode TEXT NOT NULL CHECK (mode IN ('bootstrap', 'standard')),
                    seed_balance REAL NOT NULL CHECK (seed_balance > 0),
                    eligible_balance REAL NOT NULL CHECK (eligible_balance >= 0),
                    available_profit REAL NOT NULL DEFAULT 0,
                    deployed REAL NOT NULL DEFAULT 0,
                    new_venture_deployed REAL NOT NULL DEFAULT 0,
                    entry_event_id TEXT NOT NULL UNIQUE,
                    exit_event_id TEXT UNIQUE,
                    exit_sweep_id TEXT UNIQUE,
                    transition_version INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS treasury_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    sweep_id TEXT UNIQUE,
                    available_profit REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS treasury_allocations (
                    allocation_id TEXT PRIMARY KEY,
                    amount REAL NOT NULL CHECK (amount > 0),
                    new_venture INTEGER NOT NULL CHECK (new_venture IN (0, 1)),
                    status TEXT NOT NULL CHECK (status IN ('pending', 'committed')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _enter_once(self, seed_balance: float, event_id: str) -> None:
        with self._conn:
            self._conn.execute("INSERT INTO bootstrap_state (singleton, mode, seed_balance, eligible_balance, entry_event_id) VALUES (1, 'bootstrap', ?, ?, ?)", (seed_balance, seed_balance, event_id))
            self._conn.execute("INSERT INTO treasury_events(event_id, event_type) VALUES (?, 'bootstrap_entered')", (event_id,))

    @property
    def state(self) -> TreasuryState:
        row = self._conn.execute("SELECT * FROM bootstrap_state WHERE singleton = 1").fetchone()
        if row is None:
            raise BootstrapTreasuryError("bootstrap state is missing")
        return TreasuryState(row["mode"], row["seed_balance"], row["eligible_balance"], row["available_profit"], row["deployed"], row["new_venture_deployed"], row["entry_event_id"], row["exit_event_id"], row["exit_sweep_id"], row["transition_version"])

    @property
    def policy(self) -> dict[str, float]:
        return dict(BOOTSTRAP_POLICY if self.state.mode == "bootstrap" else STANDARD_POLICY)

    @property
    def deployable_ceiling(self) -> float:
        return self.policy["max_portfolio_deployable_pct"] * self.state.eligible_balance

    @property
    def new_venture_ceiling(self) -> float:
        return self.policy["max_new_venture_funding_pct"] * self.state.eligible_balance

    def recover(self) -> TreasuryState:
        return self.state

    def sweep(self, sweep_id: str, available_profit: float) -> TreasuryState:
        if not sweep_id:
            raise BootstrapTreasuryError("sweep_id is required")
        value = float(available_profit)
        with self._lock, self._conn:
            prior = self._conn.execute("SELECT available_profit FROM treasury_events WHERE sweep_id = ?", (sweep_id,)).fetchone()
            if prior is not None:
                return self.state
            current = self.state
            self._conn.execute("INSERT INTO treasury_events(event_id, event_type, sweep_id, available_profit) VALUES (?, 'profit_sweep', ?, ?)", (f"sweep:{sweep_id}", sweep_id, value))
            self._conn.execute("UPDATE bootstrap_state SET available_profit = ? WHERE singleton = 1", (value,))
            if current.mode == "bootstrap" and value > 0:
                self._conn.execute("UPDATE bootstrap_state SET mode = 'standard', exit_event_id = ?, exit_sweep_id = ?, transition_version = transition_version + 1 WHERE singleton = 1 AND mode = 'bootstrap'", (f"bootstrap-exit:{sweep_id}", sweep_id))
        return self.state

    def record_profit_sweep(self, sweep_id: str, available_profit: float) -> TreasuryState:
        return self.sweep(sweep_id, available_profit)

    def update_balance(self, eligible_balance: float) -> TreasuryState:
        value = float(eligible_balance)
        if value < 0:
            raise BootstrapTreasuryError("eligible balance cannot be negative")
        with self._lock, self._conn:
            self._conn.execute("UPDATE bootstrap_state SET eligible_balance = ? WHERE singleton = 1", (value,))
        return self.state

    def request_allocation(self, allocation_id: str, amount: float, *, new_venture: bool = False) -> bool:
        if not allocation_id or amount <= 0:
            return False
        amount = float(amount)
        with self._lock, self._conn:
            prior = self._conn.execute("SELECT amount FROM treasury_allocations WHERE allocation_id = ?", (allocation_id,)).fetchone()
            if prior is not None:
                return float(prior["amount"]) == amount
            current = self.state
            reserved = self._conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total, COALESCE(SUM(CASE WHEN new_venture = 1 THEN amount ELSE 0 END), 0) AS new_total FROM treasury_allocations"
            ).fetchone()
            if float(reserved["total"]) + amount > self.deployable_ceiling + 1e-9:
                return False
            if new_venture and float(reserved["new_total"]) + amount > self.new_venture_ceiling + 1e-9:
                return False
            self._conn.execute("INSERT INTO treasury_allocations(allocation_id, amount, new_venture, status) VALUES (?, ?, ?, 'pending')", (allocation_id, amount, int(new_venture)))
            return True

    def commit_allocation(self, allocation_id: str) -> bool:
        with self._lock, self._conn:
            row = self._conn.execute("SELECT amount, new_venture, status FROM treasury_allocations WHERE allocation_id = ?", (allocation_id,)).fetchone()
            if row is None:
                return False
            if row["status"] == "committed":
                return True
            self._conn.execute("UPDATE treasury_allocations SET status = 'committed' WHERE allocation_id = ?", (allocation_id,))
            self._conn.execute("UPDATE bootstrap_state SET deployed = deployed + ?, new_venture_deployed = new_venture_deployed + ? WHERE singleton = 1", (row["amount"], row["amount"] if row["new_venture"] else 0))
            return True

    def allocate(self, allocation_id: str, amount: float, *, new_venture: bool = False) -> bool:
        if not self.request_allocation(allocation_id, amount, new_venture=new_venture):
            return False
        return self.commit_allocation(allocation_id)

    def allocations(self) -> tuple[dict[str, Any], ...]:
        rows = self._conn.execute("SELECT allocation_id, amount, new_venture, status FROM treasury_allocations ORDER BY created_at, allocation_id").fetchall()
        return tuple(dict(row) for row in rows)

    def close(self) -> None:
        self._conn.close()

"""Local synthetic venture registry and accounting evidence, never a payment system."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from kernel.p6.registry import LIVE_FIELDS, canonical, digest
from kernel.synthetic_orchestration import OrchestrationDenied, run_synthetic_orchestration

MAX_SEED_CENTS = 10_000


class SyntheticStoreDenied(ValueError):
    pass


class SyntheticVentureStore:
    """Caller-selected SQLite fixture store. No network or provider integration."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS ventures (
                venture_id TEXT PRIMARY KEY,
                portfolio_id TEXT NOT NULL,
                manager_id TEXT NOT NULL,
                flow_json TEXT NOT NULL,
                flow_hash TEXT NOT NULL,
                seed_cents INTEGER NOT NULL CHECK(seed_cents BETWEEN 0 AND 10000),
                synthetic_only INTEGER NOT NULL CHECK(synthetic_only = 1)
            );
            CREATE TABLE IF NOT EXISTS ledger (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                venture_id TEXT NOT NULL REFERENCES ventures(venture_id),
                event_type TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            );
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def _check_flow(flow: Mapping[str, Any]) -> None:
        if not isinstance(flow, Mapping):
            raise SyntheticStoreDenied("flow must be an object")
        SyntheticVentureStore._check_provenance(flow)
        expected = {"ceo_proposal", "manager_assignment", "worker_results",
                    "manager_aggregate", "ceo_review_package"}
        if not expected.issubset(flow):
            raise SyntheticStoreDenied("incomplete orchestration flow")
        records = [flow["ceo_proposal"], flow["manager_assignment"],
                   *flow["worker_results"], flow["manager_aggregate"], flow["ceo_review_package"]]
        venture_id = flow["ceo_proposal"]["venture_id"]
        portfolio_id = flow["manager_assignment"]["portfolio_id"]
        if not records or not isinstance(flow["worker_results"], list) or not flow["worker_results"]:
            raise SyntheticStoreDenied("missing workers")
        for record in records:
            if not isinstance(record, dict) or record.get("venture_id") != venture_id:
                raise SyntheticStoreDenied("cross-venture or malformed record")
            if (record.get("synthetic_only") is not True or record.get("effect") != "none"
                    or record.get("execution_performed") is not False
                    or record.get("external_action_count") != 0
                    or any(record.get(field) is not False for field in LIVE_FIELDS)):
                raise SyntheticStoreDenied("live authority or effect is denied")
        if (flow["ceo_review_package"]["portfolio_id"] != portfolio_id
                or flow["manager_aggregate"]["portfolio_id"] != portfolio_id
                or flow["manager_assignment"]["manager_id"] != flow["ceo_review_package"]["manager_id"]
                or flow["manager_aggregate"]["manager_id"] != flow["manager_assignment"]["manager_id"]):
            raise SyntheticStoreDenied("scope mismatch")
        result_ids = [record["task_id"] for record in flow["worker_results"]]
        if (result_ids != flow["manager_assignment"]["task_ids"]
                or result_ids != flow["manager_aggregate"]["completed_task_ids"]
                or len(result_ids) != len(set(result_ids))):
            raise SyntheticStoreDenied("worker task identity mismatch")
        if [digest(canonical(r)) for r in flow["worker_results"]] != flow["manager_aggregate"]["result_hashes"]:
            raise SyntheticStoreDenied("worker result integrity mismatch")
        if digest(canonical(flow["manager_aggregate"])) != flow["ceo_review_package"]["aggregate_hash"]:
            raise SyntheticStoreDenied("aggregate integrity mismatch")
        if flow["ceo_review_package"]["recommendation"] != "REVIEW_SYNTHETIC_RESULTS":
            raise SyntheticStoreDenied("review must remain advisory")
        for worker in flow["worker_results"]:
            artifact = worker["artifact"]
            content = json.loads(artifact["content"])
            if content["venture_id"] != venture_id or content["task_id"] != worker["task_id"]:
                raise SyntheticStoreDenied("artifact scope mismatch")

    @staticmethod
    def _check_provenance(flow: Mapping[str, Any]) -> None:
        evidence = flow.get("decision_provenance")
        if evidence is None:
            return  # Historical flows remain readable.
        if not isinstance(evidence, list) or len(evidence) != 3 or len(canonical(evidence)) > 100_000:
            raise SyntheticStoreDenied("invalid decision provenance")
        parent = None
        parent_hash = None
        configuration = None
        for stage, item in zip(("evaluation", "manager", "review"), evidence):
            if not isinstance(item, dict) or item.get("stage") != stage:
                raise SyntheticStoreDenied("decision stage mismatch")
            request, response = item["request"], item["response"]
            opportunity = request["opportunity"]
            if (item["request_hash"] != digest(canonical(request))
                    or item["response_hash"] != digest(canonical(response))
                    or item["prompt_hash"] != digest(request["system"])
                    or item["decision_id"] != digest(json.dumps(opportunity, sort_keys=True))[:16]
                    or item["parent_decision_id"] != parent
                    or opportunity["parent_decision_id"] != parent
                    or opportunity["parent_response_hash"] != parent_hash
                    or opportunity["stage"] != stage):
                raise SyntheticStoreDenied("decision lineage integrity mismatch")
            if (item.get("synthetic_only") is not True or item.get("effect") != "none"
                    or item.get("execution_performed") is not False
                    or item.get("external_action_count") != 0
                    or any(item.get(field) is not False for field in LIVE_FIELDS)):
                raise SyntheticStoreDenied("decision authority denied")
            if configuration is not None and configuration != item["configuration_fingerprint"]:
                raise SyntheticStoreDenied("decision configuration mismatch")
            configuration = item["configuration_fingerprint"]
            parent, parent_hash = item["decision_id"], item["response_hash"]
        evaluation, manager, review = evidence
        candidate = manager["request"]["opportunity"]["context"]["candidate"]
        if (candidate["idea_id"] != evaluation["response"]["selected_id"]
                or candidate not in evaluation["request"]["opportunity"]["context"]["candidates"]
                or review["request"]["opportunity"]["context"]["candidate"] != candidate
                or flow["ceo_proposal"]["venture_id"] != "exercise-" + candidate["idea_id"]
                or any(flow["ceo_proposal"][key] != candidate[key] for key in
                       ("title", "problem", "hypothesis"))):
            raise SyntheticStoreDenied("candidate lineage mismatch")
        proposal = {key: flow["ceo_proposal"][key] for key in ("venture_id", "title", "problem", "hypothesis")}
        derived = run_synthetic_orchestration(
            ceo_proposal=proposal, manager_plan=manager["response"]["plan"],
            portfolio_id=flow["manager_assignment"]["portfolio_id"])
        if (any(derived[key] != flow[key] for key in derived)
                or manager["request"]["opportunity"]["context"]["evaluation"] != evaluation["response"]
                or review["request"]["opportunity"]["context"]["evaluation"] != evaluation["response"]
                or review["request"]["opportunity"]["context"]["aggregate"] != flow["manager_aggregate"]
                or review["response"]["aggregate_hash"] != flow["ceo_review_package"]["aggregate_hash"]
                or review["response"]["disposition"] not in {"SHELVE", "CONTINUE_SYNTHETIC_RESEARCH"}):
            raise SyntheticStoreDenied("decision provenance is not bound to worker flow")

    def record(self, *, ceo_proposal: Mapping[str, Any], manager_plan: Mapping[str, Any],
               seed_cents: int, portfolio_id: str = "portfolio-synthetic",
               idempotency_key: str, decision_provenance: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if type(seed_cents) is not int or not 0 <= seed_cents <= MAX_SEED_CENTS:
            raise SyntheticStoreDenied("seed must be integer cents within $100")
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
            raise SyntheticStoreDenied("invalid idempotency key")
        # Re-derive the flow from validated fixtures; never trust caller-supplied output.
        flow = run_synthetic_orchestration(
            ceo_proposal=ceo_proposal, manager_plan=manager_plan, portfolio_id=portfolio_id)
        if decision_provenance is not None:
            # Copy caller data before validation and bind it into the existing flow hash.
            flow["decision_provenance"] = json.loads(canonical(decision_provenance))
        self._check_flow(flow)
        if decision_provenance is not None and seed_cents != decision_provenance[1]["request"]["opportunity"]["context"]["candidate"]["cost_cents"]:
            raise SyntheticStoreDenied("allocation differs from hypothetical candidate cost")
        venture_id = flow["ceo_proposal"]["venture_id"]
        flow_json = canonical(flow)
        flow_hash = digest(flow_json)
        with self.db:
            prior = self.db.execute(
                "SELECT venture_id, amount_cents FROM ledger WHERE idempotency_key=?",
                (idempotency_key,)).fetchone()
            if prior:
                existing = self.db.execute(
                    "SELECT flow_hash, seed_cents FROM ventures WHERE venture_id=?", (venture_id,)
                ).fetchone()
                if prior == (venture_id, seed_cents) and existing == (flow_hash, seed_cents):
                    return self.read(venture_id, portfolio_id=portfolio_id)
                raise SyntheticStoreDenied("conflicting idempotency key")
            if self.db.execute("SELECT 1 FROM ventures WHERE venture_id=?", (venture_id,)).fetchone():
                raise SyntheticStoreDenied("venture already registered")
            self.verify_ledger()
            self.db.execute(
                "INSERT INTO ventures VALUES (?,?,?,?,?,?,1)",
                (venture_id, portfolio_id, flow["manager_assignment"]["manager_id"],
                 flow_json, flow_hash, seed_cents))
            last = self.db.execute("SELECT entry_hash FROM ledger ORDER BY sequence DESC LIMIT 1").fetchone()
            previous_hash = last[0] if last else "GENESIS"
            sequence = self.db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM ledger").fetchone()[0]
            entry_hash = digest(canonical({
                "sequence": sequence, "venture_id": venture_id, "event_type": "SYNTHETIC_SEED_ALLOCATION",
                "amount_cents": seed_cents, "idempotency_key": idempotency_key,
                "previous_hash": previous_hash,
            }))
            self.db.execute(
                "INSERT INTO ledger(sequence, venture_id, event_type, amount_cents, idempotency_key, previous_hash, entry_hash) VALUES (?,?,?,?,?,?,?)",
                (sequence, venture_id, "SYNTHETIC_SEED_ALLOCATION", seed_cents,
                 idempotency_key, previous_hash, entry_hash))
        return self.read(venture_id, portfolio_id=portfolio_id)

    def verify_ledger(self) -> bool:
        previous = "GENESIS"
        rows = self.db.execute(
            "SELECT sequence, venture_id, event_type, amount_cents, idempotency_key, previous_hash, entry_hash FROM ledger ORDER BY sequence"
        ).fetchall()
        for index, (sequence, venture_id, event, amount, key, prev, entry_hash) in enumerate(rows, 1):
            if sequence != index or prev != previous or event != "SYNTHETIC_SEED_ALLOCATION":
                raise SyntheticStoreDenied("ledger sequence or predecessor mismatch")
            calculated = digest(canonical({
                "sequence": sequence, "venture_id": venture_id, "event_type": event,
                "amount_cents": amount, "idempotency_key": key, "previous_hash": prev,
            }))
            if calculated != entry_hash:
                raise SyntheticStoreDenied("ledger integrity mismatch")
            previous = entry_hash
        return True

    def read(self, venture_id: str, *, portfolio_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT portfolio_id, flow_json, flow_hash, seed_cents, synthetic_only FROM ventures WHERE venture_id=?",
            (venture_id,)).fetchone()
        if row is None or row[0] != portfolio_id:
            raise SyntheticStoreDenied("venture not found in requested portfolio")
        flow = json.loads(row[1])
        if row[4] != 1 or digest(row[1]) != row[2]:
            raise SyntheticStoreDenied("venture record integrity mismatch")
        self._check_flow(flow)
        self.verify_ledger()
        ledger = self.db.execute(
            "SELECT sequence,event_type,amount_cents,idempotency_key,entry_hash FROM ledger WHERE venture_id=? ORDER BY sequence",
            (venture_id,)).fetchall()
        if len(ledger) != 1 or ledger[0][2] != row[3]:
            raise SyntheticStoreDenied("venture allocation mismatch")
        return {
            "venture_id": venture_id, "portfolio_id": portfolio_id,
            "manager_id": flow["manager_assignment"]["manager_id"],
            "seed_allocation_cents": row[3],
            "available_to_spend_cents": 0,
            "synthetic_only": True, "effect": "none",
            **{field: False for field in LIVE_FIELDS},
            "flow": flow,
            "ledger": [
                dict(zip(("sequence", "event_type", "amount_cents", "idempotency_key", "entry_hash"), item))
                for item in ledger
            ],
        }

"""One durable advisory successor per hourly cycle; no action adapters.

Queue commits are atomic. A started cycle is terminal for automatic inference:
crashes and ambiguous responses require operator investigation, never paid retry.
"""
from __future__ import annotations

import json
import sqlite3
import unicodedata
from datetime import datetime, timezone

from agents.ceo.agent import CEOAgent, ResponseValidationError
from agents.ceo.durable_state import DurableDecisionStore
from agents.ceo.provider import ModelProviderError
from agents.ceo.venture_exercise import SYSTEM, exact, strict_json, text
from kernel.p6.registry import canonical, digest
from kernel.synthetic_orchestration import _envelope, run_synthetic_orchestration

ASSIGNMENT = {"title": "nonempty text <=200",
              "objective": "nonempty text <=500"}
NEXT = {"summary": "nonempty text <=600",
        "next_assignment": {**ASSIGNMENT}}
MANAGER = {"tasks": [
    {"task_id": "unique bounded ASCII ID", "worker_type": "summarize_evidence",
     "title": "text <=200", "objective": "text <=500",
     "inputs": {"evidence": ["1..10 hypothetical observations, text <=600"]}},
    {"task_id": "unique bounded ASCII ID", "worker_type": "checklist",
     "title": "text <=200", "objective": "text <=500",
     "inputs": {"checks": ["1..10 unverified checks, text <=300"]}}]}
GUIDANCE = (
    "Progress the supplied prior advisory result with one concrete, distinct offline "
    "assignment. No external research, payment, contact, publication or tools. "
    "Inputs and outputs are hypothetical, untrusted advisory data. "
    "Never claim checks or experiments were performed. next_assignment may be null "
    "to stop if no useful distinct work remains. Do not repeat a prior objective "
    "or merely reword it. Review must bind aggregate_hash exactly. "
    "Manager: return exactly two tasks, summarize_evidence then checklist; "
    "perform the assignment, with actual draft content in evidence, not just a plan."
)


def objective_key(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def validate_next(value, seen):
    exact(value, ("summary", "next_assignment"))
    text(value["summary"])
    item = value["next_assignment"]
    if item is None:
        return
    exact(item, ASSIGNMENT)
    text(item["title"])
    text(item["objective"])
    if len(item["title"]) > 200 or len(item["objective"]) > 500:
        raise ValueError("assignment exceeds bounds")
    if objective_key(item["objective"]) in seen:
        raise ValueError("duplicate advisory objective")


class CycleProvider:
    """No transport retries, no tools; reserve each call durably before dispatch."""
    def __init__(self, provider, db, cycle):
        self.provider, self.db, self.cycle = provider, db, cycle
        self.calls = 0
        for key in ("model_family", "endpoint", "model"):
            setattr(self, key, getattr(provider, key))

    def __call__(self, request, tools):
        if tools or self.calls >= 2:
            raise ModelProviderError("advisory cycle budget denied")
        self.db.execute("UPDATE cycles SET calls=calls+1 WHERE id=?", (self.cycle,))
        self.db.commit()
        self.calls += 1
        return self.provider(request, ())


def advance(state, configured, prior, cycle=None):
    """Caller holds scheduler lock and has checked the existing certification gate."""
    from agents.ceo.queue_recovery import resolution
    try:
        if resolution(state) is not None:
            return 0, {"status": "QUEUE_ADMIN_CLOSED", "inference_requests_this_tick": 0,
                       "ceo_decision": False, "automatic_retry_allowed": False}
    except Exception:
        return 4, {"status": "QUEUE_RESOLUTION_DENIED", "inference_requests_this_tick": 0}
    cycle = cycle or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    db = sqlite3.connect(state / "queue.sqlite")
    db.execute("PRAGMA synchronous=FULL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS cycles(
          id TEXT PRIMARY KEY, status TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS items(
          id TEXT PRIMARY KEY, parent TEXT, objective_key TEXT UNIQUE NOT NULL,
          assignment TEXT NOT NULL, status TEXT NOT NULL, result TEXT);
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    decisions = None
    provider = CycleProvider(configured, db, cycle)
    try:
        # Any unfinished/failed cycle blocks future cycles, even after an hour changes.
        if db.execute("SELECT 1 FROM cycles WHERE status != 'COMPLETED'").fetchone():
            return 4, {"status": "QUEUE_BLOCKED", "inference_requests_this_tick": 0}
        if db.execute("SELECT 1 FROM cycles WHERE id=?", (cycle,)).fetchone():
            pending = db.execute("SELECT id FROM items WHERE status='QUEUED'").fetchone()
            return 0, {"status": "QUEUE_REPLAYED", "inference_requests_this_tick": 0,
                       "cycle_id": cycle, "queued_item_id": pending[0] if pending else None}
        decisions = DurableDecisionStore(state / "queue.decisions.sqlite")
        if not decisions.verify_chain():
            raise ValueError("invalid queue decision chain")
        agent = CEOAgent(provider, SYSTEM, state / "queue.decisions.jsonl",
                         durable_store=decisions, advisory_only=True,
                         runner_version="advisory-queue-v1")
        fingerprint = db.execute("SELECT value FROM metadata WHERE key='fingerprint'").fetchone()
        if fingerprint and fingerprint[0] != agent.configuration_fingerprint:
            raise ValueError("configuration changed")
        if not fingerprint:
            db.execute("INSERT INTO metadata VALUES('fingerprint',?)",
                       (agent.configuration_fingerprint,))
        db.execute("INSERT INTO cycles(id,status) VALUES(?,'STARTED')", (cycle,))
        db.commit()
        pending = db.execute(
            "SELECT id, assignment FROM items WHERE status='QUEUED'").fetchall()
        if len(pending) > 1:
            raise ValueError("queue bound exceeded")
        seen = [row[0] for row in db.execute("SELECT objective_key FROM items")]
        history = [json.loads(row[0]) for row in db.execute(
            "SELECT assignment FROM items ORDER BY rowid DESC LIMIT 20")]
        evidence = []

        def role(stage, context, contract, validator):
            opportunity = dict(opportunity_id="advisory-" + cycle + "-" + stage,
                               stage=stage, context=context, response_contract=contract,
                               response_guidance=GUIDANCE,
                               parent_decision_id=evidence[-1] if evidence else None)
            def validate(raw):
                try:
                    exact(raw, ("decision", "tool_call"))
                    if raw["tool_call"] is not None:
                        raise ValueError("tools denied")
                    exact(raw["decision"], ("content",))
                    validator(strict_json(raw["decision"]["content"]))
                except Exception:
                    raise ResponseValidationError("RESPONSE_INVALID") from None
            decision = agent.shadow_decide(opportunity, response_validator=validate)
            evidence.append(decision.decision_id)
            return strict_json(decision.decision["content"])

        parent = None
        flow = None
        work_key = None
        if pending:
            parent, assignment_raw = pending[0]
            assignment = json.loads(assignment_raw)
            proposal = dict(venture_id=parent, title=assignment["title"],
                            problem=assignment["objective"],
                            hypothesis="Offline advisory drafting only; no verified market evidence.")
            def validate_manager(plan):
                exact(plan, ("tasks",))
                if not isinstance(plan["tasks"], list) or [
                        t.get("worker_type") for t in plan["tasks"]] != [
                            "summarize_evidence", "checklist"]:
                    raise ValueError("fixed local worker types required")
                signature = digest(canonical([[t["worker_type"], t["inputs"]]
                                              for t in plan["tasks"]]))
                if db.execute("SELECT 1 FROM metadata WHERE key=?",
                              ("work:" + signature,)).fetchone():
                    raise ValueError("identical worker inputs already completed")
                run_synthetic_orchestration(ceo_proposal=proposal, manager_plan=plan)
            plan = role("queue_manager", {"assignment": assignment}, MANAGER, validate_manager)
            work_key = "work:" + digest(canonical([[t["worker_type"], t["inputs"]]
                                                   for t in plan["tasks"]]))
            flow = run_synthetic_orchestration(ceo_proposal=proposal, manager_plan=plan)
            aggregate_hash = flow["ceo_review_package"]["aggregate_hash"]
            def validate_review(value):
                exact(value, ("aggregate_hash", "summary", "next_assignment"))
                if value["aggregate_hash"] != aggregate_hash:
                    raise ValueError("review lineage mismatch")
                validate_next({k: value[k] for k in NEXT}, seen)
            review = role("queue_review",
                          {"assignment": assignment, "aggregate": flow["manager_aggregate"],
                           "aggregate_hash": aggregate_hash, "recent_assignments": history},
                          dict(aggregate_hash=aggregate_hash, **NEXT), validate_review)
            next_result = {k: review[k] for k in NEXT}
        elif db.execute("SELECT 1 FROM cycles WHERE status='COMPLETED'").fetchone():
            next_result = {"summary": "Queue stopped by CEO review.", "next_assignment": None}
        else:
            # This prior result was reconstructed by the original durable workflow.
            review = prior.get("evidence", [])[-1].get("response", {})
            if review.get("disposition") != "CONTINUE_SYNTHETIC_RESEARCH":
                next_result = {"summary": "Initial exercise shelved.", "next_assignment": None}
            else:
                next_result = role("queue_proposal", {"prior_completed_result": prior},
                                   NEXT, lambda value: validate_next(value, seen))

        result = _envelope(**next_result, flow=flow, decision_ids=evidence,
                           source="configured_provider_response_not_independently_verified",
                           ai_inference_independently_verified=False)
        # Completion, successor insertion, and cycle acknowledgement share one commit.
        with db:
            if work_key:
                db.execute("INSERT INTO metadata VALUES(?,?)", (work_key, parent))
            if parent:
                db.execute("UPDATE items SET status='COMPLETED',result=? WHERE id=?",
                           (canonical(result), parent))
            item = next_result["next_assignment"]
            next_id = None
            if item is not None:
                next_id = "advisory-" + digest(canonical([parent, item]))[:24]
                db.execute("INSERT INTO items VALUES(?,?,?,?, 'QUEUED',NULL)",
                           (next_id, parent, objective_key(item["objective"]), canonical(item)))
            db.execute("INSERT INTO metadata VALUES(?,?)",
                       ("result:" + cycle, canonical(result)))
            db.execute("UPDATE cycles SET status='COMPLETED' WHERE id=?", (cycle,))
        return 0, {"status": "QUEUE_ADVANCED" if next_id else "QUEUE_STOPPED",
                   "completed_item_id": parent, "queued_item_id": next_id,
                   "cycle_id": cycle, "inference_requests_this_tick": provider.calls}
    except Exception:
        # STARTED remains durable. Never infer again after an uncertain attempt.
        return 4, {"status": "QUEUE_DENIED", "inference_requests_this_tick": provider.calls}
    finally:
        if decisions is not None:
            decisions.close()
        db.close()

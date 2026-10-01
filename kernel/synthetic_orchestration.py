"""Offline end-to-end synthetic CEO/manager/worker orchestration.

Inputs model the untrusted JSON responses from offline role fixtures. This module
has no provider, filesystem, subprocess, queue, credential, or network interface.
It produces bounded data records and JSON artifacts only.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any

from kernel.p6.registry import LIVE_FIELDS, canonical, digest

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_MAX_TEXT = 2000
_MAX_PACKETS = 3
_MAX_INPUT_BYTES = 32_000
_ALLOWED_WORKERS = {"summarize_evidence", "calculate", "checklist"}


class OrchestrationDenied(ValueError):
    """Raised when a synthetic orchestration envelope is invalid or out of scope."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise OrchestrationDenied("INVALID_ID", f"{field} must be a bounded identifier")
    return value


def _text(value: Any, field: str, *, limit: int = _MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise OrchestrationDenied("INVALID_TEXT", f"{field} must be non-empty text within {limit} characters")
    return value


def _bounded_json(value: Any, field: str) -> None:
    try:
        encoded = canonical(value).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OrchestrationDenied("INVALID_JSON", f"{field} must be JSON-compatible data") from exc
    if len(encoded) > _MAX_INPUT_BYTES:
        raise OrchestrationDenied("INPUT_TOO_LARGE", f"{field} exceeds the input size limit")


def _exact_keys(value: Mapping[str, Any], keys: set[str], field: str) -> None:
    if set(value) != keys:
        raise OrchestrationDenied("INVALID_SHAPE", f"{field} must contain exactly {sorted(keys)}")


def _envelope(**fields: Any) -> dict[str, Any]:
    return {
        **fields,
        "synthetic_only": True,
        "effect": "none",
        "execution_performed": False,
        "external_action_count": 0,
        **{name: False for name in LIVE_FIELDS},
    }


def run_synthetic_demo(brief: Mapping[str, Any]) -> dict[str, Any]:
    """Run deterministic offline CEO and manager roles, then synthetic workers.

    This helper is a local role simulation for end-to-end plumbing tests. It
    performs no model inference and accepts no callable capable of external I/O.
    """
    if not isinstance(brief, Mapping):
        raise OrchestrationDenied("INVALID_BRIEF", "brief must be a JSON object")
    _exact_keys(
        brief,
        {"venture_id", "title", "problem", "hypothesis", "evidence", "cost_values", "review_checks"},
        "synthetic brief",
    )

    # The CEO role emits exactly one proposal from the supplied synthetic brief.
    proposal = {
        "venture_id": brief["venture_id"],
        "title": brief["title"],
        "problem": brief["problem"],
        "hypothesis": brief["hypothesis"],
    }
    # The manager role receives that proposal and creates three bounded packets.
    manager_plan = {
        "tasks": [
            {
                "task_id": "evidence-review",
                "worker_type": "summarize_evidence",
                "title": "Summarize supplied synthetic evidence",
                "objective": f"Summarize evidence for: {proposal['title']}",
                "inputs": {"evidence": brief["evidence"]},
            },
            {
                "task_id": "cost-check",
                "worker_type": "calculate",
                "title": "Calculate supplied synthetic costs",
                "objective": f"Calculate example costs for: {proposal['title']}",
                "inputs": {"values": brief["cost_values"]},
            },
            {
                "task_id": "review-checklist",
                "worker_type": "checklist",
                "title": "Prepare human review checklist",
                "objective": f"List review items for: {proposal['title']}",
                "inputs": {"checks": brief["review_checks"]},
            },
        ]
    }
    return run_synthetic_orchestration(ceo_proposal=proposal, manager_plan=manager_plan)


def _worker_result(task: Mapping[str, Any], venture_id: str) -> dict[str, Any]:
    worker_type = task["worker_type"]
    inputs = task["inputs"]
    if not isinstance(inputs, Mapping):
        raise OrchestrationDenied("INVALID_WORKER_INPUT", "task inputs must be an object")

    if worker_type == "summarize_evidence":
        _exact_keys(inputs, {"evidence"}, "summarize_evidence inputs")
        evidence = inputs["evidence"]
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 10:
            raise OrchestrationDenied("INVALID_WORKER_INPUT", "evidence must contain 1 to 10 synthetic items")
        items = [_text(item, "evidence item", limit=600) for item in evidence]
        result = {"item_count": len(items), "observations": items, "interpretation": "none"}
    elif worker_type == "calculate":
        _exact_keys(inputs, {"values"}, "calculate inputs")
        values = inputs["values"]
        if not isinstance(values, list) or not 1 <= len(values) <= 20:
            raise OrchestrationDenied("INVALID_WORKER_INPUT", "values must contain 1 to 20 numbers")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
            raise OrchestrationDenied("INVALID_WORKER_INPUT", "values must be finite numbers")
        total = sum(values)
        result = {"count": len(values), "total": total, "mean": total / len(values)}
    elif worker_type == "checklist":
        _exact_keys(inputs, {"checks"}, "checklist inputs")
        checks = inputs["checks"]
        if not isinstance(checks, list) or not 1 <= len(checks) <= 10:
            raise OrchestrationDenied("INVALID_WORKER_INPUT", "checks must contain 1 to 10 items")
        result = {
            "checks": [
                {"item": _text(item, "check item", limit=300), "status": "unverified"}
                for item in checks
            ],
            "interpretation": "human review required",
        }
    else:
        raise OrchestrationDenied("UNKNOWN_WORKER", f"worker type is not registered: {worker_type}")

    artifact = {
        "artifact_id": f"artifact-{task['task_id']}",
        "media_type": "application/json",
        "content": canonical({
            "task_id": task["task_id"],
            "venture_id": venture_id,
            "worker_type": worker_type,
            "title": task["title"],
            "objective": task["objective"],
            "result": result,
            "taint": ["synthetic_input", "model_generated_task"],
        }),
    }
    return _envelope(
        task_id=task["task_id"],
        worker_id=f"worker-{worker_type}",
        venture_id=venture_id,
        status="RESULT_RECORDED",
        result=result,
        artifact=artifact,
        taint=["synthetic_input", "model_generated_task", "synthetic_worker_result"],
    )


def run_synthetic_orchestration(
    *,
    ceo_proposal: Mapping[str, Any],
    manager_plan: Mapping[str, Any],
    portfolio_id: str = "portfolio-synthetic",
) -> dict[str, Any]:
    """Run one bounded offline flow from simulated model outputs to review package.

    The two mappings are fixture responses, not calls to a language model. Their
    values remain untrusted data and can never set execution authority.
    """
    if not isinstance(ceo_proposal, Mapping) or not isinstance(manager_plan, Mapping):
        raise OrchestrationDenied("INVALID_RESPONSE", "role responses must be JSON objects")
    _bounded_json(dict(ceo_proposal), "CEO proposal")
    _bounded_json(dict(manager_plan), "manager plan")
    _exact_keys(ceo_proposal, {"venture_id", "title", "problem", "hypothesis"}, "CEO proposal")
    _exact_keys(manager_plan, {"tasks"}, "manager plan")

    venture_id = _id(ceo_proposal["venture_id"], "venture_id")
    portfolio_id = _id(portfolio_id, "portfolio_id")
    proposal = {
        "venture_id": venture_id,
        "title": _text(ceo_proposal["title"], "title"),
        "problem": _text(ceo_proposal["problem"], "problem"),
        "hypothesis": _text(ceo_proposal["hypothesis"], "hypothesis"),
    }
    proposal_hash = digest(canonical(proposal))

    tasks = manager_plan["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= _MAX_PACKETS:
        raise OrchestrationDenied("PACKET_LIMIT", f"manager must create 1 to {_MAX_PACKETS} work packets")
    normalized_tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            raise OrchestrationDenied("INVALID_TASK", f"task {index} must be an object")
        _exact_keys(task, {"task_id", "worker_type", "title", "objective", "inputs"}, f"task {index}")
        task_id = _id(task["task_id"], "task_id")
        if task_id in seen:
            raise OrchestrationDenied("DUPLICATE_TASK", "task IDs must be unique")
        seen.add(task_id)
        worker_type = task["worker_type"]
        if not isinstance(worker_type, str) or worker_type not in _ALLOWED_WORKERS:
            raise OrchestrationDenied("UNKNOWN_WORKER", f"worker type is not registered: {worker_type}")
        normalized_tasks.append({
            "task_id": task_id,
            "worker_type": worker_type,
            "title": _text(task["title"], "task title", limit=200),
            "objective": _text(task["objective"], "task objective", limit=500),
            "inputs": dict(task["inputs"]) if isinstance(task["inputs"], Mapping) else task["inputs"],
        })

    assignment = _envelope(
        assignment_id=f"assignment-{venture_id}",
        portfolio_id=portfolio_id,
        venture_id=venture_id,
        manager_id=f"manager-{venture_id}",
        proposal_hash=proposal_hash,
        task_ids=[task["task_id"] for task in normalized_tasks],
        taint=["model_generated_proposal"],
    )
    results = [_worker_result(task, venture_id) for task in normalized_tasks]
    aggregate = _envelope(
        portfolio_id=portfolio_id,
        venture_id=venture_id,
        manager_id=assignment["manager_id"],
        completed_task_ids=[result["task_id"] for result in results],
        result_hashes=[digest(canonical(result)) for result in results],
        results=results,
        status="AGGREGATED",
        taint=["model_generated_proposal", "model_generated_task", "synthetic_worker_result"],
    )
    report = _envelope(
        report_id=f"review-{venture_id}",
        portfolio_id=portfolio_id,
        venture_id=venture_id,
        proposal=proposal,
        proposal_hash=proposal_hash,
        manager_id=assignment["manager_id"],
        recommendation="REVIEW_SYNTHETIC_RESULTS",
        recommendation_basis="Synthetic worker outputs are attached for human review; no business decision was executed.",
        artifacts=[result["artifact"] for result in results],
        aggregate_hash=digest(canonical(aggregate)),
        taint=["model_generated_proposal", "model_generated_task", "synthetic_worker_result"],
    )
    flow = {
        "flow_id": f"flow-{venture_id}",
        "stages": ["CEO_PROPOSAL", "MANAGER_ASSIGNMENT", "WORKER_RESULTS", "MANAGER_AGGREGATE", "CEO_REVIEW_PACKAGE"],
        "ceo_proposal": _envelope(**proposal, proposal_hash=proposal_hash, taint=["model_generated_proposal"]),
        "manager_assignment": assignment,
        "worker_results": results,
        "manager_aggregate": aggregate,
        "ceo_review_package": report,
    }
    _bounded_json(flow, "orchestration output")
    return flow

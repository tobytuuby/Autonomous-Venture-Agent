"""Deterministic offline model for shadow-mode plumbing tests only."""


def decide(request, tool_schemas):
    opportunity = request["opportunity"]
    if opportunity.get("evidence_score", 0) < 0.8:
        return {"decision": {"action": "shelve", "reason": "insufficient evidence"}}
    return {
        "decision": {"action": "request_review", "reason": "synthetic shadow decision"},
        "tool_call": {"schema": "venture-launch-request.schema.json", "mode": "would_call_only"},
    }


decide.model_family = "synthetic-shadow-model-v1"

"""Bounded recovery through existing signed journal commands; no inference here."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.escalation_inbox import canonical
from agents.ceo.venture_workflow import hashed, research_identity

RETIRED_REASON = "Automatic recovery: retired single Worker requires current Manager decomposition."
EXCEPTION_PREFIX = "Automatic recovery terminal exception: "


class RecoveryImpossible(ValueError):
    """Exact reconciliation cannot prove that another paid request is safe."""


def command(client, config, snapshot, action, payload):
    from agents.ceo.hierarchy_research_daemon import allowed_config
    allowed_config(config, snapshot["id"], snapshot)
    research_identity(snapshot)
    now = datetime.now(timezone.utc)
    value = dict(workflow_id=snapshot["id"],
        request_id="recovery-" + hashed(dict(snapshot=hashed(snapshot), action=action, payload=payload))[:50],
        actor_id=config["actor_id"], role=config["role"], origin="control_plane",
        action=action, revision=snapshot["revision"], previous_hash=hashed(snapshot),
        version=snapshot["version"], scope_hash=snapshot["scope_hash"],
        evidence=snapshot["last_command"]["evidence"], payload=payload,
        issued_at=now.isoformat(), expires_at=(now + timedelta(minutes=5)).isoformat(), live=False)
    key = Ed25519PrivateKey.from_private_bytes(Path(config["signing_key"]).read_bytes())
    return client.apply(value, key.sign(canonical(value).encode()).hex())


def terminal_exception(client, config, snapshot, code):
    # The role owning the failure records it; CEO closes it on its next poll.
    action = {"ceo": "terminate", "manager": "hold", "worker": "security_hold"}[config["role"]]
    return command(client, config, snapshot, action, dict(reason=EXCEPTION_PREFIX + code))


def recover(client, config, snapshot):
    """At most one signed transition per poll, including after process restart."""
    if config["role"] != "ceo" or snapshot.get("research_disposition") is not None:
        return False
    last = snapshot["last_command"]
    reason = last.get("payload", {}).get("reason", "")
    if snapshot["state"] in ("HOLD", "SECURITY_HOLD") and reason.startswith(EXCEPTION_PREFIX):
        terminal_exception(client, config, snapshot, reason[len(EXCEPTION_PREFIX):])
        return True
    retired = (snapshot["scope"]["worker_id"] == "service-worker"
               and not snapshot.get("decomposition"))
    if not retired:
        return False
    if snapshot["state"] == "WORKER_PENDING":
        counts = client.worker_research_counts(snapshot)
        if (snapshot["version"] != 1 or snapshot["used_units"] >= snapshot["scope"]["budget_units"]
                or counts["round_count"] >= 4 or counts["venture_count"] >= 12):
            terminal_exception(client, config, snapshot, "RETIRED_WORKER_ALLOWANCE_EXHAUSTED")
        else:
            command(client, config, snapshot, "hold", dict(reason=RETIRED_REASON))
        return True
    if (reason == RETIRED_REASON and last.get("actor_id") == config["actor_id"]
            and last.get("request_id", "").startswith("recovery-")):
        if snapshot["state"] == "HOLD" and last["action"] == "hold":
            command(client, config, snapshot, "resume", dict(reason=RETIRED_REASON))
            return True
        if snapshot["state"] == "CEO_REDIRECTION" and last["action"] == "resume":
            # Same scope, same approval, same effort and same research session.
            command(client, config, snapshot, "revise",
                    dict(scope=snapshot["scope"], version=snapshot["version"] + 1,
                         reason=RETIRED_REASON))
            return True
    return False

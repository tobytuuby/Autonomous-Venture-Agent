"""Autonomous, role-isolated poller for Owner-approved internal research workflows.

Uses the existing pinned hierarchy mTLS broker, role signer and provider budget
governor. This is preparation-only: no tools, money or customer operations.
"""
import argparse
import hashlib
import json
import logging
import re
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.escalation_inbox import canonical
from agents.ceo.venture_workflow import hashed, research_rounds, research_session

from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_service import run as role_tick, recovery_reason

STATES = {"ceo":{"CEO_REVIEW","DECOMPOSITION_REVIEW","CEO_REDIRECTION","HOLD","OWNER_REVIEW","MANAGER_PENDING"},
          "manager":{"MANAGER_PENDING","MANAGER_REVIEW"},
          "worker":{"WORKER_PENDING"}}
RESEARCH_WORKERS = dict(A="worker-a", B="worker-b", C="worker-c")
RESEARCH_ID = re.compile(r"research-[0-9a-f]{24}\Z")


def allowed_config(base, flow, snapshot):
    role = base["role"]
    if role not in STATES or not RESEARCH_ID.fullmatch(flow):
        raise ValueError("research role or identity denied")
    if snapshot["id"] != flow or snapshot["venture_id"] != flow:
        raise ValueError("signed research workflow mismatch")
    if snapshot["mode"] != "PREPARATION_ONLY" or any(snapshot[f] is not False for f in (
            "operational_authority","external_actions_allowed","execution_performed","money_released")):
        raise ValueError("operational authority denied")
    if snapshot["scope"]["manager_id"] != "service-manager" or snapshot["scope"]["worker_id"] not in ("service-worker", "worker-a"):
        raise ValueError("research role scope denied")
    if snapshot["scope"]["budget_units"] > 5 or snapshot["scope"]["seed_cents"] != 1:
        raise ValueError("unapproved research budget")
    if not snapshot["handoff"]["item_id"] == flow or not snapshot["handoff"]["review"]["item_id"] == flow:
        raise ValueError("approved handoff missing")
    expected_actor = {"ceo": "service-ceo", "manager": "service-manager"}.get(role)
    if ((expected_actor is not None and base["actor_id"] != expected_actor)
            or (role == "worker" and base["actor_id"] not in RESEARCH_WORKERS.values())):
        raise ValueError("research actor denied")
    configured_workers = base.get("decomposition_workers")
    if configured_workers is not None and (
            type(configured_workers) is not dict or set(configured_workers) != {"A", "B", "C"}
            or set(configured_workers.values()) != set(RESEARCH_WORKERS.values())):
        raise ValueError("three-Worker research registry denied")
    plan = snapshot.get("decomposition")
    if plan:
        assignments = plan["assignments"]
        if (len(assignments) != 3 or {a["id"] for a in assignments} != {"A", "B", "C"}
                or any(a["worker_id"] != RESEARCH_WORKERS[a["id"]] for a in assignments)
                or any(a["depends_on"] not in ([], ["A", "B"] if a["id"] == "C" else [])
                       for a in assignments)):
            raise ValueError("A/B/C decomposition denied")
    if role == "worker":
        from agents.ceo.hierarchy_runner import ready_assignment
        if ready_assignment(snapshot, base["actor_id"]) is None:
            raise ValueError("research Worker assignment not ready")
    config=dict(base)
    # Override only the research task copy; preserve the configured signed workflow.
    if role == "manager":
        config["decomposition_workers"] = dict(RESEARCH_WORKERS)
    config["workflow_id"]=flow
    original=Path(base["state_dir"])
    root=Path(base.get("_research_state_root", original))
    if "_research_state_root" in base:
        # A scoped config belongs to exactly one signed session. Never turn it
        # into a queue root, including for a different workflow or round.
        if (base.get("workflow_id") != flow
                or original != root / "research" / research_session(snapshot)):
            raise ValueError("research config session mismatch")
    config["_research_state_root"]=str(root)
    state=root / "research" / research_session(snapshot)
    if original.is_symlink() or state.is_symlink():
        raise ValueError("research state alias denied")
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    config["state_dir"]=str(state)
    if role in ("ceo","manager"):
        context=dict(base["context"])
        rounds = len(research_rounds(snapshot))
        command = snapshot.get("last_command", {})
        recovered = (command.get("action") == "recover_legacy_worker"
                     and command.get("actor_id") == "service-ceo"
                     and command.get("role") == "ceo"
                     and command.get("workflow_id") == flow
                     and command.get("scope_hash") == snapshot["scope_hash"])
        # Authenticated snapshots retain the legacy scope through signed A/B/C
        # transitions even after last_command replaces the recovery command.
        # Only its original session used the old two-round exchange binding.
        # The broker still requires the exact established context and policy;
        # this neither creates a replacement session nor changes quota history.
        if (snapshot["scope"]["worker_id"] == "service-worker"
                and rounds == 1 and research_session(snapshot) == flow
                and (recovered or bool(plan))
                and type(context.get("rounds")) is int and context["rounds"] == 2):
            rounds = context["rounds"]
        context.update(session_id=research_session(snapshot),venture_id=flow,
                       objective="; ".join(snapshot["scope"]["tasks"]),rounds=rounds)
        config["context"]=context
    return config


def worker_submission_count(client,snapshot):
    """Count only digest-verified Worker submissions in the signed journal."""
    count=0
    for ref,sha in snapshot['evidence'].items():
        if not ref.startswith('preparation-') or not ref.endswith(sha):
            continue
        raw=client.load(ref)
        if hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError('research worker evidence digest corrupted')
        evidence=json.loads(raw)
        if evidence.get('scope_hash')!=snapshot['scope_hash']:
            continue  # Retain earlier rounds, but do not charge their submissions twice.
        if evidence.get('role')=='worker' and evidence.get('action')=='submit':
            count+=1
    return count


def worker_round_reservation_count(client, snapshot):
    """Read broker-owned counts over the existing authenticated hierarchy client."""
    counts = client.worker_research_counts(snapshot)
    return counts["round_count"]


def hold_exhausted_research(client,config,snapshot,worker_limit):
    """CEO signer records reserved quota exhaustion; never infers, spends or funds."""
    if (config['role']!='ceo' or config['actor_id']!='service-ceo'
            or snapshot['state']!='WORKER_PENDING'
            or not RESEARCH_ID.fullmatch(snapshot['id'])):
        return False
    counts = client.worker_research_counts(snapshot)
    if counts["round_count"] < min(worker_limit, 4) and counts["venture_count"] < 12:
        return False
    # The workflow itself is authenticated by the broker. Recheck all safety
    # constraints before invoking the existing role-signature gate.
    allowed_config(config,snapshot['id'],snapshot)
    previous=snapshot['last_command']['evidence']
    if not previous:
        raise ValueError('signed evidence required for hold')
    now=datetime.now(timezone.utc)
    command=dict(workflow_id=snapshot['id'],
        request_id='quota-hold-'+hashed(snapshot)[:50],
        actor_id='service-ceo',role='ceo',origin='control_plane',
        action='hold',revision=snapshot['revision'],
        previous_hash=hashed(snapshot),version=snapshot['version'],
        scope_hash=snapshot['scope_hash'],evidence=previous,
        payload=dict(reason='Worker inference quota exhausted before Manager approved the internal research assessment. Further evidence or revised scope required.'),
        issued_at=now.isoformat(),expires_at=(now+timedelta(minutes=5)).isoformat(),live=False)
    key=Ed25519PrivateKey.from_private_bytes(Path(config['signing_key']).read_bytes())
    result=client.apply(command,key.sign(canonical(command).encode()).hex())
    if result['state']!='HOLD':
        raise ValueError('research quota hold not committed')
    logging.warning('CEO research workflow placed on signed quota hold: %s',snapshot['id'])
    return True


def ensure_research_session(config, snapshot, client):
    """CEO establishes the existing centrally capped session before Manager I/O."""
    cfg = allowed_config(config, snapshot["id"], snapshot)
    policy = json.loads(Path(config["policy"]).read_text())
    identity = "research-session-" + hashed(cfg["context"])[:48]
    payload = dict(context=cfg["context"], actor=config["actor_id"], role="ceo",
        identity=identity, request_sha256=hashed(cfg["context"]),
        attempt=hashed(dict(session=research_session(snapshot))),
        policy=policy, endpoint=policy["roles"]["ceo"]["endpoint"],
        model=policy["roles"]["ceo"]["model"])
    if client._request("POST", "/v1/inference/reservations", payload).get("reserved") is not True:
        raise ValueError("central research session denied")


def direct_research(config, snapshot, client, signed):
    """Signed CEO recommendation advances only this proposal's internal research."""
    assessment = signed["packet"]["assessment"]
    continuing = assessment["recommendation"] == "NEEDS_MORE_RESEARCH"
    now = datetime.now(timezone.utc)
    refs = [dict(ref=ref, sha256=sha) for ref, sha in snapshot["evidence"].items()
            if ref.startswith("preparation-")][-8:]
    command = dict(workflow_id=snapshot["id"],
        request_id="research-decision-" + hashed(dict(snapshot=snapshot, issued_at=now.isoformat()))[:48],
        actor_id="service-ceo", role="ceo", origin="control_plane",
        action="continue_research" if continuing else "research_disposition",
        revision=snapshot["revision"], previous_hash=hashed(snapshot),
        version=snapshot["version"], scope_hash=snapshot["scope_hash"],
        evidence=refs, payload=dict(round=len(research_rounds(snapshot))+int(continuing),
            objective=assessment["next_internal_task"],
            unanswered_question=assessment["evidence_gaps"], review=signed),
        issued_at=now.isoformat(), expires_at=(now+timedelta(minutes=5)).isoformat(), live=False)
    key = Ed25519PrivateKey.from_private_bytes(Path(config["signing_key"]).read_bytes())
    return client.apply(command, key.sign(canonical(command).encode()).hex())


def recover_legacy_worker(client, config, snapshot):
    """One append-only routing repair; concurrent polls use signed CAS lineage."""
    if (config["role"] != "ceo" or snapshot["state"] != "WORKER_PENDING"
            or snapshot["scope"]["worker_id"] != "service-worker"
            or snapshot.get("decomposition") is not None):
        return False
    allowed_config(config, snapshot["id"], snapshot)
    now = datetime.now(timezone.utc)
    command = dict(workflow_id=snapshot["id"],
        request_id="legacy-worker-recovery-" + hashed(snapshot)[:40],
        actor_id=config["actor_id"], role="ceo", origin="control_plane",
        action="recover_legacy_worker", revision=snapshot["revision"],
        previous_hash=hashed(snapshot), version=snapshot["version"],
        scope_hash=snapshot["scope_hash"],
        evidence=snapshot["last_command"]["evidence"],
        payload=dict(reason="Retired Worker routing repair within the exact approved research scope; Manager must propose A/B/C decomposition."),
        issued_at=now.isoformat(), expires_at=(now+timedelta(minutes=5)).isoformat(),
        live=False)
    key = Ed25519PrivateKey.from_private_bytes(Path(config["signing_key"]).read_bytes())
    result = client.apply(command, key.sign(canonical(command).encode()).hex())
    if result["state"] != "MANAGER_PENDING":
        raise ValueError("legacy Worker recovery not committed")
    return True


def poll(config, *, once=False, interval=12,worker_limit_override=None):
    if config["role"] not in STATES:
        raise ValueError("unsupported research role")
    client=HierarchyClient(config["endpoint"],ca_file=config["ca_file"],
        client_cert=config["client_cert"],client_key=config["client_key"])
    worker_limit=None
    if config['role']=='worker':
        policy=json.loads(Path(config['policy']).read_text())
        if policy.get('domain')!='worker-preparation-inference-v1':
            raise ValueError('pinned worker policy required')
        worker_limit=policy['maximum_requests']
    if config['role']=='ceo':
        if type(worker_limit_override) is not int or not 1<=worker_limit_override<=16:
            raise ValueError('bounded CEO worker-limit policy required')
    blocked=set()
    while True:
        from agents.ceo.deployment_pause import cycle
        with cycle(config) as admitted:
            try:
                tasks=client.research_list() if admitted else []
                if len(tasks)>30:
                    raise ValueError("bounded research queue required")
                for item in tasks:
                    flow=item["workflow_id"]
                    permitted=STATES[config['role']] | ({'WORKER_PENDING'} if config['role']=='ceo' else set())
                    if not RESEARCH_ID.fullmatch(flow) or item['state'] not in permitted:
                        continue
                    intent = None
                    try:
                        snapshot=client.read(flow)
                        if snapshot is None or snapshot["state"] != item["state"]:
                            continue
                        intent = (flow, hashed(snapshot))
                        if intent in blocked:
                            continue
                        if snapshot.get("research_disposition") is not None:
                            continue
                        if config['role']=='ceo' and snapshot['state']=='WORKER_PENDING':
                            if recover_legacy_worker(client, config, snapshot):
                                continue
                            hold_exhausted_research(client,config,snapshot,worker_limit_override)
                            continue
                        if config['role']=='ceo' and snapshot['state']=='MANAGER_PENDING':
                            ensure_research_session(config,snapshot,client)
                            continue
                        if config['role']=='ceo' and snapshot['state'] in ('HOLD','CEO_REVIEW','OWNER_REVIEW','CEO_REDIRECTION'):
                            from agents.ceo.ceo_research_review import review
                            signed=review(allowed_config(config,flow,snapshot),snapshot,client)
                            direct_research(config,snapshot,client,signed)
                            continue
                        if worker_limit is not None:
                            if research_session(snapshot) in blocked:
                                continue
                            if worker_submission_count(client,snapshot)>=worker_limit:
                                logging.warning('Worker research quota reached; no new calls: %s',flow)
                                blocked.add(research_session(snapshot))
                                continue
                        if config["role"] == "worker":
                            # Historical single-Worker research is immutable, and cannot be
                            # executed by A/B/C without a signed approved decomposition.
                            if not snapshot.get("decomposition"):
                                continue
                            from agents.ceo.hierarchy_runner import ready_assignment
                            if ready_assignment(snapshot, config["actor_id"]) is None:
                                continue
                        role_tick(allowed_config(config,flow,snapshot),once=True)
                    except Exception as exc:
                        # Isolate a refused venture so later approved tasks still poll.
                        # A changed signed snapshot is a new intent; never edit history.
                        if isinstance(exc, ValueError) and intent is not None:
                            blocked.add(intent)
                        logging.error("research workflow blocked role=%s workflow=%s snapshot=%s reason=%s next_action=%s",
                            config["role"], flow, intent[1] if intent else "unavailable",
                            (recovery_reason(exc) if recovery_reason(exc) != "RECONCILIATION_REQUIRED" else
                             "VALIDATION_OR_AUTHORITY_DENIED" if isinstance(exc, ValueError) else "READ_OR_TRANSPORT_UNAVAILABLE"),
                            "Inspect signed lineage, original session and reservation/execution proof; preserve identities and charges")
                        if once:
                            raise

            except Exception as exc:
                logging.exception("research role %s error: %s",config["role"],type(exc).__name__)
                if once:
                    raise
        if once:
            return
        time.sleep(interval)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--once",action="store_true")
    parser.add_argument("--worker-limit",type=int)
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text())
    poll(config,once=args.once,worker_limit_override=args.worker_limit)

if __name__=="__main__":
    main()

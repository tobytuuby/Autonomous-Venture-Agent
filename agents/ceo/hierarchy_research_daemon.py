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
from agents.ceo.venture_workflow import hashed

from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_service import run as role_tick

STATES = {"ceo":{"CEO_REVIEW","HOLD"},
          "manager":{"MANAGER_PENDING","MANAGER_REVIEW"},
          "worker":{"WORKER_PENDING"}}
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
    if snapshot["scope"]["manager_id"] != "service-manager" or snapshot["scope"]["worker_id"] != "service-worker":
        raise ValueError("research role scope denied")
    if snapshot["scope"]["budget_units"] > 5 or snapshot["scope"]["seed_cents"] != 1:
        raise ValueError("unapproved research budget")
    if not snapshot["handoff"]["item_id"] == flow or not snapshot["handoff"]["review"]["item_id"] == flow:
        raise ValueError("approved handoff missing")
    config=dict(base)
    config["workflow_id"]=flow
    original=Path(base["state_dir"])
    state=original.parent / "research" / flow
    if original.is_symlink() or state.is_symlink():
        raise ValueError("research state alias denied")
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    config["state_dir"]=str(state)
    if role in ("ceo","manager"):
        context=dict(base["context"])
        context.update(session_id=flow,venture_id=flow,
                       objective=snapshot["scope"]["tasks"][0],rounds=2)
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
            raise ValueError('research worker evidence scope mismatch')
        if evidence.get('role')=='worker' and evidence.get('action')=='submit':
            count+=1
    return count


def hold_exhausted_research(client,config,snapshot,worker_limit):
    """CEO signer records quota exhaustion; never infers, spends or funds."""
    if (config['role']!='ceo' or config['actor_id']!='service-ceo'
            or snapshot['state']!='WORKER_PENDING'
            or not RESEARCH_ID.fullmatch(snapshot['id'])
            or worker_submission_count(client,snapshot)<worker_limit):
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
        try:
            tasks=client.research_list()
            if len(tasks)>30:
                raise ValueError("bounded research queue required")
            for item in tasks:
                flow=item["workflow_id"]
                permitted=STATES[config['role']] | ({'WORKER_PENDING'} if config['role']=='ceo' else set())
                if not RESEARCH_ID.fullmatch(flow) or item['state'] not in permitted:
                    continue
                snapshot=client.read(flow)
                if snapshot is None or snapshot["state"] != item["state"]:
                    continue
                if config['role']=='ceo' and snapshot['state']=='WORKER_PENDING':
                    hold_exhausted_research(client,config,snapshot,worker_limit_override)
                    continue
                if config['role']=='ceo' and snapshot['state']=='HOLD':
                    from agents.ceo.ceo_research_review import review
                    review(config,snapshot,client)
                    continue
                if worker_limit is not None:
                    if flow in blocked:
                        continue
                    if worker_submission_count(client,snapshot)>=worker_limit:
                        logging.warning('Worker research quota reached; no new calls: %s',flow)
                        blocked.add(flow)
                        continue
                role_tick(allowed_config(config,flow,snapshot),once=True)
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

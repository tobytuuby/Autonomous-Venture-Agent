#!/usr/bin/env python3
"""CEO-signed owner-authorized technical-only hierarchy acceptance kickoff.

This is a single preproduction test fixture, not admission of a real venture.
The CEO's key never leaves its Control service account.
"""
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.escalation_inbox import canonical,digest
from agents.ceo.venture_workflow import hashed

PACKET = "Owner-authorized Level 2D PREPARATION_ONLY hierarchy verification; no venture launch."
ITEM="level2d-acceptance"
VENTURE="venture-verification"
FLOW="level2d-acceptance-1"
MANAGER="service-manager"
WORKER="service-worker"
CEO="service-ceo"
TASK=(
    "Create an internal tenant-isolation and recovery acceptance specification, "
    "with an initial Worker draft and a substantive Manager-requested correction "
    "covering rollback, restart and cross-tenant denial tests. Never execute or deploy."
)


def run(config):
    flow=config["workflow_id"]
    if flow not in ("level2d-acceptance-1", "level2d-acceptance-2",
                     "level2d-acceptance-3", "level2d-acceptance-4"):
        raise ValueError("bounded technical fixture only")
    item={"level2d-acceptance-1": ITEM,
          "level2d-acceptance-2": "level2d-acceptance-retry",
          "level2d-acceptance-3": "level2d-acceptance-retry2",
          "level2d-acceptance-4": "level2d-acceptance-retry3"}[flow]
    c=HierarchyClient(config["endpoint"],ca_file=config["ca_file"],
        client_cert=config["client_cert"],client_key=config["client_key"])
    if c.read(flow) is not None:
        print("hierarchy-technical-test-already-created")
        return
    key=Ed25519PrivateKey.from_private_bytes(Path(config["signing_key"]).read_bytes())
    def sign(obj):
        return key.sign(canonical(obj).encode()).hex()
    issued=datetime.now(timezone.utc)-timedelta(seconds=10)
    expires=issued+timedelta(hours=1)
    times=dict(issued_at=issued.isoformat(),expires_at=expires.isoformat())
    review=dict(item_id=item,packet_hash=digest(PACKET.encode()),disposition="HANDOFF",
        summary="Owner-authorized technical preparation only; no external activity.",
        manager_id=MANAGER,instructions=[TASK],owner_action=None,scope="PREPARATION_ONLY")
    receipt=dict(venture_id=VENTURE,item_id=item,packet_hash=review["packet_hash"],
        review_hash=hashed(review),manager_id=MANAGER,decision="HANDOFF",
        scope="PREPARATION_ONLY",ceo_id=CEO,
        decision_reference="owner-authorized-level2d-technical-test",**times)
    handoff=c.bootstrap_prepare(dict(packet=PACKET,review=review,receipt=receipt,
                                      receipt_signature=sign(receipt)))
    scope=dict(mode="PREPARATION_ONLY",manager_id=MANAGER,worker_id=WORKER,
        tasks=[TASK],budget_units=5,seed_cents=10000)
    cmd=dict(workflow_id=flow,request_id="ceo-"+flow+"-create",
        actor_id=CEO,role="ceo",origin="control_plane",action="create",
        revision=0,previous_hash="GENESIS",version=1,
        scope_hash=hashed(scope),evidence=[dict(ref="owner-level2d-preparation",
            sha256=digest(PACKET.encode()))],
        payload=dict(venture_id=VENTURE,scope=scope,handoff_hash=hashed(handoff)),
        issued_at=datetime.now(timezone.utc).isoformat(),
        expires_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(),live=False)
    result=c.bootstrap_commit(cmd,sign(cmd))
    policy=json.loads(Path(config["policy"]).read_text())
    context=config["context"]
    if context["session_id"]!=flow or context["venture_id"]!=VENTURE:
        raise ValueError("CEO bounded technical session required")
    # CEO establishes the Control-owned inference session; this reserves one
    # model-budget slot without making a provider call. Manager cannot bootstrap.
    reservation=dict(context=context,actor=CEO,role="ceo",
        identity="ceo-level2d-technical-bootstrap",
        request_sha256=digest(PACKET.encode()),
        attempt=digest((flow+"-standing-bootstrap").encode()),
        policy=policy,endpoint=policy["roles"]["ceo"]["endpoint"],
        model=policy["roles"]["ceo"]["model"])
    receipt_budget=c._request("POST","/v1/inference/reservations",reservation)
    if receipt_budget.get("reserved") is not True:
        raise ValueError("central CEO session bootstrap denied")
    print(json.dumps(dict(workflow_id=flow,state=result["state"],
        central_session_reserved=True,owner_approval=False,operational_authority=False)))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    cfg=json.loads(Path(parser.parse_args().config).read_text())
    run(cfg)

"""CEO-owned, digest-bound kickoff of Owner-approved preparation-only research."""
import argparse
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.escalation_inbox import canonical,digest
from agents.ceo.venture_workflow import hashed
from agents.ceo.owner_idea_inbox import digest as proposal_digest

def kickoff(config,feedback):
    if (feedback.get("domain")!="owner-idea-research-feedback-v1"
            or feedback.get("advisory_only") is not True
            or feedback.get("venture_admission") is not False
            or feedback.get("financial_authority") is not False):
        raise ValueError("untrusted feedback")
    if config["role"]!="ceo" or config["actor_id"]!="service-ceo":
        raise ValueError("CEO signer required")
    client=HierarchyClient(config["endpoint"],ca_file=config["ca_file"],
        client_cert=config["client_cert"],client_key=config["client_key"])
    key=Ed25519PrivateKey.from_private_bytes(Path(config["signing_key"]).read_bytes())
    signer=lambda obj: key.sign(canonical(obj).encode()).hex()
    policy=json.loads(Path(config["policy"]).read_text())
    results=[]
    for entry in feedback["research_assignments"]:
        fingerprint=entry["proposal_digest"]
        cycle=entry["cycle_id"]
        if (entry["scope"]!="INTERNAL_RESEARCH_ONLY" or entry["status"]!="APPROVED_NOT_ASSIGNED"
                or proposal_digest(entry["proposal"])!=fingerprint
                or not any(r["cycle_id"]==cycle and r["proposal_digest"]==fingerprint
                        and r["decision"]=="APPROVE_FOR_RESEARCH" for r in feedback["records"])):
            raise ValueError("Owner decision/proposal mismatch")
        flow="research-"+fingerprint[:24]
        current=client.read(flow)
        if current is not None:
            results.append(dict(workflow_id=flow,state=current["state"],already_exists=True))
            continue
        now=datetime.now(timezone.utc)
        receipt=dict(venture_id=flow,item_id=flow,manager_id="service-manager",
            decision="HANDOFF",scope="PREPARATION_ONLY",ceo_id="service-ceo",
            decision_reference="owner-research-"+fingerprint[:24],
            issued_at=now.isoformat(),expires_at=(now+timedelta(hours=1)).isoformat())
        # Derive the complete CEO receipt using the proposal-bound broker contract.
        proposal=entry["proposal"]
        task=("Internal research only. Venture: "+proposal["title"][:70]+
              ". Target: "+proposal["customer"][:70]+
              ". Problem: "+proposal["problem"][:85]+
              ". Solution: "+proposal["solution"][:85]+
              ". Validation: "+proposal["validation_plan"][:135]+
              ". Flag unverified assumptions; no outreach, launch or spending.")
        packet=canonical(dict(domain="owner-research-task-v1",approval=entry))
        review=dict(item_id=flow,packet_hash=digest(packet.encode()),disposition="HANDOFF",
            summary="Owner-approved internal research only: "+proposal["title"],
            manager_id="service-manager",instructions=[task],owner_action=None,
            scope="PREPARATION_ONLY")
        receipt.update(packet_hash=review["packet_hash"],review_hash=hashed(review))
        handoff=client.bootstrap_prepare(dict(cycle_id=cycle,proposal_digest=fingerprint,
            receipt=receipt,receipt_signature=signer(receipt)))
        scope=dict(mode="PREPARATION_ONLY",manager_id="service-manager",
                   worker_id="service-worker",tasks=handoff["review"]["instructions"],
                   budget_units=5,seed_cents=1)
        created=datetime.now(timezone.utc)
        command=dict(workflow_id=flow,request_id="research-create-"+fingerprint[:24],
            actor_id="service-ceo",role="ceo",origin="control_plane",action="create",
            revision=0,previous_hash="GENESIS",version=1,scope_hash=hashed(scope),
            evidence=[dict(ref="research-approval-"+fingerprint[:24],sha256=fingerprint)],
            payload=dict(venture_id=flow,scope=scope,handoff_hash=hashed(handoff)),
            issued_at=created.isoformat(),
            expires_at=(created+timedelta(minutes=5)).isoformat(),live=False)
        state=client.bootstrap_commit(command,signer(command))
        context=dict(config["context"])
        context.update(session_id=flow,venture_id=flow,
                       objective=task,rounds=2)
        reservation=dict(context=context,actor="service-ceo",role="ceo",
            identity="ceo-research-bootstrap-"+fingerprint[:20],
            request_sha256=digest(packet.encode()),
            attempt=digest((flow+"-standing-bootstrap").encode()),
            policy=policy,endpoint=policy["roles"]["ceo"]["endpoint"],
            model=policy["roles"]["ceo"]["model"])
        budget=client._request("POST","/v1/inference/reservations",reservation)
        if budget.get("reserved") is not True:
            raise ValueError("CEO research quota session denied")
        results.append(dict(workflow_id=flow,state=state["state"],already_exists=False))
    return results

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--feedback",required=True)
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text())
    feedback=json.loads(Path(args.feedback).read_text())
    print(canonical(kickoff(config,feedback)))

if __name__=="__main__":
    main()

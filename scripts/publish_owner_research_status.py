"""Publish signed, durable internal-research progress for the Owner dashboard.

This is a read-only broker observation. Reports can never authorize funding,
admission, launch or external business operations.
"""
import argparse
import hashlib
import json
import os
import pathlib
import pwd
import tempfile
from datetime import datetime, timezone

from agents.ceo.escalation_inbox import canonical
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.owner_idea_inbox import digest as proposal_digest

STATUS = {
    "MANAGER_PENDING": "QUEUED",
    "WORKER_PENDING": "RESEARCHING",
    "MANAGER_REVIEW": "MANAGER_REVIEW",
    "CEO_REVIEW": "CEO_REVIEW",
    "OWNER_REVIEW": "INTERNAL_ASSESSMENT_COMPLETE",
    "BUDGET_EXHAUSTED": "BLOCKED",
    "HOLD": "BLOCKED",
    "SECURITY_HOLD": "BLOCKED",
    "CEO_REDIRECTION": "NEEDS_REVISION",
    "TERMINATED": "STOPPED",
}


def collect(config, feedback, client=None, worker_limit=None, ceo_review_dir=None, ceo_public_key=None):
    if (feedback.get("domain") != "owner-idea-research-feedback-v1"
            or feedback.get("advisory_only") is not True
            or feedback.get("venture_admission") is not False
            or feedback.get("financial_authority") is not False):
        raise ValueError("bounded Owner feedback required")
    if client is None:
        client=HierarchyClient(config["endpoint"],ca_file=config["ca_file"],
            client_cert=config["client_cert"],client_key=config["client_key"])
    listing={x["workflow_id"]:x["state"] for x in client.research_list()}
    output=[]
    for approval in feedback.get("research_assignments",[]):
        cycle=approval["cycle_id"]
        fingerprint=approval["proposal_digest"]
        if proposal_digest(approval["proposal"]) != fingerprint or not any(
                x.get("cycle_id")==cycle and x.get("proposal_digest")==fingerprint
                and x.get("decision")=="APPROVE_FOR_RESEARCH" for x in feedback["records"]):
            raise ValueError("changed or missing Owner approval")
        flow="research-"+fingerprint[:24]
        item=dict(cycle_id=cycle,proposal_digest=fingerprint,workflow_id=flow,
            title=approval["proposal"]["title"],state="NOT_ADMITTED",
            research_status="APPROVED_NOT_ASSIGNED",independent_market_evidence=False,
            artifacts=[])
        if flow in listing:
            state=client.read(flow)
            if (state is None or state["id"]!=flow or state["venture_id"]!=flow
                    or state["state"]!=listing[flow]
                    or state["mode"]!="PREPARATION_ONLY"
                    or any(state[k] is not False for k in (
                        "operational_authority","external_actions_allowed",
                        "execution_performed","money_released"))
                    or state["scope"]["seed_cents"]!=1
                    or state["handoff"]["item_id"]!=flow
                    or state["handoff"]["review"]["item_id"]!=flow):
                raise ValueError("research workflow provenance mismatch")
            item["state"]=state["state"]
            item["research_status"]=STATUS.get(state["state"],"BLOCKED")
            item["revision"]=state["revision"]
            if state['state'] in ('HOLD','SECURITY_HOLD','BUDGET_EXHAUSTED','CEO_REDIRECTION'):
                reason=state.get('last_command',{}).get('payload',{}).get('reason')
                if type(reason) is str and reason:
                    item['blocking_reason']=reason[:500]
            for ref, sha in list(state["evidence"].items())[-12:]:
                if not ref.startswith("preparation-") or not ref.endswith(sha):
                    continue
                raw=client.load(ref)
                if hashlib.sha256(raw).hexdigest()!=sha:
                    raise ValueError("signed artifact digest mismatch")
                doc=json.loads(raw)
                if doc.get("scope_hash")!=state["scope_hash"]:
                    raise ValueError("scope mismatch in worker evidence")
                item["artifacts"].append(dict(role=doc["role"],action=doc["action"],
                    deliverable=doc["deliverable"],explanation=doc["explanation"],
                    revision=doc["revision"]))
            worker_submissions=sum(a['role']=='worker' and a['action']=='submit'
                                   for a in item['artifacts'])
            if ceo_review_dir is not None and state['state']=='HOLD':
                path=pathlib.Path(ceo_review_dir)/(flow+'.json')
                if path.is_file() and not path.is_symlink():
                    if path.stat().st_size>16000 or ceo_public_key is None:
                        raise ValueError('bounded signed CEO review required')
                    outcome=json.loads(path.read_text())
                    if outcome.get('state')=='COMPLETE':
                        from agents.ceo.venture_workflow import hashed
                        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                        packet=outcome['packet']
                        if (packet.get('domain')!='owner-internal-research-ceo-review-v1'
                                or packet.get('workflow_id')!=flow
                                or packet.get('snapshot_hash')!=hashed(state)
                                or packet.get('model')!='gpt-6-sol'
                                or packet.get('financial_authority') is not False
                                or packet.get('venture_admission') is not False
                                or packet.get('external_market_evidence_verified') is not False):
                            raise ValueError('CEO assessment authorization mismatch')
                        Ed25519PublicKey.from_public_bytes(ceo_public_key).verify(
                            bytes.fromhex(outcome['signature']),canonical(packet).encode())
                        item['ceo_review']=packet['assessment']
                        item['ceo_reviewed_utc']=packet['reviewed_utc']
                        item['research_status']='CEO_ASSESSMENT_COMPLETE'
            if (state['state']=='WORKER_PENDING' and worker_limit is not None
                    and worker_submissions>=worker_limit):
                item['research_status']='BLOCKED_WORKER_QUOTA'
                item['blocking_reason']='Worker inference limit reached; manager did not approve the desk assessment. CEO scope correction is required.'
        output.append(item)
    return dict(domain="owner-research-progress-v1",advisory_only=True,
                financial_authority=False,venture_admission=False,
                generated_utc=datetime.now(timezone.utc).isoformat(),records=output)


def write_atomic(value, destination):
    dest=pathlib.Path(destination)
    if not dest.parent.is_dir() or dest.is_symlink():
        raise ValueError("safe Owner inbox directory required")
    fd,name=tempfile.mkstemp(prefix=".research-progress-",dir=dest.parent)
    try:
        with os.fdopen(fd,"wb") as file:
            file.write((canonical(value)+"\n").encode())
            file.flush()
            os.fsync(file.fileno())
        os.chmod(name,0o600)
        owner=pwd.getpwnam("venture-review")
        os.chown(name,owner.pw_uid,owner.pw_gid)
        os.replace(name,dest)
        dfd=os.open(dest.parent,os.O_RDONLY | os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--feedback",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--worker-policy",required=True)
    p.add_argument('--ceo-reviews',required=True)
    p.add_argument('--trust',required=True)
    args=p.parse_args()
    policy=json.loads(pathlib.Path(args.worker_policy).read_text())
    if policy.get('domain')!='worker-preparation-inference-v1' or policy.get('enabled') is not True:
        raise ValueError('bounded Worker policy required')
    limit=policy['maximum_requests']
    if type(limit) is not int or not 1<=limit<=16:
        raise ValueError('invalid worker inference limit')
    trust=json.loads(pathlib.Path(args.trust).read_text())
    signer=trust['actors']['service-ceo']
    if signer['role']!='ceo':
        raise ValueError('CEO pinned public key required')
    result=collect(json.loads(pathlib.Path(args.config).read_text()),
                   json.loads(pathlib.Path(args.feedback).read_text()),worker_limit=limit,
                   ceo_review_dir=args.ceo_reviews,ceo_public_key=bytes.fromhex(signer['public_key']))
    write_atomic(result,args.out)
    print("published owner research statuses",[(x["title"],x["research_status"]) for x in result["records"]])

if __name__=="__main__":
    main()

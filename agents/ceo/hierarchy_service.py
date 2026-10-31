"""Independent, role-scoped preparation worker/manager/CEO service.

Uses broker mTLS, role-specific signing key, bounded provider and durable
artifact journal. The CEO alone may advance to OWNER_REVIEW; this service never
invokes owner approval, finance, launch or external operations.
"""
import argparse
import json
import os
from pathlib import Path
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from agents.ceo.control_plane import load_trust
from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_runner import HierarchyRunner
from agents.ceo.hierarchy_model_callbacks import ModelRoleCallback
from agents.ceo.hierarchy_providers import HierarchyProvider


class RemoteWorkflow:
    def __init__(self, client, actors):
        self.client, self.actors=client, actors
    def read(self, workflow_id):
        state=self.client.read(workflow_id)
        if state is None:
            raise KeyError(workflow_id)
        return state
    def apply(self, command, signature):
        return self.client.apply(command, signature)


def run(config, *, once=False, poll_seconds=3):
    role=config["role"]
    if role not in ("ceo","manager","worker"):
        raise ValueError("hierarchy role denied")
    actor=config["actor_id"]
    actors=load_trust(config["trust"])
    if actor not in actors or actors[actor][0]!=role:
        raise ValueError("role trust denied")
    seed=Path(config["signing_key"]).read_bytes()
    if len(seed)!=32:
        raise ValueError("private role signer required")
    private=Ed25519PrivateKey.from_private_bytes(seed)
    public=private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    if public!=actors[actor][1]:
        raise ValueError("signer does not match pinned role")
    client=HierarchyClient(config["endpoint"],ca_file=config["ca_file"],
        client_cert=config["client_cert"],client_key=config["client_key"])
    state_dir=Path(config["state_dir"])
    if not state_dir.is_dir() or state_dir.is_symlink():
        raise ValueError("preprovisioned state required")
    policy=json.loads(Path(config["policy"]).read_text())
    local=None
    if role=="ceo":
        from agents.ceo.venture_exercise import configured_provider
        local=configured_provider(os.environ,required=True)
        if local.model!="gpt-6-sol":
            raise ValueError("CEO pinned reasoning model denied")
        local.trace_path=state_dir/"provider.jsonl"
    elif role=="manager" and policy["roles"]["manager"]["model"]!="gpt-6-sol":
        raise ValueError("Manager reasoning model denied")
    elif role=="worker" and policy["model"]!="gpt-6-luna":
        raise ValueError("Worker specialized model denied")
    provider=HierarchyProvider(role=role,actor=actor,
        workflow_id=config["workflow_id"],client=client,policy=policy,
        context=config.get("context"),local_provider=local,
        state_path=state_dir/"inference.sqlite")
    callback=ModelRoleCallback(role=role,provider=provider,
        artifact_store=client.store,artifact_load=client.load,actor_id=actor,
        decomposition_workers=config.get("decomposition_workers"))
    callbacks=dict(manager=None,worker=None,ceo=None)
    callbacks[role]=callback
    workflow=RemoteWorkflow(client,actors)
    runner=HierarchyRunner(workflow,**callbacks,role_filter=role,
        signers={actor:private.sign})
    allowed=dict(ceo={"CEO_REVIEW","DECOMPOSITION_REVIEW"},manager={"MANAGER_PENDING","MANAGER_REVIEW"},
                 worker={"WORKER_PENDING"})[role]
    last=None
    while True:
        try:
            state=client.read(config["workflow_id"])
            if state is not None and state["state"] in allowed:
                after=runner.tick(config["workflow_id"])
                print(json.dumps(dict(role=role,from_state=state["state"],
                      to_state=after["state"],revision=after["revision"],
                      operational_authority=False)),flush=True)
            elif state is not None and state["state"]=="OWNER_REVIEW" and role=="ceo":
                print(json.dumps(dict(role=role,status="OWNER_REVIEW_ONLY",
                      operational_authority=False)),flush=True)
                return 0
            elif last != ("waiting",state["state"] if state else None):
                last=("waiting",state["state"] if state else None)
                print(json.dumps(dict(role=role,status="WAITING",
                    workflow_state=last[1],operational_authority=False)),flush=True)
        except KeyError:
            pass
        if once:
            return 0
        time.sleep(poll_seconds)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True)
    parser.add_argument("--once",action="store_true")
    args=parser.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    return run(cfg,once=args.once)


if __name__=="__main__":
    raise SystemExit(main())

"""Autonomous, role-isolated poller for Owner-approved internal research workflows.

Uses the existing pinned hierarchy mTLS broker, role signer and provider budget
governor. This is preparation-only: no tools, money or customer operations.
"""
import argparse
import json
import logging
import re
import time
from pathlib import Path

from agents.ceo.hierarchy_client import HierarchyClient
from agents.ceo.hierarchy_service import run as role_tick

STATES = {"ceo":{"CEO_REVIEW"},
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


def poll(config, *, once=False, interval=12):
    if config["role"] not in STATES:
        raise ValueError("unsupported research role")
    client=HierarchyClient(config["endpoint"],ca_file=config["ca_file"],
        client_cert=config["client_cert"],client_key=config["client_key"])
    while True:
        try:
            tasks=client.research_list()
            if len(tasks)>30:
                raise ValueError("bounded research queue required")
            for item in tasks:
                flow=item["workflow_id"]
                if not RESEARCH_ID.fullmatch(flow) or item["state"] not in STATES[config["role"]]:
                    continue
                snapshot=client.read(flow)
                if snapshot is None or snapshot["state"] != item["state"]:
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
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text())
    poll(config,once=args.once)

if __name__=="__main__":
    main()

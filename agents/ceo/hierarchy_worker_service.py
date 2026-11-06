"""Bounded deployment entrypoint for the existing Worker hierarchy service."""
import argparse
import json
import os
import stat
from agents.ceo.escalation_inbox import inside_root
from agents.ceo.hierarchy_service import run
from agents.ceo.role_maintenance import configured_gate

FIELDS = {"role", "actor_id", "workflow_id", "endpoint", "trust", "signing_key",
          "client_cert", "client_key", "ca_file", "state_dir", "policy"}


def load_config(path):
    path = inside_root(path)
    if path.stat().st_size > 16000:
        raise ValueError("bounded config required")
    config = json.loads(path.read_text())
    if set(config) not in (FIELDS, FIELDS | {"maintenance_admission"}) or config["role"] != "worker":
        raise ValueError("Worker-only config required")
    configured_gate(config)
    if config["actor_id"] != "service-worker" or config["workflow_id"] != "level2d-acceptance-1":
        raise ValueError("technical fixture identity required")
    if "REPLACE-" in config["endpoint"]:
        raise ValueError("existing verified broker endpoint required")
    for field in ("trust", "signing_key", "client_cert", "client_key", "ca_file", "state_dir", "policy"):
        config[field] = str(inside_root(config[field]))
    for field in ("signing_key", "client_key"):
        info = os.stat(config[field])
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("private Worker credential ownership required")
    policy_path = inside_root(config["policy"])
    if policy_path.stat().st_size > 16000:
        raise ValueError("bounded policy required")
    policy = json.loads(policy_path.read_text())
    from pathlib import Path
    expected = json.loads((Path(__file__).resolve().parents[2] /
        "infrastructure/level2d-worker-policy.json").read_text())
    if policy != expected:
        raise ValueError("bounded Worker policy required")
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    return run(load_config(args.config), once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())

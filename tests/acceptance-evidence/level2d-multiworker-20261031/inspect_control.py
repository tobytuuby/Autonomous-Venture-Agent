#!/usr/bin/env python3
"""Read-only Control service inspection. Prints allowlisted non-secret fields only.

Run from the approved project root via the venture-control bridge:
sudo -n python3 tests/acceptance-evidence/level2d-multiworker-20261031/inspect_control.py
No provider, signer, database or network request is invoked.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

PROJECT = Path("/home/epsilon/venture-control-workspace")
assert Path.cwd().resolve() == PROJECT
def run(*args):
    return subprocess.check_output(args, text=True).strip()
def sha(data):
    return hashlib.sha256(data).hexdigest()
def unit_info(unit):
    fields = ("Id", "ActiveState", "SubState", "User", "WorkingDirectory",
              "MainPID", "ExecMainStartTimestamp", "EnvironmentFiles")
    output = run("systemctl", "show", unit, *["--property=" + k for k in fields])
    return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
unit = "venture-control-broker-mtls.service"
service = unit_info(unit)
assert service["ActiveState"] == "active"
pid = service["MainPID"]
# Never print the complete environment or credential values.
env = dict(entry.split("=", 1) for entry in
           Path("/proc", pid, "environ").read_bytes().decode().split("\0") if "=" in entry)
allow = ("VENTURE_BROKER_HIERARCHY_ENABLED", "VENTURE_BROKER_WORKER_INFERENCE_ENABLED",
         "VENTURE_BROKER_RESERVATION_ACTOR", "VENTURE_BROKER_CEO_RESERVATION_ACTOR")
trust_path = Path(env["VENTURE_BROKER_HIERARCHY_TRUST"])
trust_raw = trust_path.read_bytes()
trust = json.loads(trust_raw)["actors"]
actors = {actor: value["role"] for actor, value in trust.items()}
root = Path(service["WorkingDirectory"])
paths = {
    "kernel/broker/mtls_server.py": [(90, 112)],
    "kernel/broker/isolated_mtls.py": [(51, 66)],
    "agents/ceo/worker_inference.py": [(15, 33), (42, 62), (72, 108)],
    "agents/ceo/hierarchy_gateway.py": [(182, 209)],
    "agents/ceo/hierarchy_runner.py": [(15, 26), (82, 96)],
}
sources = {}
for rel, ranges in paths.items():
    raw = (root / rel).read_bytes()
    lines = raw.decode().splitlines()
    sources[rel] = dict(sha256=sha(raw), local_checkout_sha256=sha((PROJECT / rel).read_bytes()),
        excerpts=[dict(line=n, text=lines[n-1]) for start, end in ranges
                  for n in range(start, min(end, len(lines)) + 1)])
policy_path = root / "artifacts/preparation-authority/worker-inference-policy.json"
policy_raw = policy_path.read_bytes()
policy = json.loads(policy_raw)
policy_fields = ("actor_id", "domain", "enabled", "epoch", "maximum_output_tokens",
                 "maximum_requests", "model")
ceo_unit = unit_info("venture-level2d-ceo.service")
ceo_path = Path(ceo_unit["WorkingDirectory"]) / "artifacts/level2c-ceo/hierarchy-config.json"
ceo_raw = ceo_path.read_bytes()
ceo = json.loads(ceo_raw)
tracked_dirty = run("git", "diff", "--name-only", "HEAD").splitlines()
result = dict(
    schema="level2d-multiworker-preflight-v1",
    observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    classification="operator-observed-live-control-configuration-and-on-disk-source",
    verdict="BLOCKED",
    journey_executed=False,
    project_head=run("git", "rev-parse", "HEAD"),
    branch=run("git", "branch", "--show-current"),
    dirty_tracked_sha256={p: sha((PROJECT / p).read_bytes()) for p in tracked_dirty},
    service=service,
    settings={k: env.get(k) for k in allow},
    worker_pin_count=len(list(filter(None, env.get("VENTURE_BROKER_WORKER_PINS", "").split(",")))),
    trust=dict(path=str(trust_path), sha256=sha(trust_raw), actors=actors),
    worker_policy=dict(path=str(policy_path), sha256=sha(policy_raw),
                       fields={k: policy[k] for k in policy_fields},
                       endpoint_host=urlsplit(policy["endpoint"]).hostname),
    ceo_service=ceo_unit,
    ceo_config=dict(sha256=sha(ceo_raw), fields={k: ceo.get(k) for k in
                    ("role", "actor_id", "workflow_id", "decomposition_workers")}),
    sources=sources,
    blockers=[
        "Pinned hierarchy trust has only one Worker actor; three distinct authorized live Workers are unavailable.",
        "Deployed Worker reservation and execution closures bind every Worker TLS pin to service-worker.",
        "One actor_id policy must equal the hard-coded actor before signed assignment authorization.",
        "Technical bootstrap permits only level2d-acceptance-1 through -5; the new fixture ID is denied.",
    ],
    limitations=[
        "No Agents VM service or credential inspection was needed after the Control prerequisite failed.",
        "Source hashes identify files on disk, not proof of exact Python bytecode loaded in the running process.",
        "Two TLS pins do not demonstrate two actors; the broker routes both through one Worker role and actor.",
        "No inference, signed command, audit transition, provider receipt, live denial probe or restart was performed.",
    ])
# Guard against service replacement during the observation.
assert unit_info(unit)["MainPID"] == pid
print(json.dumps(result, indent=2, sort_keys=True))

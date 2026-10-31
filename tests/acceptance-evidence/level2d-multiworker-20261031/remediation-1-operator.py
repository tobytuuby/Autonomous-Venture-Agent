#!/usr/bin/env python3
"""Operator-only candidate preparation. No service/config installation or inference."""
import hashlib, json, os
from pathlib import Path
ROOT = Path("/home/epsilon/venture-agents-workspace")
FLOW = "level2d-multiworker-remediation-1"
assert Path.cwd().resolve() == ROOT, "run only from approved Agents project"
if os.geteuid() != 0:
    raise SystemExit("STOP: operator root required; do not bypass no-new-privileges")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
path = Path("/var/lib/venture-manager/level2d/hierarchy-config.json")
cfg = json.loads(path.read_text())
assert cfg["role"] == "manager" and cfg["actor_id"] == "service-manager"
for name in ("a", "b", "c"):
    worker = json.loads(Path("/var/lib/venture-worker-"+name+"/level2d/hierarchy-config.json").read_text())
    assert worker["actor_id"] == "worker-"+name and worker["role"] == "worker"
    assert worker["workflow_id"] == FLOW, "unexpected Worker workflow: stop"
    policy = json.loads(Path(worker["policy"]).read_text())
    assert policy["model"] == "gpt-6-luna" and policy["maximum_requests"] <= 4
candidate = dict(cfg, workflow_id=FLOW,
                 decomposition_workers=dict(A="worker-a", B="worker-b", C="worker-c"))
if "context" in candidate:
    candidate["context"] = dict(candidate["context"], session_id=FLOW)
# Preserve credentials by reference only. This candidate remains root-only.
out = ROOT / "artifacts/level2d-multiworker-remediation-1-operator"
out.mkdir(mode=0o700, exist_ok=False)
os.chmod(out, 0o700)
target = out / "manager-candidate.json"
with target.open("x") as f: json.dump(candidate, f, indent=2); f.write("\n")
os.chmod(target, 0o600)
report = dict(source_sha256=sha(path), candidate_sha256=sha(target),
              workflow_id=FLOW, decomposition_workers=candidate["decomposition_workers"],
              installed=False, restarted=False, provider_calls=0,
              next_gate="Review Control fixture budget 12 (range 10-15), assignment limit 4 and shared ceiling; reconcile CEO/Manager model pin before installation/kickoff")
print(json.dumps(report, sort_keys=True))

"""Reproduce sanitized readiness inspection; root reads service files, no inference.
Run from the approved project root. Never outputs secret values or secret hashes.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd
import shlex
import stat
import subprocess
import sys

ROOT = Path("/home/epsilon/venture-control-workspace")
if Path.cwd().resolve() != ROOT or os.geteuid() != 0:
    raise SystemExit("Run as trusted operator from approved root")
sys.path.insert(0, str(ROOT))
from agents.ceo.authenticated_handoff import read_source

def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)

emit({"head": subprocess.check_output(["git", "-c", "safe.directory=" + str(ROOT),
      "rev-parse", "HEAD"], text=True).strip(), "inspection_only": True})
for name in ("artifacts/authenticated-handoff/ingress/trust.json",
             "artifacts/preparation-control/trust.json"):
    path = ROOT / name
    data = json.loads(path.read_text())
    emit({"path": name, "actor_count": len(data["actors"]),
          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
for name in ("artifacts/authenticated-handoff/state/status.json",
             "artifacts/scheduled-ceo/status.json"):
    data = json.loads((ROOT / name).read_text())
    emit({"path": name, "status": data.get("status"), "reason": data.get("reason"),
          "escalation": data.get("escalation")})
source = read_source(ROOT / "artifacts/scheduled-ceo")
emit({"verified_source": {k: source[k] for k in
      ("id", "status", "packet_hash", "review_source")},
      "review_present": source["review"] is not None,
      "decision_present": source["decision"] is not None})
for name in ("artifacts/authenticated-handoff/ingress/authorization.json",
             "artifacts/authenticated-handoff/state/authorization.json",
             "artifacts/scheduled-ceo/escalation.attempt.json"):
    emit({"path": name, "exists": (ROOT / name).exists()})
# The installed lanes have no CLI grant/key paths. Report only matching file names
# in their configured private directories, never content or private-key hashes.
for relative in ("artifacts/authenticated-handoff/ingress", "artifacts/scheduled-ceo"):
    emit({"directory": relative, "grant_or_operator_pin_files": sorted(
        p.name for p in (ROOT / relative).iterdir()
        if any(term in p.name.lower() for term in ("grant", "operator", "allowance")))})
env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
       "PYTHONDONTWRITEBYTECODE": "1"}
allowed = {"CEO_MODEL_ENDPOINT", "CEO_MODEL_NAME", "CEO_MODEL_TOKEN"}
for name in ("/etc/venture-ceo.env", "/etc/venture-ceo-shadow.env"):
    path = Path(name)
    info = path.lstat()
    secure = (stat.S_ISREG(info.st_mode) and info.st_uid == 0
              and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1)
    emit({"environment_file": name, "uid": info.st_uid, "gid": info.st_gid,
          "mode": oct(stat.S_IMODE(info.st_mode)), "secure_regular_file": secure})
    if not secure:
        raise SystemExit("Secure environment file required")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep and key in allowed:
            values = shlex.split(value, comments=False)
            if len(values) != 1:
                raise SystemExit("Unsupported service environment syntax")
            env[key] = values[0]
env["CEO_KERNEL_GATE_FILE"] = str(ROOT / "infrastructure/venture-ceo-kernel-gate.runtime.json")
account = pwd.getpwnam("venture-ceo")
# Pass credentials only in the child environment, never argv, files or reports.
probe = """
import json, os
from agents.ceo.venture_exercise import configured_provider
from agents.ceo.provider_dispatch import runtime_manifest
result = dict(uid=os.getuid(), service_account='venture-ceo',
    inference_requests=0, environment_present={k: bool(os.environ.get(k)) for k in
    ('CEO_MODEL_ENDPOINT','CEO_MODEL_NAME','CEO_MODEL_TOKEN','CEO_KERNEL_GATE_FILE')})
try:
    configured_provider(dict(os.environ), required=True)
    result['provider_configuration_and_gate'] = 'VALID_CONFIGURATION_ONLY'
except Exception as exc:
    result['provider_configuration_and_gate'] = 'BLOCKED'
    result['error_class'] = type(exc).__name__
try:
    result['runtime_dependency_count'] = len(runtime_manifest())
    result['runtime_boundary'] = 'VALID_LOCAL_FILES_ONLY'
except Exception as exc:
    result['runtime_boundary'] = 'BLOCKED'
    result['runtime_error_class'] = type(exc).__name__
print(json.dumps(result, sort_keys=True))
"""
result = subprocess.run(["/usr/bin/python3", "-B", "-c", probe], cwd=ROOT, env=env,
    user=account.pw_uid, group=account.pw_gid, extra_groups=[], capture_output=True, text=True)
if result.returncode:
    emit({"service_preflight": "FAILED", "exit_code": result.returncode})
else:
    emit(json.loads(result.stdout))
emit({"decision": "BLOCKED_EXTERNAL_SIGNED_PREREQUISITES",
      "new_identity_generated": False, "trust_changed": False,
      "inference_requests": 0, "production_ceo_attached": False,
      "owner_approval_created": False, "live_authority_changed": False})

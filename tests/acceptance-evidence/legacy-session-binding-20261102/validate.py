"""Validate only the three scoped source changes over the inspected HEAD."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

root = Path.cwd()
out = root / "tests/acceptance-evidence/legacy-session-binding-20261102"
clean = root / "artifacts/legacy-session-binding-20261102/clean"
clean.mkdir(parents=True, exist_ok=True)
archive = clean.parent / "head.tar"
with archive.open("wb") as stream:
    subprocess.run(["git", "archive", "HEAD"], stdout=stream, check=True)
subprocess.run(["tar", "-xf", str(archive), "-C", str(clean)], check=True)
files = ["agents/ceo/hierarchy_research_daemon.py",
         "tests/test_research_abc_routing.py", "tests/test_level2c_central_roles.py"]
for name in files:
    shutil.copyfile(root / name, clean / name)
(clean / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
(out / "source-sha256.json").write_text(json.dumps({
    name: hashlib.sha256((clean / name).read_bytes()).hexdigest()
    for name in files}, indent=2) + "\n")
groups = {
    "focused": ["tests.test_legacy_worker_recovery", "tests.test_research_abc_routing",
                "tests.test_level2c_central_roles"],
    "regression": ["tests.test_legacy_worker_recovery", "tests.test_research_recovery",
        "tests.test_research_abc_routing", "tests.test_research_broker_admission",
        "tests.test_research_reservation_counts", "tests.test_research_continuation",
        "tests.test_hierarchy_gateway", "tests.test_hierarchy_service_research",
        "tests.test_hierarchy_model_callbacks", "tests.test_hierarchy_providers",
        "tests.test_venture_workflow", "tests.test_worker_inference",
        "tests.test_owner_research_quota_hold", "tests.test_level2c_central_roles"]}
commands = {}
failed = False
for group, modules in groups.items():
    command = [str(root / "infrastructure/python-runtime/.venv/bin/python"),
               "-B", "-m", "unittest", *modules, "-v"]
    commands[group] = command
    with (out / (group + ".log")).open("w") as stream:
        result = subprocess.run(command, cwd=clean, stdout=stream,
            stderr=subprocess.STDOUT, env=dict(os.environ,
                TMPDIR=str(clean / "artifacts/tmp"), PYTHONDONTWRITEBYTECODE="1"))
    (out / (group + ".exit")).write_text(str(result.returncode) + "\n")
    print(group, result.returncode, flush=True)
    failed |= result.returncode != 0
(out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
raise SystemExit(int(failed))

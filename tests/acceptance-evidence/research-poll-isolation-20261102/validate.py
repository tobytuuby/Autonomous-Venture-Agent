"""Reproduce against archived HEAD plus only this task's three source files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
root = Path.cwd()
out = root / "tests/acceptance-evidence/research-poll-isolation-20261102"
clean = root / "artifacts/research-poll-isolation-clean"
clean.mkdir(exist_ok=True)
with (out / "base.tar").open("wb") as stream:
    subprocess.run(["git", "archive", "HEAD"], stdout=stream, check=True)
subprocess.run(["tar", "-xf", str(out / "base.tar"), "-C", str(clean)], check=True)
(out / "base.tar").unlink()
sources = ["agents/ceo/hierarchy_service.py", "agents/ceo/hierarchy_research_daemon.py",
           "tests/test_research_poll_isolation.py"]
for file in sources:
    shutil.copyfile(root / file, clean / file)
(clean / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
modules = ["tests.test_research_poll_isolation", "tests.test_legacy_worker_recovery",
 "tests.test_research_recovery", "tests.test_research_abc_routing",
 "tests.test_research_broker_admission", "tests.test_research_reservation_counts",
 "tests.test_research_continuation", "tests.test_hierarchy_gateway",
 "tests.test_hierarchy_service_research", "tests.test_hierarchy_model_callbacks",
 "tests.test_hierarchy_providers", "tests.test_venture_workflow",
 "tests.test_worker_inference", "tests.test_owner_research_quota_hold",
 "tests.test_level2c_central_roles"]
cmd = ["python3", "-B", "-m", "unittest", *modules, "-v"]
(out / "command.json").write_text(json.dumps(cmd, indent=2) + "\n")
(out / "source-sha256.json").write_text(json.dumps(
    {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in sources}, indent=2) + "\n")
with (out / "regression.log").open("w") as log:
    result = subprocess.run(cmd, cwd=clean,
        env=dict(os.environ, TMPDIR=str(clean / "artifacts/tmp"), PYTHONDONTWRITEBYTECODE="1"),
        stdout=log, stderr=subprocess.STDOUT)
(out / "regression.exit").write_text(str(result.returncode) + "\n")
raise SystemExit(result.returncode)

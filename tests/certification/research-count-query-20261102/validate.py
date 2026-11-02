"""Reproduce selected validation on HEAD plus only this query fix."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

root = Path.cwd()
evidence = root / "artifacts/research-count-query-20261102"
clean = evidence / "clean"
clean.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", "HEAD"]))) as archive:
    archive.extractall(clean, filter="data")
changed = [
    "agents/ceo/hierarchy_client.py", "agents/ceo/hierarchy_gateway.py",
    "agents/ceo/hierarchy_research_daemon.py", "kernel/broker/isolated_mtls.py",
    "tests/test_owner_research_quota_hold.py", "tests/test_research_reservation_counts.py",
]
for name in changed:
    shutil.copyfile(root/name, clean/name)
tmp = clean/"artifacts/test-tmp"
tmp.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1")
groups = {
    "focused": "research_reservation_counts owner_research_quota_hold research_continuation",
    "regression": "broker_isolated_mtls broker_mtls_entrypoint research_broker_admission owner_research_admission research_abc_routing hierarchy_multi_worker hierarchy_service_research hierarchy_providers hierarchy_model_callbacks worker_inference hierarchy_gateway hierarchy_runner hierarchy_redirection venture_workflow manager_review_budget preparation_broker hierarchy_bootstrap ceo_research_review owner_research_progress",
}
failed = False
for group, names in groups.items():
    command = ["python3", "-B", "-m", "unittest", *["tests.test_"+n for n in names.split()], "-v"]
    (evidence/(group+".command")).write_text(" ".join(command)+"\n")
    with (evidence/(group+".log")).open("w") as output:
        result = subprocess.run(command, cwd=clean, env=env, stdout=output, stderr=subprocess.STDOUT)
    (evidence/(group+".exit")).write_text(str(result.returncode)+"\n")
    print(group, result.returncode, flush=True)
    failed |= bool(result.returncode)
raise SystemExit(failed)

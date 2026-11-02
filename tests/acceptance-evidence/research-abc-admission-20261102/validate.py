import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

root = Path.cwd()
evidence = root / "artifacts/ava-abc-admission-20261102"
clean = evidence / "clean-final"
clean.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", "HEAD"]))) as archive:
    archive.extractall(clean, filter="data")
scoped = ("agents/ceo/hierarchy_gateway.py", "tests/test_owner_research_admission.py",
          "tests/test_research_broker_admission.py", "tests/test_mvp_handoff.py")
for name in scoped:
    shutil.copyfile(root / name, clean / name)
modules = """test_research_broker_admission test_owner_research_admission
test_research_abc_routing test_hierarchy_multi_worker test_hierarchy_service_research
test_owner_research_quota_hold test_research_continuation test_worker_inference
test_hierarchy_gateway test_hierarchy_runner test_hierarchy_model_callbacks
test_hierarchy_redirection test_venture_workflow test_manager_review_budget
test_preparation_broker test_hierarchy_bootstrap test_ceo_research_review
test_mvp_handoff test_owner_research_progress test_owner_research_feedback""".split()
command = ["python3", "-B", "-m", "unittest", *["tests."+m for m in modules], "-v"]
(evidence / "test-command.txt").write_text(" ".join(command)+"\n")
failed = False
for label, cwd in (("clean-expanded", clean), ("dirty-expanded", root)):
    tmp = cwd / "artifacts/admission-test-tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    with (evidence / (label+".log")).open("w") as log:
        result = subprocess.run(command, cwd=cwd,
            env=dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1"),
            stdout=log, stderr=subprocess.STDOUT)
    (evidence / (label+".exit")).write_text(str(result.returncode)+"\n")
    print(label, "exit", result.returncode, flush=True)
    failed |= result.returncode != 0
raise SystemExit(failed)

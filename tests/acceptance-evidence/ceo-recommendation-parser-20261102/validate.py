"""Isolated HEAD archive plus only the scoped implementation/test changes."""
import io
import os
import pathlib
import shutil
import subprocess
import tarfile

root = pathlib.Path.cwd()
evidence = root / "tests/acceptance-evidence/ceo-recommendation-parser-20261102"
clean = root / "artifacts/ceo-recommendation-parser-clean"
clean.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", "HEAD"]))) as archive:
    archive.extractall(clean, filter="data")
for name in ("agents/ceo/ceo_research_review.py", "tests/test_ceo_research_review.py",
             "tests/test_research_continuation.py"):
    shutil.copyfile(root / name, clean / name)
tmp = clean / "artifacts/test-tmp"
tmp.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1")
modules = """test_ceo_research_review test_research_abc_routing test_hierarchy_service_research
test_hierarchy_providers test_hierarchy_model_callbacks test_research_continuation
test_owner_research_quota_hold test_level2c_central_roles test_provider_dispatch_transport
test_hierarchy_gateway test_hierarchy_runner test_hierarchy_multi_worker
test_research_broker_admission test_owner_research_admission test_worker_inference
test_owner_research_feedback test_owner_research_progress test_research_reservation_counts""".split()
for label, selected in (("focused", ["test_ceo_research_review", "test_research_continuation"]),
                        ("regression", modules)):
    command = ["python3", "-B", "-m", "unittest", *["tests." + m for m in selected], "-v"]
    with (evidence / (label + ".log")).open("w") as log:
        print("COMMAND:", " ".join(command), file=log, flush=True)
        result = subprocess.run(command, cwd=clean, env=env, stdout=log, stderr=subprocess.STDOUT)
    (evidence / (label + ".exit")).write_text(str(result.returncode) + "\n")
    print(label, "exit", result.returncode, flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)

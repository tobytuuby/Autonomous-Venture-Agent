import io, os, pathlib, shutil, subprocess, tarfile
root = pathlib.Path.cwd()
clean = root / "artifacts/research-manager-fix-clean"
clean.mkdir(exist_ok=True)
archive = subprocess.check_output(["git", "archive", "HEAD"])
with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
    tf.extractall(clean, filter="data")
files = ["agents/ceo/hierarchy_research_daemon.py", "agents/ceo/hierarchy_service.py",
         "tests/test_research_abc_routing.py"]
for name in files:
    shutil.copyfile(root / name, clean / name)
tmp = clean / "artifacts/test-tmp"
tmp.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE="1")
modules = """test_research_abc_routing test_hierarchy_service_research test_hierarchy_providers
test_hierarchy_model_callbacks test_research_continuation test_owner_research_quota_hold
test_level2c_central_roles test_provider_dispatch_transport test_hierarchy_gateway test_hierarchy_runner
test_hierarchy_multi_worker test_research_broker_admission test_owner_research_admission
test_worker_inference""".split()
result = subprocess.run(["python3", "-B", "-m", "unittest",
    *["tests." + m for m in modules], "-v"], cwd=clean, env=env)
raise SystemExit(result.returncode)

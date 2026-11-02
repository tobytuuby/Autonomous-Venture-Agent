from pathlib import Path
import os, shutil, subprocess, json, hashlib
root=Path.cwd()
clean=root/"artifacts/manager-pending-recovery-clean"
out=root/"tests/acceptance-evidence/research-recovery-20261102"
(clean/"artifacts").mkdir(exist_ok=True)
files=["agents/ceo/hierarchy_providers.py","agents/ceo/hierarchy_service.py","agents/ceo/provider_gateway.py","tests/test_research_recovery.py","tests/test_research_abc_routing.py","tests/test_level2c_central_roles.py"]
for f in files:
 shutil.copyfile(root/f,clean/f)
(out/"validated-source-sha256.json").write_text(json.dumps({f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},indent=2))
modules=["tests.test_research_recovery","tests.test_research_abc_routing","tests.test_hierarchy_service_research","tests.test_hierarchy_providers","tests.test_level2c_central_roles","tests.test_worker_inference","tests.test_research_continuation","tests.test_owner_research_quota_hold","tests.test_hierarchy_model_callbacks","tests.test_venture_workflow","tests.test_research_reservation_counts"]
env=dict(os.environ,TMPDIR=str(out/"tmp"))
cmd=["python3","-B","-m","unittest",*modules,"-v"]
(out/"clean-command.json").write_text(json.dumps(cmd))
with (out/"clean-tests.log").open("w") as log:
 result=subprocess.run(cmd,cwd=clean,env=env,stdout=log,stderr=subprocess.STDOUT)
(out/"clean-tests.exit").write_text(str(result.returncode)+"\n")
raise SystemExit(result.returncode)

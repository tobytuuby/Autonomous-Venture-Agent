"""Bounded source deployment to the existing Control services; never starts inference.

Run from the approved checkout after commit/push. Keeps the technical CEO inactive.
Only installed source files change; no service config, key, policy or ledger changes.
"""
import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
B=Path("/usr/local/lib/venture-control-broker-level2c")
C=Path("/usr/local/lib/venture-ceo-level2c")
def sha(raw): return hashlib.sha256(raw).hexdigest()
def run(*args): return subprocess.check_output(args,text=True).strip()
def active(name): return run("systemctl","is-active",name)
def atomic(path,raw,info):
 tmp=path.with_name(path.name+".acceptance-tmp")
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,"wb") as f:
   f.write(raw);os.fchown(f.fileno(),info.st_uid,info.st_gid)
   os.fchmod(f.fileno(),stat.S_IMODE(info.st_mode));f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if tmp.exists(): tmp.unlink()
def observation():
 raw=run("python3","-B","scripts/level2d_acceptance_observe.py")
 return json.loads(raw)
def require_research_ceo_inactive():
 # The historical gate checks only the legacy CEO. Unknown state also denies.
 try:
  state=run("systemctl","show","venture-owner-research-ceo.service","--property=ActiveState","--value")
 except (OSError,subprocess.SubprocessError):
  state="unknown"
 if state!="inactive":
  raise SystemExit("DENY: P1-04 research CEO must be verifiably inactive before legacy deployment")
def main():
 require_research_ceo_inactive()
 assert Path.cwd().resolve()==P and os.geteuid()==0
 assert run("systemctl","show","venture-level2d-ceo.service","--property=ActiveState","--value")=="inactive"
 assert active("venture-control-broker-mtls.service")=="active"
 for name in ("level2d-acceptance-focused-final.log","level2d-acceptance-regression.log"):
  log=(P/"artifacts"/name).read_text()
  assert "\nOK\n" in log and log.rstrip().endswith("EXIT_CODE=0"),"tests not complete"
 head=run("git","rev-parse","HEAD")
 assert run("git","rev-parse","origin/main")==head,"push first"
 pre=json.loads((P/"artifacts/level2d-install-preflight.json").read_text())
 files=["agents/ceo/hierarchy_gateway.py","agents/ceo/hierarchy_model_callbacks.py","agents/ceo/hierarchy_runner.py","agents/ceo/venture_workflow.py"]
 targets=[(root,rel) for root in (B,C) for rel in files]+[(C,"scripts/level2d_hierarchy_kickoff.py"),(C,"scripts/publish_owner_research_status.py")]
 changes=[]
 for root,rel in targets:
  target=root/rel
  assert not target.is_symlink() and not any(p.is_symlink() for p in target.parents)
  info=target.stat();assert stat.S_ISREG(info.st_mode) and info.st_nlink==1
  old=target.read_bytes();new=(P/rel).read_bytes()
  assert sha(old)==pre["installed_sources"][str(target)],"installed source changed"
  assert new==subprocess.check_output(["git","show",head+":"+rel]),"source not committed"
  if old!=new: changes.append((target,old,new,info))
 before=observation()
 assert before["states"]["level2d-multiworker-remediation-1"]["state"]=="BUDGET_EXHAUSTED"
 assert before["states"]["level2d-multiworker-acceptance-1"] is None
 backup=P/"artifacts/level2d-acceptance-control-backup"
 backup.mkdir(mode=0o700,exist_ok=False)
 for index,(target,old,new,info) in enumerate(changes):
  path=backup/str(index);path.write_bytes(old);path.chmod(0o600)
 applied=[]
 try:
  for target,old,new,info in changes:
   atomic(target,new,info);applied.append((target,old,info))
  subprocess.run(["systemctl","restart","venture-control-broker-mtls.service"],check=True)
  assert active("venture-control-broker-mtls.service")=="active"
  after=observation()
  assert after["states"]==before["states"],"signed workflow changed"
  assert after["resource_tables"]==before["resource_tables"],"resource ledger changed"
  assert after["policies"]==before["policies"],"policy changed"
  assert after["ceo"]["ActiveState"]=="inactive"
  report=dict(commit=head,installed=[dict(path=str(t),old_sha256=sha(o),new_sha256=sha(n)) for t,o,n,i in changes],
   broker_active=True,ceo_inactive=True,signed_journal_verified=after["signed_journal_verified"],
   ledger_rows_unchanged=True,historical_states_unchanged=True,provider_calls=0,
   new_workflow_created=False,configuration_changed=False)
  (P/"artifacts/level2d-acceptance-control-deploy.json").write_text(json.dumps(report,indent=2))
  print(json.dumps(report,indent=2))
 except BaseException:
  for target,old,info in reversed(applied): atomic(target,old,info)
  subprocess.run(["systemctl","restart","venture-control-broker-mtls.service"],check=True)
  raise
if __name__=="__main__": main()

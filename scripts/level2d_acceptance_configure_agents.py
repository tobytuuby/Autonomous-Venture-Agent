"""Human operator only: bind existing Agents roles to one new technical fixture.

No signing, provider request, quota edit, key rotation or journal modification.
Run as root from /home/epsilon/venture-agents-workspace after source validation.
"""
import hashlib,json,os,sqlite3,stat,subprocess,sys
from pathlib import Path
P=Path("/home/epsilon/venture-agents-workspace")
R=Path("/usr/local/lib/venture-manager-level2c")
OLD="level2d-multiworker-remediation-1"
NEW="level2d-multiworker-acceptance-1"
FILES={
 "agents/ceo/hierarchy_gateway.py":"3b03c983bd8469b3706628894c4dbed41630600d243d99ae9215babd267db272",
 "agents/ceo/hierarchy_model_callbacks.py":"e95a7a36bfcdf417031a3fecd6a1ae3062f1d316815dedf45fea9f4263c9e748",
 "agents/ceo/hierarchy_runner.py":"8d61c24dd45cc4783e86c04b729a5aa218c68a0df839a84e465fbcdc6575c86c",
 "agents/ceo/venture_workflow.py":"da95891be6291ae542e84200afc40ca036fa7227dc2f4dac3644fe6d65fe6cdc",
}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def atomic(path,raw,info):
 assert not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
 tmp=path.with_name(path.name+".acceptance-tmp")
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,"wb") as f:
   f.write(raw);os.fchown(f.fileno(),info.st_uid,info.st_gid)
   os.fchmod(f.fileno(),stat.S_IMODE(info.st_mode));f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if tmp.exists(): tmp.unlink()
def rows(p):
 with sqlite3.connect(p.as_uri()+"?mode=ro",uri=True) as db:
  return {t:sha(repr(sorted(db.execute('SELECT * FROM "'+t+'"'),key=repr)).encode())
    for t, in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
def main():
 assert Path.cwd().resolve()==P
 if os.geteuid()!=0: raise SystemExit("Human operator root required; do not bypass bridge no_new_privileges")
 assert (P/"artifacts/level2d-acceptance-agents-tests.log").read_text().rstrip().endswith("EXIT_CODE=0")
 sys.path.insert(0,str(R))
 from agents.ceo.hierarchy_client import HierarchyClient
 paths=[Path("/var/lib/venture-manager/level2d/hierarchy-config.json")]+[
  Path("/var/lib/venture-worker-"+letter+"/level2d/hierarchy-config.json") for letter in ("a","b","c")]
 configs=[json.loads(p.read_text()) for p in paths]
 manager=configs[0]
 client=HierarchyClient(manager["endpoint"],ca_file=manager["ca_file"],
  client_cert=manager["client_cert"],client_key=manager["client_key"])
 old=client.read(OLD)
 assert old["state"]=="BUDGET_EXHAUSTED" and old["revision"]==11 and old["used_units"]==5
 assert client.read(NEW) is None,"new fixture already exists: stop for review"
 changes=[]
 for rel,expected in FILES.items():
  path=R/rel;raw=path.read_bytes()
  assert sha(raw)==expected,"installed source differs: "+rel
  new=(P/rel).read_bytes()
  if new!=raw: changes.append((path,raw,new,path.stat()))
 private=[]
 for index,(path,cfg) in enumerate(zip(paths,configs)):
  role="manager" if index==0 else "worker"
  actor="service-manager" if index==0 else "worker-"+("a","b","c")[index-1]
  assert cfg["role"]==role and cfg["actor_id"]==actor and cfg["workflow_id"]==OLD
  policy=json.loads(Path(cfg["policy"]).read_text())
  if role=="worker":
   assert policy["actor_ids"]==["worker-a","worker-b","worker-c"]
   assert policy["maximum_requests"]==4 and policy["maximum_output_tokens"]==1024 and policy["model"]=="gpt-6-luna"
  else:
   assert policy["maximum_requests"]==8 and policy["roles"]["manager"]["model"]=="gpt-6-sol"
  candidate=dict(cfg,workflow_id=NEW)
  if "context" in candidate:
   assert candidate["context"]["session_id"]==OLD
   candidate["context"]=dict(candidate["context"],session_id=NEW)
  if role=="manager": candidate["decomposition_workers"]=dict(A="worker-a",B="worker-b",C="worker-c")
  raw=path.read_bytes();new=(json.dumps(candidate,indent=2)+"\n").encode()
  changes.append((path,raw,new,path.stat()))
  private.append(Path(cfg["state_dir"])/"inference.sqlite")
 units=["venture-level2d-manager.service"]+["venture-level2d-worker@worker-"+c+".service" for c in ("a","b","c")]
 assert all(subprocess.check_output(["systemctl","is-active",u],text=True).strip()=="active" for u in units)
 backup=P/"artifacts/level2d-acceptance-agents-backup"
 backup.mkdir(mode=0o700,exist_ok=False)
 applied=[]
 subprocess.run(["systemctl","stop",*units],check=True)
 try:
  journals={str(p):rows(p) for p in private}
  for index,(path,raw,new,info) in enumerate(changes):
   assert stat.S_ISREG(info.st_mode) and info.st_nlink==1
   b=backup/str(index);b.write_bytes(raw);b.chmod(0o600)
  for p in private:
   with sqlite3.connect(p.as_uri()+"?mode=ro",uri=True) as src,sqlite3.connect(backup/(p.parent.parent.name+"-inference.sqlite")) as dst:
    src.backup(dst)
  for path,raw,new,info in changes:
   atomic(path,new,info);applied.append((path,raw,info))
  assert client.read(NEW) is None
  assert client.read(OLD)==old
  assert {str(p):rows(p) for p in private}==journals
  subprocess.run(["systemctl","start",*units],check=True)
  assert all(subprocess.check_output(["systemctl","is-active",u],text=True).strip()=="active" for u in units)
  report=dict(workflow_id=NEW,old_workflow_unchanged=True,inference_journal_rows_unchanged=True,
   source_changes=[str(p) for p,o,n,i in changes if p.is_relative_to(R)],
   roles_configured=["service-manager","worker-a","worker-b","worker-c"],
   new_fixture_absent=True,provider_calls=0,keys_and_policies_unchanged=True,ceo_started=False)
  (P/"artifacts/level2d-acceptance-agents-deploy.json").write_text(json.dumps(report,indent=2))
  print(json.dumps(report,indent=2))
 except BaseException:
  subprocess.run(["systemctl","stop",*units],check=True)
  for path,raw,info in reversed(applied): atomic(path,raw,info)
  subprocess.run(["systemctl","start",*units],check=True)
  raise
if __name__=="__main__": main()

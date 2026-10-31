#!/usr/bin/env python3
"""Activate only inspected Control policy/code and inactive technical CEO binding.
Run from the approved Control checkout as root. No signer or provider invocation.
"""
import hashlib, json, os, pathlib, pwd, sqlite3, stat, subprocess, sys
P=pathlib.Path("/home/epsilon/venture-control-workspace")
FLOW="level2d-multiworker-remediation-1"
assert pathlib.Path.cwd().resolve()==P
assert os.geteuid()==0, "operator root required"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def unit(n):
 return dict(x.split("=",1) for x in subprocess.check_output(
  ["systemctl","show",n,"--property=Id,MainPID,ActiveState,WorkingDirectory"],text=True).splitlines() if "=" in x)
def regular(p):
 assert not p.is_symlink() and not any(x.is_symlink() for x in p.parents)
 assert p.is_file() and p.stat().st_nlink==1
def atomic(p,data,uid,gid,mode):
 tmp=p.with_name(p.name+".level2d-activation-tmp")
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 try:
  with os.fdopen(fd,"wb") as f:
   f.write(data); f.flush(); os.fsync(f.fileno()); os.fchown(f.fileno(),uid,gid); os.fchmod(f.fileno(),mode)
  os.replace(tmp,p)
  d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
  try: os.fsync(d)
  finally: os.close(d)
 finally:
  if tmp.exists(): tmp.unlink()
before=json.loads((P/"artifacts/level2d-activation-20261031/before.json").read_text())
b=unit("venture-control-broker-mtls.service")
c=unit("venture-level2d-ceo.service")
assert b["MainPID"]==before["broker"]["MainPID"] and b["ActiveState"]=="active"
assert c["ActiveState"]=="inactive", "technical CEO must remain inactive"
r=pathlib.Path(b["WorkingDirectory"]); cr=pathlib.Path(c["WorkingDirectory"])
assert r==pathlib.Path("/usr/local/lib/venture-control-broker-level2c")
assert cr==pathlib.Path("/usr/local/lib/venture-ceo-level2c")
a=r/"artifacts/preparation-authority"
policy=a/"worker-inference-policy.json"
cp=pathlib.Path(before["ceo_config_path"])
source=P/"agents/ceo/worker_inference.py"; target=r/"agents/ceo/worker_inference.py"
for p in (policy,cp,source,target): regular(p)
assert sha(target)==before["sources"]["agents/ceo/worker_inference.py"]["installed"]
assert sha(cp)==before["ceo_config_sha256"]
old=json.loads(policy.read_text()); assert old==before["policy"]
new=dict(old); new.pop("actor_id")
new["actor_ids"]=["service-worker","worker-a","worker-b","worker-c"]
assert old["maximum_requests"]==4 and old["model"]=="gpt-6-luna"
sys.path.insert(0,str(P))
from agents.ceo.worker_inference import valid_policy
valid_policy(new)
cfg=json.loads(cp.read_text())
assert cfg["role"]=="ceo" and cfg["actor_id"]=="service-ceo"
assert cfg["workflow_id"]=="level2d-acceptance-5" and cfg["context"]["session_id"]==cfg["workflow_id"]
assert cfg["context"]["venture_id"]=="venture-verification"
candidate=dict(cfg,workflow_id=FLOW,context=dict(cfg["context"],session_id=FLOW))
assert (P/"artifacts/level2d-activation-20261031/tests.exit").read_text().strip()=="0"
backup=P/"artifacts/level2d-activation-20261031/private-backups"
backup.mkdir(mode=0o700,exist_ok=False); os.chmod(backup,0o700)
changes=[(target,source.read_bytes()),(policy,(json.dumps(new,indent=2)+"\n").encode()),
         (cp,(json.dumps(candidate,indent=2)+"\n").encode())]
saved=[]
for i,(p,data) in enumerate(changes):
 info=p.stat(); raw=p.read_bytes(); dest=backup/(str(i)+"-"+p.name)
 dest.write_bytes(raw); os.chmod(dest,0o600)
 saved.append((p,raw,info))
# Preserve consistent copies of each live SQLite database without resetting it.
for name in ("resources.sqlite","hierarchy/workflow.sqlite","hierarchy/inbox.sqlite"):
 p=a/name
 if p.exists():
  with sqlite3.connect(p.as_uri()+"?mode=ro",uri=True) as src, sqlite3.connect(backup/p.name) as dst:
   src.backup(dst)
  os.chmod(backup/p.name,0o600)
report=dict(workflow_id=FLOW,backup_directory=str(backup),provider_calls=0,
 no_signatures_created=True,ceo_started=False,ledger_reset=False,
 shared_reservations_before=before["worker_reservations_by_venture"],
 installed=[],classification="operator-executed Control activation; acceptance blocked")
stopped=False
try:
 subprocess.run(["systemctl","stop","venture-control-broker-mtls.service"],check=True); stopped=True
 for (p,data),(_,raw,info) in zip(changes,saved):
  assert p.read_bytes()==raw, "concurrent deployed change"
  atomic(p,data,info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode))
  report["installed"].append(dict(path=str(p),before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=sha(p)))
 subprocess.run(["systemctl","start","venture-control-broker-mtls.service"],check=True)
 assert unit("venture-control-broker-mtls.service")["ActiveState"]=="active"
 assert unit("venture-level2d-ceo.service")["ActiveState"]=="inactive"
 report["broker_after"]=unit("venture-control-broker-mtls.service")
 print(json.dumps(report,indent=2,sort_keys=True))
except BaseException:
 if stopped:
  subprocess.run(["systemctl","stop","venture-control-broker-mtls.service"],check=False)
  for p,raw,info in reversed(saved):
   atomic(p,raw,info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode))
  subprocess.run(["systemctl","start","venture-control-broker-mtls.service"],check=False)
 raise

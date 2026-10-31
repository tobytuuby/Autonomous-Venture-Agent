#!/usr/bin/env python3
"""Operator step for the existing Agents services; no signing or model call.
Root is required. Run only from /home/epsilon/venture-agents-workspace.
The requested workflow must still be absent. This does not resolve exhausted
Control venture quota and must not be followed by kickoff without that gate.
"""
import hashlib, json, os, pathlib, stat, subprocess
P=pathlib.Path("/home/epsilon/venture-agents-workspace")
FLOW="level2d-multiworker-remediation-1"
assert pathlib.Path.cwd().resolve()==P
if os.geteuid()!=0:
 raise SystemExit("STOP: operator root required; do not bypass no-new-privileges")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def unit(n):
 return dict(x.split("=",1) for x in subprocess.check_output(["systemctl","show",n,
  "--property=ActiveState,User,WorkingDirectory"],text=True).splitlines() if "=" in x)
def regular(p):
 assert p.is_file() and not p.is_symlink() and p.stat().st_nlink==1
 assert not any(x.is_symlink() for x in p.parents)
def wire(v): return (json.dumps(v,indent=2)+"\n").encode()
def atomic(p,data,info):
 t=p.with_name(p.name+".level2d-activation-tmp")
 fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,"wb") as f:
   f.write(data); f.flush(); os.fsync(f.fileno()); os.fchown(f.fileno(),info.st_uid,info.st_gid)
   os.fchmod(f.fileno(),stat.S_IMODE(info.st_mode))
  os.replace(t,p)
  fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
  try: os.fsync(fd)
  finally: os.close(fd)
 finally:
  if t.exists(): t.unlink()
mp=pathlib.Path("/var/lib/venture-manager/level2d/hierarchy-config.json")
regular(mp); cfg=json.loads(mp.read_text())
assert cfg["role"]=="manager" and cfg["actor_id"]=="service-manager"
assert cfg["workflow_id"].startswith("level2d-acceptance-"), "unexpected Manager binding"
assert cfg["context"]["session_id"]==cfg["workflow_id"]
assert cfg["context"]["venture_id"]=="venture-verification"
units=["venture-level2d-manager.service"]+["venture-level2d-worker@worker-"+x+".service" for x in "abc"]
assert all(unit(u)["ActiveState"]=="active" for u in units)
root=pathlib.Path(unit(units[0])["WorkingDirectory"])
assert root==pathlib.Path("/usr/local/lib/venture-manager-level2c")
# Inspect actual installed code against the reviewed source hashes before changing configs.
bundle=P/"artifacts/level2d-activation-20261031"
manifest=json.loads((bundle/"agents-code-hashes.json").read_text())
for rel,expected in manifest.items():
 regular(root/rel); assert sha(root/rel)==expected, "installed code mismatch: "+rel
policy=json.loads((bundle/"worker-policy.json").read_text())
assert policy["actor_ids"]==["service-worker","worker-a","worker-b","worker-c"]
assert policy["maximum_requests"]==4 and policy["maximum_output_tokens"]<=1024
assert policy["model"]=="gpt-6-luna"
candidate=dict(cfg,workflow_id=FLOW,context=dict(cfg["context"],session_id=FLOW),
 decomposition_workers=dict(A="worker-a",B="worker-b",C="worker-c"))
changes={mp:wire(candidate)}
for x in "abc":
 wp=pathlib.Path("/var/lib/venture-worker-"+x+"/level2d/hierarchy-config.json")
 regular(wp); w=json.loads(wp.read_text())
 assert w["actor_id"]=="worker-"+x and w["role"]=="worker" and w["workflow_id"]==FLOW
 pp=pathlib.Path(w["policy"]); regular(pp)
 assert pp.is_relative_to(wp.parent), "worker policy must stay in its private home"
 old=json.loads(pp.read_text())
 assert {k:v for k,v in old.items() if k not in ("actor_id","actor_ids")}=={k:v for k,v in policy.items() if k!="actor_ids"}
 assert "worker-"+x in old.get("actor_ids",[old.get("actor_id")])
 changes[pp]=wire(policy)
# Authenticate a read as the Manager; deny activation if the target could already run.
probe = """import json
from pathlib import Path
from agents.ceo.hierarchy_client import HierarchyClient
c=json.loads(Path('/var/lib/venture-manager/level2d/hierarchy-config.json').read_text())
h=HierarchyClient(c['endpoint'],ca_file=c['ca_file'],client_cert=c['client_cert'],client_key=c['client_key'])
assert h.read('level2d-multiworker-remediation-1') is None, 'target workflow already exists; stop'
print('TARGET_ABSENT')
"""
subprocess.run(["/usr/bin/python3","-B","-c",probe],check=True,cwd=root,
 user="venture-manager",group="venture-manager",
 env={"PATH":"/usr/bin:/bin","PYTHONPATH":str(root)})
# Do not copy or print private signing or TLS key bytes. Existing references remain.
backup=bundle/"private-backups"
backup.mkdir(mode=0o700,exist_ok=False); os.chmod(backup,0o700)
saved=[]
for n,(p,data) in enumerate(changes.items()):
 raw=p.read_bytes(); info=p.stat(); dest=backup/(str(n)+"-"+p.name)
 dest.write_bytes(raw); os.chmod(dest,0o600); saved.append((p,raw,info))
stopped=False
try:
 subprocess.run(["systemctl","stop",*units],check=True); stopped=True
 for (p,data),(_,raw,info) in zip(changes.items(),saved):
  assert p.read_bytes()==raw, "concurrent configuration change"
  atomic(p,data,info)
 subprocess.run(["systemctl","start",*units],check=True)
 assert all(unit(u)["ActiveState"]=="active" for u in units)
 print(json.dumps(dict(workflow_id=FLOW,decomposition_workers=candidate["decomposition_workers"],
  installed=[dict(path=str(p),before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=sha(p)) for p,raw,info in saved],
  backup_directory=str(backup),provider_calls=0,signatures_created=False,quota_reconciled=False)))
except BaseException:
 if stopped:
  subprocess.run(["systemctl","stop",*units],check=False)
  for p,raw,info in reversed(saved): atomic(p,raw,info)
  subprocess.run(["systemctl","start",*units],check=False)
 raise

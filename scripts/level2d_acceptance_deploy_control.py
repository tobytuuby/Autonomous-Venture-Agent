"""Bounded source deployment to the existing Control services; never starts inference.

Run from the approved checkout after commit/push. Keeps the technical CEO inactive.
Only installed source files change; no service config, key, policy or ledger changes.
"""
import argparse,hashlib,json,os,stat,subprocess,sys
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
  directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
  try: os.fsync(directory)
  finally: os.close(directory)
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
def main(argv=()):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--preflight-only",action="store_true",
                     help="print existing Stage6 decision; no live observation or mutation")
 args=parser.parse_args(argv)
 # Consult the existing Stage6 authority before even observing live services.
 sys.path.insert(0,str(P))
 from scripts.ceo_stage6_deployment_gate import deployment_decision
 decision=deployment_decision()
 if args.preflight_only:
  print(json.dumps(decision,sort_keys=True))
  raise SystemExit(2)
 if decision.get("deployment_allowed") is not True:
  raise SystemExit("DENY: existing Stage6 blocks deployment; synthetic C4 is not authority")
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


# C4 is deliberately a fixture-only procedure in this existing deployment
# component. It has no SSH, systemd, provider, ledger mutation or live adapter.
# Fixture identity observations are evidence inputs, never production authority.
def _fixture_path(root, relative):
 path=root/relative
 if (not isinstance(relative,str) or Path(relative).is_absolute()
     or ".." in Path(relative).parts or str(path.resolve())!=str(path)):
  raise ValueError("noncanonical fixture path")
 path.relative_to(root)
 if any(p.is_symlink() for p in (path,*path.parents)):
  raise ValueError("symlink fixture path")
 return path

def _fixture_root(root):
 root=Path(root)
 if (not root.is_absolute() or root.parent!=P or not root.name.startswith("c4-fixture-")
     or root.is_symlink() or root.resolve()!=root):
  raise ValueError("C4 accepts only direct project-local synthetic fixtures")
 return root

def _snapshot(root, names):
 if not isinstance(names,list) or not names or len(names)>128 or len(set(names))!=len(names):
  raise ValueError("bounded unique inventory required")
 if all(name.startswith("state/") for name in names):
  # Flat, exhaustive state inventory: new journals/sidecars or unknown files
  # invalidate coverage, including writes made while existing actions drain.
  entries=[]
  with os.scandir(root/"state") as scan:
   for entry in scan:
    entries.append("state/"+entry.name)
    if len(entries)>128: raise ValueError("state inventory bound")
  if set(entries)!=set(names): raise ValueError("state inventory changed")
 result={}; total=0
 for name in sorted(names):
  path=_fixture_path(root,name); before=path.stat()
  if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>1048576:
   raise ValueError("unsafe or oversized fixture file")
  raw=path.read_bytes(); after=path.stat(); total+=len(raw)
  stable=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_uid,s.st_gid,
                   s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  if stable(before)!=stable(after) or total>4194304:
   raise ValueError("unstable or oversized snapshot")
  result[name]=dict(sha256=sha(raw),size=len(raw),uid=before.st_uid,
                    mode=stat.S_IMODE(before.st_mode),dev=before.st_dev,ino=before.st_ino)
 return result

def _digest(value):
 return sha(json.dumps(value,sort_keys=True,separators=(",",":")).encode())

def coordinated_preflight(root, plan, reviewed_plan_sha256):
 """Bounded read-only synthetic prerequisite check. Never creates a gate."""
 from kernel.broker.isolated_mtls import MaintenanceAdmission
 root=_fixture_root(root)
 # Detach caller-owned mutable data before any validation or wait.
 plan=json.loads(json.dumps(plan))
 if _digest(plan)!=reviewed_plan_sha256 or plan.get("classification")!="SYNTHETIC_ONLY":
  raise ValueError("exact independently reviewed fixture plan required")
 expected={"Control":{"ceo","broker"},"Agents":{"manager-1","manager-2","manager-3",
                                              "worker-A","worker-B","worker-C"}}
 participants=plan["participants"]
 if len(participants)!=8 or {h:{p["role"] for p in participants if p["host"]==h}
                              for h in expected}!=expected:
  raise ValueError("exact two-host participant inventory required")
 if any(p["host"] not in expected or type(p["uid"]) is not int or p["uid"]<0 for p in participants):
  raise ValueError("host/UID pins required")
 # One control per host and service UID; no sharing across host/UID groups.
 groups={}
 for p in participants:
  key=(p["host"],p["uid"])
  value=(p["control"],p["identity"])
  if key in groups and groups[key]!=value:
   raise ValueError("one gate per host/UID required")
  groups[key]=value
 if len({v[0] for v in groups.values()})!=len(groups):
  raise ValueError("host/UID gates must be independent")
 gates=[]
 for key,(control,identity) in sorted(groups.items()):
  path=_fixture_path(root,control)
  if key[1]!=os.geteuid():
   raise ValueError("fixture runner must act as pinned service UID")
  gates.append((key,MaintenanceAdmission(str(path),identity)))
 # Frozen files contain synthetic trust, signed scope/quota policy, timer and
 # external-writer inventory, and source/installed/loaded identity observations.
 frozen=_snapshot(root,plan["frozen"])
 if frozen!=plan["baseline"] or _snapshot(root,plan["frozen"])!=frozen:
  raise ValueError("immutable prerequisite baseline changed")
 required={"trust","signed_scope_quota","timers","external_writers","identities"}
 if set(plan["prerequisites"])!=required:
  raise ValueError("complete prerequisite evidence required")
 for kind,name in plan["prerequisites"].items():
  if name not in plan["frozen"]:
   raise ValueError("prerequisite outside immutable baseline")
  value=json.loads(_fixture_path(root,name).read_bytes())
  if kind=="identities":
   if (len(value)!=8 or { (v["host"],v["role"]) for v in value}
       !={(p["host"],p["role"]) for p in participants}
       or any(set(v)!={"host","role","source","installed","loaded"} or
              not v["source"] or v["source"]!=v["installed"] or v["source"]!=v["loaded"]
              for v in value)):
    raise ValueError("source/installed/loaded fixture identity mismatch")
  elif value!={"classification":"SYNTHETIC_ONLY","ready":True}:
   raise ValueError("prerequisite not ready")
 state=_snapshot(root,plan["state"])
 if set(plan["state"]) & set(plan["frozen"]):
  raise ValueError("state and frozen inventories overlap")
 updates=plan["updates"]
 if not updates or not set(updates)<=set(plan["frozen"]):
  raise ValueError("code must be pinned in baseline")
 for name,new in updates.items():
  if (not name.startswith(("code/Control/","code/Agents/")) or
      not name.endswith(".py") or not isinstance(new,str)):
   raise ValueError("code-only fixture update required")
  compile(new,name,"exec")
 if plan["execution_status"] not in plan["state"]:
  raise ValueError("pending proof must be snapshotted")
 return root,plan,gates,state

def _close_fixture_gates(gates):
 from kernel.broker.isolated_mtls import MaintenanceDenied
 errors=[]
 for key,gate in gates:
  try:
   with gate.drain(0): pass
  except MaintenanceDenied:
   # A busy lease still persists CLOSED. The joined drain below must succeed;
   # malformed/unsafe controls cannot become an attestation.
   errors.append(key)
 return errors

def coordinated_synthetic_maintenance(root, plan, reviewed_plan_sha256, timeout=2):
 """Close all, drain roles then broker, snapshot, change code, attest CLOSED.

 Return is not release. Failure retains CLOSED; rollback restores code only.
 This function never stops/restarts a real service or writes execution state.
 """
 import time
 from contextlib import ExitStack
 from kernel.broker.isolated_mtls import MaintenanceAdmission
 MaintenanceAdmission._deadline(timeout)
 root,plan,gates,_=coordinated_preflight(root,plan,reviewed_plan_sha256)
 deadline=time.monotonic()+timeout
 _close_fixture_gates(gates)
 applied=[]
 try:
  with ExitStack() as stack:
   broker=next((p["host"],p["uid"]) for p in plan["participants"] if p["role"]=="broker")
   for key,gate in sorted(gates,key=lambda item:(item[0]==broker,item[0])):
    stack.enter_context(gate.drain(max(0,deadline-time.monotonic())))
   if _snapshot(root,plan["frozen"])!=plan["baseline"]:
    raise ValueError("baseline changed during drain")
   before=_snapshot(root,plan["state"])
   status=json.loads(_fixture_path(root,plan["execution_status"]).read_bytes())
   if status!={"execution":"COMPLETE","response":"DURABLE"}:
    raise ValueError("HOLD: pending/ambiguous execution; never retry")
   # Code-only backup, unique run directory. No state or trust restoration.
   backup=root/"code-backup"; backup.mkdir(mode=0o700,exist_ok=False)
   originals=[]
   for index,name in enumerate(sorted(plan["updates"])):
    target=_fixture_path(root,name); raw=target.read_bytes(); info=target.stat()
    saved=backup/str(index)
    with saved.open("xb") as stream:
     os.fchmod(stream.fileno(),0o600); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    originals.append((target,raw,info))
   # Sorted reviewed plan gives the backup-index/path mapping. Persist all
   # backups and directory entries before replacing the first code file.
   for directory in (backup,root):
    fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
   for target,raw,info in originals:
    name=str(target.relative_to(root))
    applied.append((target,raw,info))
    atomic(target,plan["updates"][name].encode(),info)
   if _snapshot(root,plan["state"])!=before:
    raise ValueError("protected state bytes/identity changed")
   # Code changes must not alter trust, timers, quotas or identity observations.
   frozen=_snapshot(root,plan["frozen"])
   for name in set(plan["frozen"])-set(plan["updates"]):
    if frozen[name]!=plan["baseline"][name]:
     raise ValueError("immutable prerequisite changed")
   attestation=dict(classification="LOCAL_SYNTHETIC_EXECUTION",deployment_allowed=False,
       resume_verified=False,plan_sha256=reviewed_plan_sha256,state=before,frozen=frozen,
       gates=[dict(host=k[0],uid=k[1],control=str(g.path.relative_to(root)),
                   identity=":".join(map(str,g.identity))) for k,g in gates])
   receipt=root/"closed-attestation.json"
   with receipt.open("x") as stream:
    json.dump(attestation,stream,sort_keys=True); stream.flush(); os.fsync(stream.fileno())
   return attestation
 except BaseException:
  # Recovery is reversible code only; unresolved state remains evidence for HOLD.
  try:
   for target,raw,info in reversed(applied): atomic(target,raw,info)
  finally:
   _close_fixture_gates(gates)
  raise

def release_synthetic_after_attestation(root, plan, reviewed_plan_sha256,
                                        reviewed_attestation_sha256):
 """Independent explicit release, after review of this exact CLOSED receipt.

 No CLI/live counterpart. Receipt pins, current bytes and all CLOSED drains
 must still match. Release failure recloses every fixture control.
 """
 from contextlib import ExitStack
 from kernel.broker.isolated_mtls import MaintenanceAdmission
 root=_fixture_root(root)
 plan=json.loads(json.dumps(plan))
 # Bind the original plan without comparing its old code baseline after update.
 if _digest(plan)!=reviewed_plan_sha256:
  raise ValueError("reviewed plan changed")
 receipt=_fixture_path(root,"closed-attestation.json")
 if receipt.stat().st_size>1048576: raise ValueError("receipt bound")
 attestation=json.loads(receipt.read_bytes())
 if (_digest(attestation)!=reviewed_attestation_sha256 or
     attestation["plan_sha256"]!=reviewed_plan_sha256):
  raise ValueError("independent exact attestation review required")
 # Re-derive expected gates from the reviewed plan, never trust receipt paths.
 expected=sorted({(p["host"],p["uid"],p["control"],p["identity"])
                   for p in plan["participants"]})
 if attestation["gates"]!=[dict(host=h,uid=u,control=c,identity=i) for h,u,c,i in expected]:
  raise ValueError("attestation gate identity mismatch")
 gates=[((h,u),MaintenanceAdmission(str(_fixture_path(root,c)),i)) for h,u,c,i in expected]
 try:
  with ExitStack() as stack:
   for key,gate in gates:
    if gate.path.read_bytes()!=b"CLOSED\n": raise ValueError("release requires CLOSED")
    stack.enter_context(gate.drain(0))
   if (_snapshot(root,plan["state"])!=attestation["state"] or
       _snapshot(root,plan["frozen"])!=attestation["frozen"]):
    raise ValueError("post-attestation drift; HOLD")
  # C1 release independently reacquires locks; participating writers are
  # cooperative. Privileged/uncooperative writers are outside fixture proof.
  for key,gate in gates: gate.release(0)
 except BaseException:
  _close_fixture_gates(gates)
  raise
 return dict(classification="SYNTHETIC_RELEASE_ONLY",deployment_allowed=False)

if __name__=="__main__": main(sys.argv[1:])

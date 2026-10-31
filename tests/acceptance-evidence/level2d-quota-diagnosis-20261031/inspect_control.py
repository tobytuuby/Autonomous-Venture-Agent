#!/usr/bin/env python3
"""Read-only installed governor diagnosis. No signer, reserve, or provider entrypoint."""
import datetime as dt, hashlib, json, os, pathlib, pwd, sqlite3, subprocess, sys
P=pathlib.Path("/home/epsilon/venture-control-workspace")
assert pathlib.Path.cwd().resolve()==P
assert os.geteuid()==0
sys.dont_write_bytecode=True
def unit(name):
 return dict(x.split("=",1) for x in subprocess.check_output(["systemctl","show",name,"--property=ActiveState,MainPID,WorkingDirectory"],text=True).splitlines())
broker=unit("venture-control-broker-mtls.service")
ceo=unit("venture-level2d-ceo.service")
r=pathlib.Path(broker["WorkingDirectory"])
assert r==pathlib.Path("/usr/local/lib/venture-control-broker-level2c")
sys.path.insert(0,str(r))
env=dict(x.split("=",1) for x in pathlib.Path("/proc",broker["MainPID"],"environ").read_bytes().decode().split("\0") if "=" in x)
from agents.ceo.control_plane import load_trust
from agents.ceo.venture_workflow import VentureWorkflow
from agents.ceo import service_identity as si
from agents.ceo import worker_inference as wi
a=si.AUTHORITY_DIRECTORY
cfg=json.loads(pathlib.Path("/usr/local/lib/venture-ceo-level2c/artifacts/level2c-ceo/hierarchy-config.json").read_text())
uid=pwd.getpwnam("venture-broker").pw_uid
os.setresuid(uid,uid,0)
trust=load_trust(env["VENTURE_BROKER_HIERARCHY_TRUST"])
policy=wi.current_policy()
authority=si.ProviderQuota(a).authority()
def ro(path):
 db=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
 db.execute("PRAGMA query_only=ON")
 return db
journal=VentureWorkflow.__new__(VentureWorkflow)
journal.actors=trust
journal.db=ro(a/"hierarchy/workflow.sqlite")
journal.verify()
target=cfg["workflow_id"]
def state(flow):
 row=journal.db.execute("SELECT snapshot FROM inbox WHERE id=?",(flow,)).fetchone()
 return json.loads(row[0]) if row else None
target_state=state(target)
db=ro(a/"resources.sqlite")
tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
rows=[]
for key,raw in db.execute("SELECT identity,request FROM worker_reservations"):
 request=json.loads(raw)
 prior_state=state(request["workflow_id"])
 day=db.execute("SELECT day,tokens FROM reservations WHERE identity=?",(key,)).fetchone()
 execution=db.execute("SELECT status FROM worker_executions WHERE identity=?",(key,)).fetchone() if "worker_executions" in tables else None
 rows.append(dict(identity=key,workflow_id=request["workflow_id"],venture_id=prior_state["venture_id"],signed_state=prior_state["state"],worker_id=request["worker_id"],assignment_id=request.get("assignment_id","LEGACY_SINGLE_WORKER"),policy_epoch=request["policy"]["epoch"],ceiling=request["policy"]["maximum_requests"],daily_reservation=list(day) if day else None,execution_status=execution[0] if execution else "ABSENT"))
now=dt.datetime.now(dt.timezone.utc)
used,tokens=db.execute("SELECT COUNT(*),COALESCE(SUM(tokens),0) FROM reservations WHERE day=?",(now.date().isoformat(),)).fetchone()
shared=[x for x in rows if x["venture_id"]==cfg["context"]["venture_id"]]
ceiling=min([policy["maximum_requests"]]+[x["ceiling"] for x in shared])
os.setresuid(0,0,0)
source={}
for f in ("agents/ceo/service_identity.py","agents/ceo/worker_inference.py","agents/ceo/venture_workflow.py"):
 source[f]=dict(installed_sha256=hashlib.sha256((r/f).read_bytes()).hexdigest(),checkout_sha256=hashlib.sha256((P/f).read_bytes()).hexdigest())
report=dict(at=now.isoformat(),classification="read-only installed Control ledger and cryptographically verified signed journal",broker=broker,ceo=ceo,authority=authority,worker_policy=policy,
 daily=dict(day=now.date().isoformat(),used_requests=used,maximum_requests=si.DAILY_REQUESTS,remaining_requests=max(0,si.DAILY_REQUESTS-used),reserved_output_tokens=tokens,maximum_output_tokens=si.DAILY_OUTPUT_TOKENS,next_utc_window=(now+dt.timedelta(days=1)).date().isoformat()+"T00:00:00+00:00"),
 venture=dict(id=cfg["context"]["venture_id"],used_worker_reservations=len(shared),effective_ceiling=ceiling,remaining=max(0,ceiling-len(shared)),renewal_window=None,prior_reservations=shared),
 target=dict(workflow_id=target,signed_state=target_state["state"] if target_state else None,context=cfg["context"]),sources=source,
 total_worker_reservations=len(rows),journal_verified=True,
 provider_calls_this_inspection=0,provider_side_remaining_quota="NOT_INDEPENDENTLY_VERIFIED",
 decision="DO_NOT_KICKOFF" if len(shared)>=ceiling else "REQUIRES_REMAINING_PREFLIGHT")
print(json.dumps(report,indent=2,sort_keys=True))
journal.close();db.close()

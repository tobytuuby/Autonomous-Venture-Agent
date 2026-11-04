"""Live CEO-uid GET plus immutable signature/recovery joins. No execution."""
import hashlib,json,os,pwd,sqlite3,ssl,sys,urllib.request
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
assert Path.cwd()==P
sys.path.insert(0,str(P))
from agents.ceo.hierarchy_client import HierarchyClient,NoRedirect
from agents.ceo.control_plane import load_trust
from agents.ceo.venture_workflow import VentureWorkflow,hashed
C=Path("/usr/local/lib/venture-ceo-level2c")
B=Path("/usr/local/lib/venture-control-broker-level2c")
cfg=json.loads((C/"artifacts/level2c-ceo/hierarchy-config.json").read_text())
def ro(p):
 d=sqlite3.connect(p.resolve().as_uri()+"?mode=ro",uri=True,timeout=3);d.execute("PRAGMA query_only=ON");return d
r={}
db=ro(B/"artifacts/preparation-authority/resources.sqlite")
tables=["reservations","remote_reservations","remote_executions","worker_reservations","worker_executions","worker_research_charges"]
def counts(): return {t:db.execute("SELECT COUNT(*) FROM "+t).fetchone()[0] for t in tables}
r["counts_before"]=counts()
# Inspect pending intent binding only; do not export prompts or responses.
pending=[]
for p in Path(cfg["state_dir"]).rglob("*.sqlite"):
 d=ro(p)
 try:
  if not d.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='calls'").fetchone(): continue
  for identity,request,attempt in d.execute("SELECT identity,request,attempt FROM calls WHERE response IS NULL"):
   row=db.execute("SELECT request FROM remote_reservations WHERE identity=?",(identity,)).fetchone()
   reservation=json.loads(row[0]) if row else None
   ex=db.execute("SELECT status FROM remote_executions WHERE identity=?",(identity,)).fetchone()
   pending.append({"local_path":str(p),"identity":identity,"request_sha256":hashlib.sha256(request.encode()).hexdigest(),"attempt_sha256":hashlib.sha256(attempt.encode()).hexdigest(),"central_reservation":row is not None,"execution_mode":reservation.get("execution_mode","LEGACY") if reservation else None,"central_execution_status":ex[0] if ex else "ABSENT"})
 finally:d.close()
r["pending_intents"]=pending
w=VentureWorkflow.__new__(VentureWorkflow)
# Independently parse public trust for offline verification; never alter runtime roots.
trust=Path(cfg["trust"])
assert trust.is_relative_to(C) and not trust.is_symlink()
assert trust.stat().st_uid==pwd.getpwnam("venture-ceo").pw_uid and not trust.stat().st_mode & 0o022
value=json.loads(trust.read_text())
assert set(value)=={"actors"} and len(value["actors"])<=32
w.actors={k:(v["role"],bytes.fromhex(v["public_key"])) for k,v in value["actors"].items()}
assert all(len(v[1])==32 for v in w.actors.values())
assert len({v[1] for v in w.actors.values()})==len(w.actors)
w.db=ro(B/"artifacts/preparation-authority/hierarchy/workflow.sqlite")
try:
 w.verify()
 r["signed_journal"]={"verified":True,"audit_records":w.db.execute("SELECT COUNT(*) FROM audit").fetchone()[0],"workflows":w.db.execute("SELECT COUNT(*) FROM inbox").fetchone()[0]}
except Exception as e:r["signed_journal"]={"verified":False,"error_type":type(e).__name__}
# Use the real service uid, installed certificate and existing loopback mTLS endpoint.
account=pwd.getpwnam("venture-ceo")
os.setegid(account.pw_gid);os.seteuid(account.pw_uid)
try:
 assert os.geteuid()==account.pw_uid
 client=HierarchyClient(cfg["endpoint"],ca_file=cfg["ca_file"],client_cert=cfg["client_cert"],client_key=cfg["client_key"])
 assert client.base=="https://localhost:8443"
 ctx=ssl.create_default_context(cafile=cfg["ca_file"]);ctx.load_cert_chain(cfg["client_cert"],cfg["client_key"])
 client.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ctx),NoRedirect())
 index=client.research_list()
 r["service_uid_get"]={"ok":True,"uid":os.geteuid(),"user":account.pw_name,"actor":cfg["actor_id"],"research_count":len(index),"snapshot_joins":[]}
 for entry in index[:30]:
  s=client.read(entry["workflow_id"])
  row=w.db.execute("SELECT snapshot FROM inbox WHERE id=?",(entry["workflow_id"],)).fetchone()
  r["service_uid_get"]["snapshot_joins"].append({"workflow_id":entry["workflow_id"],"revision":s["revision"],"matches_verified_journal":row is not None and hashed(json.loads(row[0]))==hashed(s)})
except Exception as e:r["service_uid_get"]={"ok":False,"error_type":type(e).__name__}
finally:os.seteuid(0);os.setegid(0)
r["counts_after"]=counts();r["counts_unchanged"]=r["counts_before"]==r["counts_after"]
db.close();w.db.close()
print(json.dumps(r,indent=2))
(P/"tests/acceptance-evidence/ceo-legacy-units-20261104/verified-readonly.json").write_text(json.dumps(r,indent=2)+"\n")

"""Read-only, secret-free observation of existing Control acceptance and Owner API."""
import hashlib,json,os,sqlite3,subprocess,sys
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
assert Path.cwd().resolve()==P
def unit(name):
 return dict(x.split("=",1) for x in subprocess.check_output(["systemctl","show",name,"--property=Id,ActiveState,MainPID,WorkingDirectory"],text=True).splitlines() if "=" in x)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
broker=unit("venture-control-broker-mtls.service")
root=Path(broker["WorkingDirectory"])
env=dict(x.split("=",1) for x in Path("/proc",broker["MainPID"],"environ").read_bytes().decode().split("\0") if "=" in x)
sys.path.insert(0,str(P))
from agents.ceo.control_plane import load_trust
from agents.ceo.venture_workflow import VentureWorkflow
trust={k:(v["role"],bytes.fromhex(v["public_key"])) for k,v in json.loads(Path(env["VENTURE_BROKER_HIERARCHY_TRUST"]).read_text())["actors"].items()}
authority=root/"artifacts/preparation-authority"
def connect(p): return sqlite3.connect(p.as_uri()+"?mode=ro",uri=True)
w=object.__new__(VentureWorkflow)
w.actors=trust
w.db=connect(authority/"hierarchy/workflow.sqlite")
w.verify()
states={}
for flow in ("level2d-acceptance-5","level2d-multiworker-remediation-1","level2d-multiworker-acceptance-1"):
 try: s=w.read(flow)
 except KeyError: s=None
 if s:
  states[flow]={k:s.get(k) for k in ("state","revision","used_units","scope","operational_authority","money_released")}
  states[flow]["actions"]=[{"actor":(v:=json.loads(raw)["snapshot"])["last_command"]["actor_id"],"action":v["last_command"]["action"],"revision":v["revision"]} for raw, in w.db.execute("SELECT event FROM audit ORDER BY sequence") if json.loads(raw)["snapshot"]["id"]==flow]
 else: states[flow]=None
files=["agents/ceo/worker_inference.py","agents/ceo/venture_workflow.py","agents/ceo/hierarchy_gateway.py","agents/ceo/hierarchy_model_callbacks.py","agents/ceo/hierarchy_runner.py"]
sources={rel:{"checkout":sha(P/rel),"broker":sha(root/rel)} for rel in files}
db=connect(authority/"resources.sqlite")
tables={}
for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
 rows=db.execute('SELECT * FROM "'+name+'"').fetchall()
 tables[name]={"count":len(rows),"rows_sha256":hashlib.sha256(repr(sorted(rows,key=repr)).encode()).hexdigest(),"columns":[x[1] for x in db.execute('PRAGMA table_info("'+name+'")')]}
policies={}
for name in ("worker-inference-policy.json","exchange-usage-policy.json","central-reservation-policy.json"):
 p=authority/name
 if p.is_file(): policies[name]=json.loads(p.read_text())
ceo=unit("venture-level2d-ceo.service")
cp=Path(ceo["WorkingDirectory"])/"artifacts/level2c-ceo/hierarchy-config.json"
cfg=json.loads(cp.read_text())
owner=unit("venture-owner-api.service")
owner_sources={rel:{"checkout":sha(P/rel),"installed":sha(Path(owner["WorkingDirectory"])/rel)} for rel in ("agents/ceo/owner_api.py","agents/ceo/owner_idea_inbox.py")}
print(json.dumps(dict(broker=broker,ceo=ceo,ceo_binding={k:cfg.get(k) for k in ("workflow_id","context","decomposition_workers")},signed_journal_verified=True,states=states,sources=sources,resource_tables=tables,policies=policies,owner_api=owner,owner_sources=owner_sources,provider_calls=0),indent=2))

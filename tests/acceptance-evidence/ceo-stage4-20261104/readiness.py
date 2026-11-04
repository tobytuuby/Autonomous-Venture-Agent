"""Bounded read-only readiness. No POST, model, environment or service mutation."""
import ast, hashlib, json, sqlite3, subprocess, sys, urllib.request, ssl
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
assert Path.cwd()==P
sys.dont_write_bytecode=True
OUT=P/"tests/acceptance-evidence/ceo-stage4-20261104"
CEO=Path("/usr/local/lib/venture-ceo-level2c")
BROKER=Path("/usr/local/lib/venture-control-broker-level2c")
cfg=json.loads((CEO/"artifacts/level2c-ceo/hierarchy-config.json").read_text())
def sha(b): return hashlib.sha256(b).hexdigest()
def ro(path):
 db=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=3)
 db.execute("PRAGMA query_only=ON")
 return db
def counts(path):
 if not path.exists(): return {"exists":False,"path":str(path),"resolved":str(path.resolve())}
 db=ro(path)
 try:
  result={}
  for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
   if not name.replace("_","").isalnum(): continue
   result[name]=db.execute('SELECT COUNT(*) FROM "'+name+'"').fetchone()[0]
  if "remote_executions" in result:
   result["remote_execution_status"]=dict(db.execute("SELECT status,COUNT(*) FROM remote_executions GROUP BY status"))
  if "calls" in result:
   result["calls_without_response"]=db.execute("SELECT COUNT(*) FROM calls WHERE response IS NULL").fetchone()[0]
  return {"exists":True,"path":str(path),"resolved":str(path.resolve()),"counts":result}
 finally: db.close()
r={"dependencies":[]}
# Traverse only project Python source imports from the seven scoped modules and entrypoints.
for tree in (CEO,BROKER):
 queue=["agents.ceo."+x for x in ("hierarchy_service","hierarchy_providers","provider_gateway","hierarchy_runner","hierarchy_research_daemon","ceo_research_review","provider_reservation","hierarchy_gateway")]
 seen=set()
 while queue and len(seen)<120:
  module=queue.pop()
  if module in seen: continue
  seen.add(module)
  rel=module.replace(".","/")+".py"
  target=tree/rel
  if not target.is_file():
   r["dependencies"].append({"tree":tree.name,"module":module,"missing":True});continue
  b=target.read_bytes()
  repo=P/rel
  r["dependencies"].append({"tree":tree.name,"module":module,"sha256":sha(b),"head_sha256":sha(repo.read_bytes()) if repo.is_file() else None,"matches_head":repo.is_file() and b==repo.read_bytes()})
  for node in ast.walk(ast.parse(b)):
   if isinstance(node,ast.ImportFrom) and node.module:
    if node.module.startswith(("agents.","kernel.")): queue.append(node.module)
    if node.module in ("agents.ceo","kernel.broker"):
     for n in node.names: queue.append(node.module+"."+n.name)
   if isinstance(node,ast.Import):
    queue.extend(n.name for n in node.names if n.name.startswith(("agents.","kernel.")))
paths=[tree/"artifacts/preparation-authority/resources.sqlite" for tree in (CEO,BROKER)]
state=Path(cfg["state_dir"])
local=list(state.rglob("*.sqlite"))
assert len(local)<=100
paths+=local
r["ledgers_before"]=[counts(p) for p in paths]
sys.path.insert(0,str(CEO))
from agents.ceo.hierarchy_client import HierarchyClient,NoRedirect
client=HierarchyClient(cfg["endpoint"],ca_file=cfg["ca_file"],client_cert=cfg["client_cert"],client_key=cfg["client_key"])
assert client.base=="https://localhost:8443"
context=ssl.create_default_context(cafile=cfg["ca_file"])
context.load_cert_chain(cfg["client_cert"],cfg["client_key"])
client.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context),NoRedirect())
from cryptography import x509
cert=x509.load_pem_x509_certificate(Path(cfg["client_cert"]).read_bytes())
r["identity"]={"configured_role":cfg["role"],"configured_actor":cfg["actor_id"],"certificate_subject":cert.subject.rfc4514_string(),"certificate_sha256":sha(Path(cfg["client_cert"]).read_bytes()),"os_user_probe":subprocess.check_output(["id","-un"],text=True).strip()}
try:
 index=client.research_list()
 r["live_read"]={"authenticated_get":True,"research_count":len(index),"states":[]}
 for entry in index[:30]:
  s=client.read(entry["workflow_id"])
  r["live_read"]["states"].append({"workflow_id":entry["workflow_id"],"state":s["state"],"revision":s["revision"],"snapshot_sha256":sha(json.dumps(s,sort_keys=True,separators=(",",":"),allow_nan=False).encode()),"disposed":s.get("research_disposition") is not None})
except Exception as e: r["live_read"]={"authenticated_get":False,"error_type":type(e).__name__}
r["ledgers_after"]=[counts(p) for p in paths]
r["ledger_counts_unchanged"]=r["ledgers_before"]==r["ledgers_after"]
(OUT/"readiness.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps({k:v for k,v in r.items() if k!="dependencies"},indent=2))

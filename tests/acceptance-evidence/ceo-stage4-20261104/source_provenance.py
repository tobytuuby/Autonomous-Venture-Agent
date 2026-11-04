"""Read-only source provenance; no environment, credentials, state writes or service mutations."""
import ast, difflib, hashlib, json, subprocess
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
assert Path.cwd()==P
OUT=P/"tests/acceptance-evidence/ceo-stage4-20261104"
def run(*args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=40)
 return dict(argv=list(args),exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
def sha(b): return hashlib.sha256(b).hexdigest()
r={"head":run("git","rev-parse","HEAD"),"date":run("date","-u","--iso-8601=seconds"),"tracked_status":run("git","status","--short","--untracked-files=no")}
r["services"]=run("systemctl","show","venture-owner-research-ceo.service","venture-control-broker-mtls.service","--property=Id,ActiveState,SubState,MainPID,NRestarts,ExecMainStartTimestamp,WorkingDirectory,Requires,After,KillMode,TimeoutStopUSec")
r["modules"]=[]
for tree,names in [("venture-ceo-level2c",["hierarchy_service","hierarchy_providers","provider_gateway"]),("venture-control-broker-level2c",["hierarchy_service","hierarchy_providers","provider_gateway","hierarchy_runner"])]:
 for name in names:
  rel="agents/ceo/"+name+".py"
  path=Path("/usr/local/lib")/tree/rel
  try: b=path.read_bytes()
  except OSError as e:
   r["modules"].append({"path":str(path),"error":str(e)});continue
  head=subprocess.check_output(["git","show","HEAD:"+rel])
  matches=[]
  for rev in subprocess.check_output(["git","log","--format=%H","--",rel],text=True).splitlines():
   old=subprocess.check_output(["git","show",rev+":"+rel])
   if old==b: matches.append(rev)
  imports=[]
  for node in ast.walk(ast.parse(b)):
   if isinstance(node,ast.ImportFrom): imports.append({"module":node.module,"names":[v.name for v in node.names],"level":node.level})
   if isinstance(node,ast.Import): imports.append({"module":[v.name for v in node.names]})
  label=tree+"-"+name
  (OUT/(label+".diff")).write_text("".join(difflib.unified_diff(b.decode().splitlines(True),head.decode().splitlines(True),fromfile=str(path),tofile="HEAD:"+rel)))
  r["modules"].append(dict(path=str(path),sha256=sha(b),head_sha256=sha(head),matches_head=b==head,historical_matches=matches,imports=imports,diff=label+".diff"))
(OUT/"observation.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r,indent=2))

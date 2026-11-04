"""Read existing advisory snapshot only; no consumer tick, signing or inference."""
import json,sys,os,fcntl
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
assert Path.cwd()==P
sys.path.insert(0,str(P))
from agents.ceo.authenticated_handoff import read_source
from agents.ceo.preparation_broker import read_scheduled
s=P/"artifacts/scheduled-ceo"
a=read_source(s)
with (s/"runner.lock").open("rb") as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 b=read_scheduled(s)
r={"verified_readers_agree":a==b,"item_id":a["id"],"item_status":a["status"],"review_present":a["review"] is not None,"decision_present":a["decision"] is not None,"review_source":a["review_source"]}
print(json.dumps(r,indent=2))
assert r["verified_readers_agree"]

"""Only the two owner-requested systemd mutations, guarded by fresh state."""
import json,subprocess
from pathlib import Path
assert Path.cwd()==Path("/home/epsilon/venture-control-workspace")
def props(u):
 s=subprocess.check_output(["systemctl","show",u,"--property=MainPID,ActiveState,SubState,UnitFileState"],text=True)
 return dict(l.split("=",1) for l in s.splitlines())
assert props("venture-level2c-ceo.service")==dict(MainPID="0",ActiveState="inactive",SubState="dead",UnitFileState="enabled")
assert props("venture-ceo-exercise.timer")==dict(ActiveState="active",SubState="waiting",UnitFileState="enabled")
assert props("venture-ceo-exercise.service")["ActiveState"]=="failed"
for u,pid in [("venture-owner-research-ceo.service","288443"),("venture-control-broker-mtls.service","288442")]:
 p=props(u);assert p["MainPID"]==pid and p["ActiveState"]=="active" and p["SubState"]=="running"
for args in [["sudo","-n","systemctl","disable","venture-level2c-ceo.service"],["sudo","-n","systemctl","disable","--now","venture-ceo-exercise.timer"]]:
 p=subprocess.run(args,text=True,capture_output=True)
 print(json.dumps(dict(command=args,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)),flush=True)
 assert p.returncode==0

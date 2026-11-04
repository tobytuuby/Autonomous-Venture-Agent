"""Validate captured observations without any runtime interaction."""
import json
from pathlib import Path
P=Path("tests/acceptance-evidence/ceo-legacy-units-20261104")
def read(n):return json.loads((P/n).read_text())
def units(r):
 return {d["Id"]:d for d in (dict(l.split("=",1) for l in s.splitlines() if "=" in l) for s in r["units"]["stdout"].strip().split("\n\n"))}
a,b=read("before.json"),read("final.json")
ua,ub=units(a),units(b)
checks={}
for name,pid in [("venture-owner-research-ceo.service","288443"),("venture-control-broker-mtls.service","288442")]:
 for k in ["MainPID","ActiveState","SubState","ExecMainStartTimestamp","NRestarts","User","Group","ExecStart","UnitFileState"]:
  assert ua[name][k]==ub[name][k],(name,k)
 assert ub[name]["MainPID"]==pid and ub[name]["ActiveState"]=="active"
 checks[name]="unchanged active identity/start/restarts/entrypoint"
assert ub["venture-level2c-ceo.service"]["UnitFileState"]=="disabled"
assert ub["venture-level2c-ceo.service"]["ActiveState"]=="inactive"
timer=ub["venture-ceo-exercise.timer"]
assert timer["UnitFileState"]=="linked" and timer["ActiveState"]=="failed" and timer["LoadState"]=="loaded"
assert not Path("/etc/systemd/system/timers.target.wants/venture-ceo-exercise.timer").exists()
for k in ["ActiveState","SubState","ExecMainStatus","ExecMainStartTimestamp","Result"]:
 assert ua["venture-ceo-exercise.service"][k]==ub["venture-ceo-exercise.service"][k],k
assert a["hashes"]==b["hashes"]
checks["all_271_source_unit_advisory_file_hashes_identical"]=len(b["hashes"])==271
assert (P/"health-before.log").read_bytes()==(P/"health-after.log").read_bytes()
h=read("health-after.log")
assert h["signed_journal"]["verified"] and h["service_uid_get"]["ok"] and h["counts_unchanged"]
assert all(s["matches_verified_journal"] for s in h["service_uid_get"]["snapshot_joins"])
assert (P/"consumers-before.log").read_bytes()==(P/"consumers-after.log").read_bytes()
checks.update(legacy_disabled=True,timer_stopped_not_enabled_definition_retained=True,advisory_failed_state_preserved=True,authenticated_get_and_signed_records_verified=True,accounting_and_pending_intent_unchanged=True,consumer_readers_unchanged=True)
for n in ["before","after","final","health-before","health-after","consumers-before","disable","retain-timer","tests"]:
 assert (P/(n+".exit")).read_text().strip()=="0",n
print(json.dumps(checks,indent=2))

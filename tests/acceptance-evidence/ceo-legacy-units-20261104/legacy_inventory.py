"""Read-only legacy dependency inventory; never read secret environment files."""
import hashlib,json,subprocess
from pathlib import Path
P=Path("/home/epsilon/venture-control-workspace")
assert Path.cwd()==P
def run(*a):
 p=subprocess.run(a,text=True,capture_output=True,timeout=45)
 return dict(command=list(a),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
units=["venture-level2c-ceo.service","venture-ceo-exercise.service","venture-ceo-exercise.timer","venture-owner-research-ceo.service","venture-control-broker-mtls.service","venture-level2d-ceo.service","venture-authenticated-handoff.service","venture-preparation-broker.service"]
props="Id,LoadState,User,Group,ExecStart,WorkingDirectory,MainPID,ActiveState,SubState,UnitFileState,ExecMainStartTimestamp,NRestarts,Result,ExecMainStatus,Requires,Wants,Requisite,BindsTo,PartOf,RequiredBy,WantedBy,BoundBy,ConsistsOf,TriggeredBy,Triggers,UpheldBy,OnFailure,OnSuccess,Before,After,FragmentPath,DropInPaths"
r={"date":run("date","-u","--iso-8601=seconds"),"units":run("systemctl","show",*units,"--property="+props),"inventory":run("systemctl","list-unit-files","*ceo*","--no-pager"),"definitions":run("systemctl","cat",*units)}
r["reverse"]={u:run("systemctl","list-dependencies","--reverse","--all",u,"--no-pager") for u in units[:3]}
pattern="venture-level2c-ceo|venture-ceo-exercise|scheduled-ceo|scheduled_exercise"
r["installed_references"]=run("grep","-RInE","--include=*.service","--include=*.timer","--include=*.target","--include=*.socket","--include=*.path",pattern,"/etc/systemd/system","/run/systemd/system","/usr/lib/systemd/system","/lib/systemd/system")
r["scheduler_references"]=run("grep","-RInE",pattern,"/etc/cron.d","/etc/cron.daily","/etc/cron.hourly","/etc/cron.weekly","/etc/cron.monthly","/etc/crontab","/var/spool/cron","/usr/local/bin","/usr/local/sbin")
r["repo_references"]=run("git","grep","-n","-E",pattern,"--","scripts","infrastructure","agents","tests/test*")
r["hashes"]={}
for root in [Path("/usr/local/lib/venture-ceo-level2c"),Path("/usr/local/lib/venture-control-broker-level2c")]:
 for f in sorted(root.rglob("*.py")):
  r["hashes"][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
for f in sorted((P/"artifacts/scheduled-ceo").rglob("*")):
 if f.is_file() and not f.is_symlink():r["hashes"][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
for u in units:
 f=Path("/etc/systemd/system")/u
 if f.is_file():r["hashes"][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
print(json.dumps(r,indent=2))

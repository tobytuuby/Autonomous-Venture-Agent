import hashlib, json, subprocess
from pathlib import Path
P = Path("/home/epsilon/venture-control-workspace")
assert Path.cwd() == P
def run(*args):
    p = subprocess.run(args, text=True, capture_output=True)
    return {"command": list(args), "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
report = {"head": run("git", "rev-parse", "HEAD"), "date": run("date", "-u", "--iso-8601=seconds")}
units = ["venture-owner-research-ceo.service", "venture-level2d-ceo.service", "venture-control-broker-mtls.service", "venture-level2c-ceo.service", "venture-ceo-exercise.service", "venture-ceo-exercise.timer"]
props = "Id,LoadState,ActiveState,SubState,UnitFileState,MainPID,ExecMainStartTimestamp,NRestarts,WorkingDirectory,FragmentPath,DropInPaths,ExecStart,Requires,Wants,RequiredBy,WantedBy,BoundBy,PartOf,ConsistsOf,TriggeredBy,UpheldBy"
report["units"] = run("systemctl", "show", *units, "--property=" + props)
report["ceo_inventory"] = run("systemctl", "list-unit-files", "*ceo*", "--no-pager")
report["reverse_dependencies"] = run("systemctl", "list-dependencies", "--reverse", "--all", "venture-level2d-ceo.service", "--no-pager")
report["unit_references"] = run("grep", "-RIl", "--include=*.service", "--include=*.timer", "--include=*.target", "--include=*.socket", "--include=*.path", "venture-level2d-ceo", "/etc/systemd/system", "/run/systemd/system", "/usr/lib/systemd/system", "/lib/systemd/system")
report["scheduled_references"] = run("grep", "-RIl", "venture-level2d-ceo", "/etc/cron.d", "/etc/cron.daily", "/etc/cron.hourly", "/var/spool/cron/crontabs", "/usr/local/bin", "/usr/local/sbin")
report["installed_units"] = run("systemctl", "cat", *units)
report["repo_references"] = run("git", "grep", "-n", "venture-level2d-ceo", "--", "scripts", "infrastructure", "agents", "tests/test*")
modules = ["hierarchy_service.py", "hierarchy_research_daemon.py", "hierarchy_gateway.py", "hierarchy_providers.py", "provider_gateway.py", "venture_workflow.py", "hierarchy_runner.py"]
report["modules"] = []
for root in [Path("/usr/local/lib/venture-ceo-level2c"), Path("/usr/local/lib/venture-control-broker-level2c")]:
    for module in modules:
        rel = "agents/ceo/" + module
        target = root / rel
        if target.exists():
            committed = subprocess.check_output(["git", "show", "HEAD:" + rel])
            report["modules"].append({"path": str(target), "sha256": sha(target), "head_sha256": hashlib.sha256(committed).hexdigest(), "matches_head": target.read_bytes() == committed})
report["python_binary"] = {"path": "/usr/bin/python3", "resolved": str(Path("/usr/bin/python3").resolve()), "sha256": sha("/usr/bin/python3"), "version": run("/usr/bin/python3", "--version")}
report["research_unit_matches_repo"] = Path("/etc/systemd/system/venture-owner-research-ceo.service").read_bytes() == (P / "infrastructure/systemd/venture-owner-research-ceo.service").read_bytes()
report["recent_research_errors"] = run("journalctl", "-u", "venture-owner-research-ceo.service", "--since=-10min", "--priority=err", "--no-pager", "--quiet", "--output=cat")
# Only counts are reported; application journal content may contain sensitive data.
j = report["recent_research_errors"]
j["line_count"] = len(j.pop("stdout").splitlines())
print(json.dumps(report, indent=2))

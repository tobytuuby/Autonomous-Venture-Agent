"""Bounded offline preparation manager. Never operational venture admission.

Run: PYTHONDONTWRITEBYTECODE=1 python3 ventures/venture-001/runtime/manager.py --run pilot-01
All generated state lives below this pilot's runtime/runs directory.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
from zipfile import ZipFile, BadZipFile

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
ROOT = PILOT.parents[1]
sys.path.insert(0, str(ROOT))
from kernel.p6.registry import LIVE_FIELDS
from kernel.workers.evidence import WorkerEvidenceBoundary

ROLES = ("research", "development", "testing", "security", "commercial")
INPUTS = ("product/restock.html", "product/START-HERE.md", "OFFER.md",
          "validation/test-restock.js", "validation/TEST-PLAN.md")
MAX_TASKS = 10
MODE = "offline_noncommercial_preparation"
DENIED = {name: False for name in LIVE_FIELDS}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe(base, relative):
    path = base / relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != base.parent):
        raise ValueError("symlinks denied")
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("path escape denied")
    return path

def request_guard(request):
    if set(request) != {"mode", "authorities"} or request["mode"] != MODE:
        raise PermissionError("only offline preparation; operational admission required elsewhere")
    if (not isinstance(request["authorities"], dict)
            or set(request["authorities"]) != set(DENIED)
            or any(value is not False for value in request["authorities"].values())):
        raise PermissionError("all live authorities denied")

class Manager:
    def __init__(self, run_id, request=None):
        request_guard(request if request is not None else {"mode": MODE, "authorities": DENIED})
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", run_id):
            raise ValueError("invalid run identity")
        self.home = safe(PILOT, "runtime/runs/" + run_id)
        self.home.mkdir(parents=True, exist_ok=True)
        self.lock = safe(self.home, "manager.lock").open("a")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError("manager already active")
        self.db = sqlite3.connect(safe(self.home, "state.sqlite"))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(
              id TEXT PRIMARY KEY, role TEXT NOT NULL, deps TEXT NOT NULL,
              attempt INTEGER NOT NULL, correction_of TEXT,
              status TEXT NOT NULL, record TEXT);
            CREATE TABLE IF NOT EXISTS events(
              sequence INTEGER PRIMARY KEY, body TEXT, previous TEXT, hash TEXT);
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT);
        """)
        self.verify_events()
        self.inputs = safe(self.home, "inputs")
        self.inputs.mkdir(exist_ok=True)
        fingerprint = canonical({p.name: digest(p) for p in
                                 (HERE / "manager.py", HERE / "worker.py", HERE / "containment.py")})
        old = self.db.execute("SELECT value FROM metadata WHERE key='runtime'").fetchone()
        if old and old[0] != fingerprint:
            self.close()
            raise ValueError("runtime changed; use a new run")
        if not old:
            for name in INPUTS:
                src = safe(PILOT, name)
                if src.is_file():
                    if src.stat().st_size > 1024 * 1024:
                        raise ValueError("input too large")
                    dest = safe(self.inputs, name)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dest)
            manifest = {str(p.relative_to(self.inputs)): digest(p)
                        for p in self.inputs.rglob("*") if p.is_file()}
            with self.db:
                self.db.execute("INSERT INTO metadata VALUES('runtime',?)", (fingerprint,))
                self.db.execute("INSERT INTO metadata VALUES('inputs',?)", (canonical(manifest),))
                self.event("initialized", {"mode": MODE, "inputs": manifest, **DENIED})
        manifest = json.loads(self.db.execute("SELECT value FROM metadata WHERE key='inputs'").fetchone()[0])
        for name, sha in manifest.items():
            if digest(safe(self.inputs, name)) != sha:
                raise ValueError("input snapshot integrity failure")

    def close(self):
        self.db.close()
        self.lock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def event(self, action, detail):
        body = canonical({"action": action, "detail": detail})
        row = self.db.execute("SELECT hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        previous = row[0] if row else "GENESIS"
        sha = hashlib.sha256((previous + body).encode()).hexdigest()
        self.db.execute("INSERT INTO events(body,previous,hash) VALUES(?,?,?)",
                        (body, previous, sha))

    def verify_events(self):
        previous = "GENESIS"
        for row in self.db.execute("SELECT * FROM events ORDER BY sequence"):
            sha = hashlib.sha256((previous + row["body"]).encode()).hexdigest()
            if row["previous"] != previous or row["hash"] != sha:
                raise ValueError("event chain integrity failure")
            previous = sha

    def tasks(self):
        return [dict(row, deps=json.loads(row["deps"]),
                     record=json.loads(row["record"]) if row["record"] else None)
                for row in self.db.execute("SELECT * FROM tasks ORDER BY rowid")]

    def assign(self, role, deps=(), correction_of=None):
        if role not in ROLES or len(self.tasks()) >= MAX_TASKS:
            raise ValueError("worker/task bound denied")
        tasks = {t["id"]: t for t in self.tasks()}
        if any(d not in tasks for d in deps):
            raise ValueError("unknown dependency")
        if correction_of:
            original = tasks[correction_of]
            if original["attempt"] >= 2 or original["status"] != "rejected":
                raise ValueError("correction bound denied")
            attempt = 2
        else:
            if any(t["role"] == role for t in tasks.values()):
                return
            attempt = 1
        identity = role + "-" + str(attempt)
        with self.db:
            self.db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,'pending',NULL)",
                            (identity, role, canonical(list(deps)), attempt, correction_of))
            self.event("assignment", {"id": identity, "role": role, "dependencies": list(deps),
                                     "correction_of": correction_of,
                                     "correction_scope": {"action": "clean rerun from immutable snapshot",
                                                          "prior_failure": tasks[correction_of]["record"]} if correction_of else None,
                                     "backend": "fixed_local_program",
                                     "timeout_seconds": 15, "max_artifact_bytes": 2097152})

    def effective(self, identity):
        tasks = self.tasks()
        correction = next((t for t in tasks if t["correction_of"] == identity), None)
        return correction or next(t for t in tasks if t["id"] == identity)

    def update(self, task, status, record):
        with self.db:
            self.db.execute("UPDATE tasks SET status=?,record=? WHERE id=?",
                            (status, canonical(record), task["id"]))
            self.event(status, {"id": task["id"], "record": record})

    def validate(self, task, out, exit_status):
        if exit_status != 0:
            return ["worker exited unsuccessfully"]
        try:
            result = json.loads(safe(out, "result.json").read_text())
            if task["role"] == "development":
                with ZipFile(safe(out, "review-kit.zip")) as z:
                    if sorted(z.namelist()) != ["START-HERE.md", "restock.html"] or z.testzip():
                        raise ValueError("invalid package")
                    for name in z.namelist():
                        if hashlib.sha256(z.read(name)).hexdigest() != digest(self.inputs / "product" / name):
                            raise ValueError("package source mismatch")
            elif task["role"] == "testing":
                if result["exit_status"] != 0 or "PASS:" not in safe(out, "assertions.log").read_text():
                    raise ValueError("assertions failed")
            elif task["role"] == "security":
                if result["findings"]:
                    raise ValueError("static findings require human remediation")
            elif task["role"] == "research":
                if not result["inventory"]:
                    raise ValueError("no source evidence")
            elif task["role"] == "commercial":
                if result["demand_verified"] is not False or result["sales"] != 0:
                    raise ValueError("unsupported commercial claim")
            return []
        except (OSError, ValueError, KeyError, TypeError, BadZipFile) as exc:
            return ["artifact review failed: " + type(exc).__name__]

    def dispatch(self, task):
        # Caller cannot substitute arbitrary commands, paths or authorities.
        current = next((t for t in self.tasks() if t["id"] == task.get("id")), None)
        if current != task or task["status"] != "pending":
            raise PermissionError("unregistered assignment")
        if any(self.effective(d)["status"] != "accepted" for d in task["deps"]):
            raise PermissionError("dependency not accepted")
        attempt = safe(self.home, task["id"])
        attempt.mkdir(exist_ok=False)
        source, out = attempt / "inputs", attempt / "outputs"
        shutil.copytree(self.inputs, source)
        out.mkdir()
        for dep in task["deps"]:
            actual = self.effective(dep)
            if actual["role"] == "development":
                item = safe(self.home, actual["id"] + "/outputs/review-kit.zip")
                shutil.copyfile(item, source / "review-kit.zip")
        command = [sys.executable, "-I", "-S", "-B", str(HERE / "worker.py"),
                   task["role"], str(source), str(out)]
        self.update(task, "running", {"command": command})
        log = attempt / "worker.log"
        code = -1
        failure = None
        with log.open("wb") as stream:
            try:
                proc = subprocess.Popen(command, cwd=attempt, stdout=stream, stderr=subprocess.STDOUT,
                                        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                                        start_new_session=True)
                try:
                    code = proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    failure = "timeout"
            except OSError as exc:
                failure = type(exc).__name__
        defects = self.validate(task, out, code)
        artifacts = []
        for p in sorted(out.rglob("*")):
            if p.is_symlink():
                defects.append("symlink artifact denied")
            elif p.is_file():
                if p.stat().st_size > 2097152:
                    defects.append("artifact too large")
                else:
                    artifacts.append({"path": str(p.relative_to(self.home)), "sha256": digest(p),
                                      "bytes": p.stat().st_size})
        record = {"command": command, "exit_status": code, "failure": failure,
                  "defects": defects, "artifacts": artifacts,
                  "log": str(log.relative_to(self.home)), "log_sha256": digest(log),
                  "backend": "fixed_local_program", "agent_inference": False}
        boundary = WorkerEvidenceBoundary()
        boundary.accept(task["id"], tuple(a["sha256"] for a in artifacts), bool(defects))
        if not boundary.manager_may_treat_as_clean(task["id"]):
            defects.append("worker evidence tainted")
        self.update(task, "rejected" if defects else "accepted", record)

    def step(self):
        # Interrupted attempts are never assumed successful or silently reused.
        for t in self.tasks():
            if t["status"] == "running":
                self.update(t, "rejected", {"failure": "interrupted; execution outcome unknown"})
            elif t["status"] == "accepted":
                if digest(safe(self.home, t["record"]["log"])) != t["record"]["log_sha256"]:
                    raise ValueError("accepted log integrity failure")
                for artifact in t["record"]["artifacts"]:
                    if digest(safe(self.home, artifact["path"])) != artifact["sha256"]:
                        raise ValueError("accepted artifact integrity failure")
        for t in self.tasks():
            if t["status"] == "rejected" and t["attempt"] == 1:
                if not any(x["correction_of"] == t["id"] for x in self.tasks()):
                    self.assign(t["role"], t["deps"], t["id"])
        if not self.tasks():
            self.assign("research")
        if self.effective("research-1")["status"] == "accepted":
            # Grow graph from the actual source inventory and available deliverables.
            if (self.inputs / "product/restock.html").exists() and (self.inputs / "product/START-HERE.md").exists():
                self.assign("development", ["research-1"])
                self.assign("security", ["development-1"])
                if (self.inputs / "validation/test-restock.js").exists():
                    self.assign("testing", ["development-1"])
            if (self.inputs / "OFFER.md").exists():
                self.assign("commercial", ["research-1"])
        for t in self.tasks():
            if t["status"] == "pending" and all(self.effective(d)["status"] == "accepted" for d in t["deps"]):
                self.dispatch(t)
                return True
        return False

    def bundle(self):
        tasks = self.tasks()
        effective = [self.effective(t["id"]) for t in tasks if t["attempt"] == 1]
        result = {"mode": MODE, "approval_status": "UNAPPROVED_PILOT",
                  "operational_admission": "NOT_REQUESTED",
                  "review_decision": "offline_preparation_review_only",
                  "status": "complete" if len(effective) == 5 and all(t["status"] == "accepted" for t in effective) else "incomplete",
                  "tasks": tasks, "authorities": DENIED,
                  "capabilities": {"local_fixed_programs": list(ROLES), "ai_agents": "unavailable/not invoked",
                                   "browser": "not dispatched", "network": "denied",
                                   "development": "packaging existing files only",
                                   "corrections": "one clean rerun; source remediation requires human review"},
                  "limitations": "No live market validation, autonomous code authoring, browser proof or security certification. SQLite/event hashes are local evidence, not external audit anchoring."}
        (self.home / "integrated-review.json").write_text(json.dumps(result, indent=2) + "\n")
        events = [dict(r) for r in self.db.execute("SELECT * FROM events ORDER BY sequence")]
        (self.home / "decision-log.json").write_text(json.dumps(events, indent=2) + "\n")
        return result

    def run(self):
        while self.step():
            pass
        return self.bundle()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True)
    args = p.parse_args()
    with Manager(args.run) as manager:
        result = manager.run()
        print(json.dumps({"status": result["status"], "bundle": str(manager.home / "integrated-review.json")}))
        return 0 if result["status"] == "complete" else 1

if __name__ == "__main__":
    raise SystemExit(main())

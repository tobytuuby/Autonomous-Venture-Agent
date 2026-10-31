#!/usr/bin/env python3
"""Scoped Control retirement deployment. Requires explicit installed-target authority.

Run from the approved checkout with --apply after review. Never signs, reserves,
calls a provider, starts a CEO, or changes a trust pin or historical ledger row.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import sqlite3
import stat
import subprocess
import sys

P = Path("/home/epsilon/venture-control-workspace")
R = Path("/usr/local/lib/venture-control-broker-level2c")
A = R / "artifacts/preparation-authority"
BROKER = "venture-control-broker-mtls.service"
CEO = "venture-level2d-ceo.service"
OLD_SHA = "3d968c3e978cfd508fd085c898beca90bcc2e8db0ed375d6ad07560f091fd8c9"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unit(name):
    return dict(line.split("=", 1) for line in subprocess.check_output(
        ["systemctl", "show", name, "--property=ActiveState,MainPID,WorkingDirectory"],
        text=True).splitlines())


def regular(path):
    assert not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
    info = path.stat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    return info


def atomic(path, raw, info):
    temporary = path.with_name(path.name + ".retirement-tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            os.fchown(handle.fileno(), info.st_uid, info.st_gid)
            os.fchmod(handle.fileno(), stat.S_IMODE(info.st_mode))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def snapshot():
    result = {}
    for name in ("resources.sqlite", "hierarchy/workflow.sqlite", "hierarchy/inbox.sqlite"):
        path = A / name
        regular(path)
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            tables = sorted(row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"))
            result[name] = {}
            for table in tables:
                rows = sorted(db.execute('SELECT * FROM "' + table.replace('"', '""') + '"'), key=repr)
                result[name][table] = dict(rows=len(rows), sha256=sha(repr(rows).encode()))
    return result


def verify_journal(trust_path):
    sys.path.insert(0, str(R))
    from agents.ceo.control_plane import load_trust
    from agents.ceo.venture_workflow import VentureWorkflow
    uid = pwd.getpwnam("venture-broker").pw_uid
    os.setresuid(uid, uid, 0)
    try:
        trust = load_trust(trust_path)
        assert all(actor in trust for actor in ("service-worker", "worker-a", "worker-b", "worker-c"))
        journal = VentureWorkflow.__new__(VentureWorkflow)
        journal.actors = trust
        journal.db = sqlite3.connect((A / "hierarchy/workflow.sqlite").as_uri() + "?mode=ro", uri=True)
        journal.db.execute("PRAGMA query_only=ON")
        try:
            journal.verify()
            states = {flow: json.loads(raw) for flow, raw in journal.db.execute("SELECT id,snapshot FROM inbox")}
            with sqlite3.connect((A / "resources.sqlite").as_uri() + "?mode=ro", uri=True) as db:
                requests = [json.loads(row[0]) for row in db.execute("SELECT request FROM worker_reservations")]
            shared = [r for r in requests if states[r["workflow_id"]]["venture_id"] == "venture-verification"]
            cap = min([4] + [r["policy"]["maximum_requests"] for r in shared])
            return dict(journal_verified=True, legacy_trust_retained=True,
                        venture="venture-verification", used=len(shared), ceiling=cap,
                        remaining=max(0, cap - len(shared)))
        finally:
            journal.close()
    finally:
        os.setresuid(0, 0, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", required=True)
    parser.parse_args()
    assert Path.cwd().resolve() == P and os.geteuid() == 0
    assert (P / "artifacts/level2d-retirement-tests-final.exit").read_text().strip() == "0"
    assert unit(CEO)["ActiveState"] == "inactive"
    before_unit = unit(BROKER)
    assert before_unit["ActiveState"] == "active" and Path(before_unit["WorkingDirectory"]) == R
    # Read only the selected trust path; never report the process environment.
    environment = dict(part.split("=", 1) for part in
        Path("/proc", before_unit["MainPID"], "environ").read_bytes().decode().split("\0") if "=" in part)
    trust_path = Path(environment["VENTURE_BROKER_HIERARCHY_TRUST"])
    assert trust_path.is_relative_to(R)
    source = P / "agents/ceo/worker_inference.py"
    target = R / "agents/ceo/worker_inference.py"
    policy_path = A / "worker-inference-policy.json"
    for path in (source, target, policy_path, trust_path):
        regular(path)
    old_policy = json.loads(policy_path.read_bytes())
    new_policy = json.loads((P / "infrastructure/level2d-active-worker-policy.json").read_bytes())
    assert old_policy["actor_ids"] == ["service-worker", "worker-a", "worker-b", "worker-c"]
    assert dict(old_policy, actor_ids=new_policy["actor_ids"]) == new_policy
    assert new_policy["actor_ids"] == ["worker-a", "worker-b", "worker-c"]
    assert sha(target.read_bytes()) == OLD_SHA
    changes = [(target, source.read_bytes()), (policy_path, (json.dumps(new_policy, indent=2) + "\n").encode())]
    saved = [(path, path.read_bytes(), regular(path)) for path, _ in changes]
    trust_before = sha(trust_path.read_bytes())
    backup = P / "artifacts/level2d-retirement-private-backups"
    backup.mkdir(mode=0o700, exist_ok=False)
    for index, (path, raw, _) in enumerate(saved):
        fd = os.open(backup / (str(index) + "-" + path.name), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
    stopped = False
    try:
        subprocess.run(["systemctl", "stop", BROKER], check=True)
        stopped = True
        rows_before = snapshot()
        budget = verify_journal(trust_path)
        for name in rows_before:
            with sqlite3.connect((A / name).as_uri() + "?mode=ro", uri=True) as src:
                destination = backup / Path(name).name
                with sqlite3.connect(destination) as dst:
                    src.backup(dst)
                os.chmod(destination, 0o600)
        for (path, raw), (_, old, info) in zip(changes, saved):
            assert path.read_bytes() == old, "concurrent installed change"
            atomic(path, raw, info)
        subprocess.run(["systemctl", "start", BROKER], check=True)
        after_unit = unit(BROKER)
        assert after_unit["ActiveState"] == "active" and after_unit["MainPID"] != before_unit["MainPID"]
        assert unit(CEO)["ActiveState"] == "inactive"
        assert snapshot() == rows_before, "historical ledger changed"
        assert sha(trust_path.read_bytes()) == trust_before
        assert verify_journal(trust_path) == budget
        assert all(path.read_bytes() == raw for path, raw in changes)
        print(json.dumps(dict(
            classification="operator-executed Control retirement and verified retained signed journal",
            broker=after_unit, policy=new_policy, allocation=budget,
            decision="DO_NOT_KICKOFF" if budget["remaining"] < 3 else "REQUIRES_REMAINING_PREFLIGHT",
            ledger_tables=rows_before, historical_rows_unchanged=True,
            trust_sha256=trust_before, installed_sha256=sha(source.read_bytes()),
            provider_calls=0, signatures_created=0, ceo_started=False,
            target_provider_acceptance="NOT_RUN", live_legacy_denial="NOT_RUN",
            ledger_reset=False, caps_changed=False), indent=2, sort_keys=True))
    except BaseException:
        if stopped:
            subprocess.run(["systemctl", "stop", BROKER], check=False)
            for path, raw, info in reversed(saved):
                atomic(path, raw, info)
            subprocess.run(["systemctl", "start", BROKER], check=False)
        raise


if __name__ == "__main__":
    main()

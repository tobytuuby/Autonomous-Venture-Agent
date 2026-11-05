"""Bounded read-only detection over existing Control SQLite state.

Never constructs a runtime store, reconciles an intent, or grants resume authority.
Only project-contained explicit paths are accepted; no production key discovery.
"""
import json
import os
from pathlib import Path
import sqlite3
import stat
import time

from agents.ceo.escalation_inbox import inside_root, canonical, digest, identifier
from agents.ceo.venture_workflow import VentureWorkflow

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 5000
SECONDS = 2.0


class BoundaryHold(ValueError):
    pass


def fingerprint(path):
    result = []
    for candidate in (path, *(Path(str(path) + s) for s in ("-wal", "-shm", "-journal"))):
        if candidate.is_symlink() or any(p.is_symlink() for p in candidate.parents):
            raise BoundaryHold("PATH_ALIAS")
        try:
            s = candidate.stat()
        except FileNotFoundError:
            result.append(None)
            continue
        if (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1
                or s.st_uid != os.geteuid() or s.st_mode & 0o077
                or s.st_size > MAX_BYTES):
            raise BoundaryHold("PRIVATE_BOUNDED_FILE_REQUIRED")
        result.append((s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns))
    if result[0] is None:
        raise BoundaryHold("STATE_MISSING")
    # Even a read-only SQLite WAL open can create/update shared-memory sidecars.
    # Reject sidecars before AND after immutable reads; never treat ignored WAL
    # bytes as safe resume evidence. Immutable prevents sidecar writes even if
    # a writer races the open. Concurrent reads remain detection only.
    if any(x is not None for x in result[1:]):
        raise BoundaryHold("SQLITE_SIDECAR_PRESENT")
    return tuple(result)


def rows(db, table, columns):
    value = db.execute("SELECT " + columns + " FROM " + table).fetchmany(MAX_ROWS + 1)
    if len(value) > MAX_ROWS:
        raise BoundaryHold("ROW_BOUND")
    return value


def tables(db, required, optional=()):
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not set(required) <= names or names - set(required) - set(optional):
        raise BoundaryHold("UNKNOWN_SCHEMA")
    if db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('view','trigger')").fetchone():
        raise BoundaryHold("UNKNOWN_SCHEMA")
    return names


def resource_state(db):
    names = tables(db, ("reservations", "exchange_sessions", "exchange_calls",
                        "remote_reservations"),
                   ("remote_executions", "worker_reservations", "worker_executions",
                    "worker_research_charges"))
    # All tables are bounded, including historical rows not otherwise examined.
    for name in names:
        rows(db, name, "*")
    reservations = dict(rows(db, "remote_reservations", "identity,request"))
    charged = dict(rows(db, "reservations", "identity,tokens"))
    joined = dict(rows(db, "exchange_calls", "identity,session"))
    sessions = dict(rows(db, "exchange_sessions", "session,binding"))
    executions = dict((r[0], r[1:]) for r in rows(
        db, "remote_executions", "identity,request,response,status")) if "remote_executions" in names else {}
    if any(rows(db, name, "*") for name in names if name.startswith("worker_")):
        raise BoundaryHold("WORKER_STATE_REQUIRES_SEPARATE_PROOF")
    if set(reservations) != set(charged) or set(joined) != set(reservations) or set(executions) - set(reservations):
        raise BoundaryHold("INCONSISTENT_RESERVATIONS")
    for identity, wire in reservations.items():
        saved = json.loads(wire)
        if (canonical(saved) != wire or saved["context"]["session_id"] != joined[identity]
                or joined[identity] not in sessions or type(charged[identity]) is not int
                or charged[identity] != saved["policy"]["maximum_output_tokens"]
                or sessions[joined[identity]] != digest(canonical(dict(
                    context=saved["context"], policy=saved["policy"])).encode())
                or identity != digest(canonical(dict(domain="preparation-exchange-call-v1",
                    session=joined[identity], actor=saved["actor"], identity=saved["identity"])).encode())):
            raise BoundaryHold("INCONSISTENT_RESERVATIONS")
        execution = executions.get(identity)
        if execution is None:
            raise BoundaryHold("RESERVED_NOT_COMPLETED")
        request, response, status = execution
        if status == "PENDING":
            raise BoundaryHold("PROVIDER_OUTCOME_PENDING")
        payload = json.loads(request)
        if (status != "COMPLETE" or response is None
                or payload["reservation"] != saved
                or digest(canonical(payload["request"]).encode()) != saved["request_sha256"]
                or type(json.loads(response)) is not dict):
            raise BoundaryHold("UNKNOWN_EXECUTION")
    return len(executions)


def assess(*, workflow, resources, ceo_calls, actors):
    """Detection only. actors must be independently pinned public keys.

    Stable samples cannot exclude a later writer, rollback or omitted runtime
    state. In particular this does not verify provider execution or safe resume.
    """
    report = dict(decision="HOLD", deployment_allowed=False, resume_verified=False,
                  dry_run=True, classification="READ_ONLY_BOUNDARY_DETECTION",
                  observation="UNKNOWN", reasons=[], provider_calls=0)
    connections = []
    deadline = time.monotonic() + SECONDS
    try:
        paths = [inside_root(p) for p in (workflow, resources, ceo_calls)]
        if len(set(paths)) != 3:
            raise BoundaryHold("DISTINCT_STATE_PATHS_REQUIRED")
        before = [fingerprint(p) for p in paths]
        versions = []
        for path in paths:
            db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True,
                                 timeout=0, isolation_level=None)
            connections.append(db)
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1024 * 1024)
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise BoundaryHold("UNSUPPORTED_JOURNAL_MODE")
            versions.append(db.execute("PRAGMA data_version").fetchone()[0])
            db.execute("BEGIN")
        wdb, rdb, cdb = connections
        tables(wdb, ("inbox", "audit"))
        rows(wdb, "audit", "sequence")
        rows(wdb, "inbox", "id")
        roles, keys = [], []
        for actor, (role, key) in actors.items():
            identifier(actor)
            if role not in {"ceo", "manager", "worker", "owner", "security"} or type(key) is not bytes or len(key) != 32:
                raise BoundaryHold("INVALID_PUBLIC_PINS")
            roles.append(role)
            keys.append(key)
        if (not keys or len(set(keys)) != len(keys)
                or roles.count("ceo") != 1 or roles.count("owner") != 1):
            raise BoundaryHold("INVALID_PUBLIC_PINS")
        verifier = object.__new__(VentureWorkflow)
        verifier.actors, verifier.db = dict(actors), wdb
        verifier.verify()  # Existing signed lineage verifier, no constructor/read mutator.
        states = [json.loads(raw)["state"] for raw, in rows(wdb, "inbox", "snapshot")]
        complete = resource_state(rdb)
        tables(cdb, ("calls",))
        calls = rows(cdb, "calls", "identity,request,response,attempt")
        for _, request, response, attempt in calls:
            if response is None:
                raise BoundaryHold("CEO_INTENT_PENDING")
            if (not attempt or type(json.loads(request)) is not dict
                    or type(json.loads(response)) is not dict):
                raise BoundaryHold("UNKNOWN_CEO_INTENT")
        if any(s not in {"TERMINATED", "OWNER_REJECTED", "BUDGET_EXHAUSTED"} for s in states):
            raise BoundaryHold("SIGNED_WORKFLOW_UNRESOLVED")
        for db in connections:
            db.execute("ROLLBACK")
        if ([fingerprint(p) for p in paths] != before or any(
                db.execute("PRAGMA data_version").fetchone()[0] != v
                for db, v in zip(connections, versions))):
            raise BoundaryHold("RACING_STATE_CHANGE")
        if time.monotonic() > deadline:
            raise BoundaryHold("SNAPSHOT_TIME_BOUND")
        report["observation"] = "COMPLETED_DETECTED" if complete or calls else "QUIESCENT_DETECTED"
        report["reasons"] = ["PROCESS_ISOLATION_AND_STATE_COVERAGE_UNVERIFIED",
                             "TECHNICAL_DEPLOYMENT_GATES_REMAIN_REQUIRED"]
    except BoundaryHold as exc:
        report["reasons"] = [str(exc)]
    except Exception:
        # Never expose SQLite contents, prompts, responses, paths or exception text.
        report["reasons"] = ["INVALID_OR_UNREADABLE_STATE"]
    finally:
        for db in connections:
            db.close()
    return report

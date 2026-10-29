"""Central paid inference ceilings only. No execution, payment or launch authority."""
import os
import sqlite3
import stat
from types import SimpleNamespace

from agents.ceo.escalation_inbox import canonical, digest, exact, identifier, inside_root
from agents.ceo import service_identity

RESERVATION_PATH = "/v1/inference/reservations"
MAX_RESERVATION = 8192


def reserve_exchange(payload, *, actor, role="manager"):
    """Trusted broker callback; actor comes from TLS pin configuration, never JSON.

    A CEO-established session is mandatory. Exact retry of one durable intent is
    idempotent; a fresh intent for the same logical call is a replay and denied.
    """
    from agents.ceo.preparation_exchange import StandingModel
    exact(payload, ("context", "actor", "role", "identity", "request_sha256",
                    "attempt", "policy", "endpoint", "model"))
    if role not in ("ceo", "manager") or payload["role"] != role or payload["actor"] != actor:
        raise ValueError("reservation role denied")
    identifier(payload["identity"])
    for field in ("request_sha256", "attempt"):
        value = payload[field]
        if (type(value) is not str or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value)):
            raise ValueError("reservation digest denied")
    context = payload["context"]
    exact(context, ("session_id", "venture_id", "ceo_id", "manager_id", "objective", "rounds"))
    identifier(context["session_id"])
    if context[role + "_id"] != actor:
        raise ValueError("reservation context recipient denied")
    authority = service_identity.ProviderQuota(service_identity.AUTHORITY_DIRECTORY)
    live_policy = authority.authority()
    if any(name in live_policy["revoked"] for name in
           (actor, "service-ceo", "service-manager", "service-worker")):
        raise ValueError("standing authority revoked")
    # Reuse the standing policy validator with authoritative Control files.
    checker = StandingModel.__new__(StandingModel)
    checker.authority, checker.epoch = authority, authority.authority()["epoch"]
    checker.context, checker.actor, checker.role = context, actor, role
    checker.provider = SimpleNamespace(endpoint=payload["endpoint"], model=payload["model"])
    policy = checker._policy()
    if policy != payload["policy"]:
        raise ValueError("standing policy changed")
    binding = digest(canonical(dict(context=context, policy=policy)).encode())
    call = digest(canonical(dict(domain="preparation-exchange-call-v1",
        session=context["session_id"], actor=actor, identity=payload["identity"])).encode())
    wire = canonical(payload)
    path = inside_root(authority.directory / "resources.sqlite")
    # Only the authenticated CEO may bootstrap broker-owned quota state.
    if not path.exists() and role == "ceo":
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise ValueError("private resource ledger required")
    db = sqlite3.connect(path, isolation_level=None, timeout=5)
    try:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        if role == "ceo":
            db.execute("CREATE TABLE IF NOT EXISTS reservations(day TEXT, identity TEXT UNIQUE, tokens INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS exchange_sessions(session TEXT PRIMARY KEY, binding TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS exchange_calls(identity TEXT PRIMARY KEY, session TEXT)")
        db.execute("""CREATE TABLE IF NOT EXISTS remote_reservations(
            identity TEXT PRIMARY KEY, request TEXT NOT NULL)""")
        session = context["session_id"]
        row = db.execute("SELECT binding FROM exchange_sessions WHERE session=?", (session,)).fetchone()
        if row is None:
            if role != "ceo":
                raise ValueError("CEO-established Control session required")
            db.execute("INSERT INTO exchange_sessions VALUES(?,?)", (session, binding))
        elif row[0] != binding:
            raise ValueError("Control session binding required")
        prior = db.execute("SELECT request FROM remote_reservations WHERE identity=?", (call,)).fetchone()
        if prior:
            if prior[0] != wire:
                raise ValueError("changed or replayed reservation")
        else:
            count = db.execute("SELECT COUNT(*) FROM exchange_calls WHERE session=?", (session,)).fetchone()[0]
            if count >= policy["maximum_requests"]:
                raise ValueError("standing session inference ceiling reached")
            db.execute("INSERT INTO exchange_calls VALUES(?,?)", (call, session))
            authority._reserve_daily(db, call, policy["maximum_output_tokens"])
            db.execute("INSERT INTO remote_reservations VALUES(?,?)", (call, wire))
        db.execute("COMMIT")
    except BaseException:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()
    return dict(reserved=True, request_sha256=digest(wire.encode()),
                maximum_output_tokens=policy["maximum_output_tokens"],
                scope="PREPARATION_ONLY")

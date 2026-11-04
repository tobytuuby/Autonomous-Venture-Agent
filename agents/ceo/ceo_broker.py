"""CEO-only proof over the existing broker ledger; no schema or state writes.

POST carries an exact bounded request so prompts and identities stay out of URLs.
The proof returns only typed statuses and digests, never prompts or responses.
"""
import os
import sqlite3
import stat

from agents.ceo.escalation_inbox import canonical, digest, exact, inside_root
from agents.ceo.provider_reservation import validate_exchange

PROOF_PATH = "/v1/inference/ceo-proof"
EXECUTE_PATH = "/v1/inference/ceo-execute"
DOMAIN = "ceo-broker-proof-v1"


def ceo_proof(payload, *, actor, hierarchy):
    exact(payload, ("reservation", "request"))
    reservation, request = payload["reservation"], payload["request"]
    if actor != "service-ceo" or reservation.get("execution_mode") != "CONTROL_LEDGER_V1":
        raise ValueError("tracked CEO proof required")
    authority, policy, binding, call, wire = validate_exchange(
        reservation, actor=actor, role="ceo")
    exact(request, ("system", "json_object_mode", "opportunity"))
    if (request["json_object_mode"] is not True
            or digest(canonical(request).encode()) != reservation["request_sha256"]):
        raise ValueError("exact CEO request required")
    from agents.ceo.provider_gateway import validate_ceo_review
    validate_ceo_review(request, reservation, actor, hierarchy)
    path = inside_root(authority.directory / "resources.sqlite")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise ValueError("private central ledger required")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        db.execute("BEGIN")
        session = db.execute("SELECT binding FROM exchange_sessions WHERE session=?",
                             (reservation["context"]["session_id"],)).fetchone()
        if session is None or session[0] != binding:
            raise ValueError("existing exact CEO session required")
        row = db.execute("SELECT request FROM remote_reservations WHERE identity=?", (call,)).fetchone()
        charged = db.execute("SELECT tokens FROM reservations WHERE identity=?", (call,)).fetchone()
        joined = db.execute("SELECT session FROM exchange_calls WHERE identity=?", (call,)).fetchone()
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='remote_executions'").fetchone()
        execution = (db.execute("SELECT request,response,status FROM remote_executions WHERE identity=?",
                                (call,)).fetchone() if exists else None)
        if row is None:
            if charged is not None or joined is not None or execution is not None:
                raise ValueError("inconsistent CEO reservation evidence")
            reserved, status = "ABSENT", "NOT_STARTED"
        else:
            if (row[0] != wire or charged != (policy["maximum_output_tokens"],)
                    or joined != (reservation["context"]["session_id"],)):
                raise ValueError("original exact CEO reservation required")
            reserved, status = "EXACT", "NOT_STARTED"
            if execution is not None:
                if (execution[0] != canonical(payload)
                        or execution[2] not in ("PENDING", "COMPLETE")
                        or (execution[2] == "PENDING" and execution[1] is not None)
                        or (execution[2] == "COMPLETE" and execution[1] is None)):
                    raise ValueError("inconsistent CEO execution evidence")
                status = execution[2]
        return dict(domain=DOMAIN, session_sha256=binding,
                    reservation_sha256=digest(wire.encode()),
                    request_sha256=reservation["request_sha256"],
                    reservation_status=reserved, execution_status=status)
    finally:
        db.close()


def execute_ceo(payload, *, actor, hierarchy, provider):
    """Use only an already charged exact reservation; ambiguous calls stay held."""
    proof = ceo_proof(payload, actor=actor, hierarchy=hierarchy)
    if proof["reservation_status"] != "EXACT" or proof["execution_status"] == "PENDING":
        raise ValueError("original unambiguous CEO reservation required")
    from agents.ceo.provider_gateway import execute_reserved
    return execute_reserved(payload, actor=actor, role="ceo",
                            hierarchy=hierarchy, provider=provider)

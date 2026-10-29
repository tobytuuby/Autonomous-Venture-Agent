#!/usr/bin/env python3
"""Root-controlled snapshot bridge: owner triage feedback to CEO advisory inbox.

The export is informational. It cannot become an Ed25519 owner approval,
venture admission, funding authorization, or business execution instruction.
"""
import json
import os
import pathlib
import sqlite3
import sys
import tempfile
from agents.ceo.escalation_inbox import canonical

def export(review_db,destination):
    src=sqlite3.connect("file:"+str(review_db)+"?mode=ro",uri=True)
    try:
        records=[dict(cycle_id=r[0],proposal_digest=r[1],decision=r[2],
                      reason=r[3],reviewed_utc=r[4])
                 for r in src.execute(
                 "SELECT cycle_id,proposal_digest,decision,reason,created_utc FROM owner_idea_reviews ORDER BY id")]
    finally:
        src.close()
    data=dict(domain="owner-idea-research-feedback-v1",advisory_only=True,
              venture_admission=False,financial_authority=False,records=records)
    dest=pathlib.Path(destination)
    if not dest.parent.is_dir() or dest.is_symlink():
        raise ValueError("safe existing destination directory required")
    fd,name=tempfile.mkstemp(prefix=".feedback-",dir=dest.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write((canonical(data)+"\n").encode());f.flush();os.fsync(f.fileno())
        os.chmod(name,0o600)
        import pwd
        user=pwd.getpwnam("venture-ceo")
        os.chown(name,user.pw_uid,user.pw_gid)
        os.replace(name,dest)
        dfd=os.open(dest.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    finally:
        if os.path.exists(name):os.unlink(name)
    return len(records)

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: publish_owner_idea_feedback.py DB DEST")
    print("owner-feedback-records-published",export(sys.argv[1],sys.argv[2]))

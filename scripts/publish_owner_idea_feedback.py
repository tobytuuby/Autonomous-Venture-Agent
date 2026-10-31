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
from agents.ceo.owner_idea_inbox import digest as proposal_digest

def export(review_db,destination,discovery_db=None):
    src=sqlite3.connect("file:"+str(review_db)+"?mode=ro",uri=True)
    try:
        records=[dict(cycle_id=r[0],proposal_digest=r[1],decision=r[2],
                      reason=r[3],reviewed_utc=r[4])
                 for r in src.execute(
                 "SELECT cycle_id,proposal_digest,decision,reason,created_utc FROM owner_idea_reviews ORDER BY id")]
    finally:
        src.close()
    assignments=[]
    if discovery_db is not None:
        source=sqlite3.connect('file:'+str(discovery_db)+'?mode=ro',uri=True)
        try:
            proposals={}
            for cycle,raw in source.execute("SELECT cycle_id,result FROM discovery WHERE state='COMPLETE'"):
                for proposal in json.loads(raw)['proposals']:
                    key=(cycle,proposal_digest(proposal))
                    if key in proposals:
                        raise ValueError('ambiguous proposal identity')
                    proposals[key]=proposal
        finally:
            source.close()
        for record in records:
            if record['decision']!='APPROVE_FOR_RESEARCH':
                continue
            key=(record['cycle_id'],record['proposal_digest'])
            if key not in proposals:
                raise ValueError('owner decision references missing or altered proposal')
            assignments.append(dict(cycle_id=record['cycle_id'],proposal_digest=record['proposal_digest'],
                reviewed_utc=record['reviewed_utc'],proposal=proposals[key],
                scope='INTERNAL_RESEARCH_ONLY',status='APPROVED_NOT_ASSIGNED'))
    data=dict(domain='owner-idea-research-feedback-v1',advisory_only=True,
              venture_admission=False,financial_authority=False,records=records,
              research_assignments=assignments)
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
    if len(sys.argv) not in (3,4):raise SystemExit('usage: publish_owner_idea_feedback.py DB DEST [DISCOVERY_DB]')
    print('owner-feedback-records-published',export(sys.argv[1],sys.argv[2],
        sys.argv[3] if len(sys.argv)==4 else None))

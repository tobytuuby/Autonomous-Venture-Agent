#!/usr/bin/env python3
"""One-time, evidence-preserving recovery of denied Level2D worker reservations."""
import hashlib, json, os, pathlib, shutil, sqlite3, subprocess, tempfile

FLOW = "level2d-multiworker-remediation-1"
OLD = ["service-worker","worker-a","worker-b","worker-c"]
NEW = ["worker-a","worker-b","worker-c"]
EXPECTED = {
 "worker-a": ("A","worker-A-2994d91b72bf616168f658f700db15a057f8f6e0c5e51840c1","b869452025c5c3ce0bf90e8367335d6a2d9b8d6e5bbf68d2a3ad1463ba64a1e1"),
 "worker-b": ("B","worker-B-2994d91b72bf616168f658f700db15a057f8f6e0c5e51840c1","b5a258b8ab5aed1236a0617e3b359bd3da98cae0476e2cdd4814c84b10f46d91"),
}
suffix=".pre-denied-reservation-recovery-20261031"
plans={}
if os.geteuid()!=0:
    raise SystemExit("Run as root via sudo")
for actor in NEW:
    c=pathlib.Path("/var/lib/venture-"+actor+"/level2d/hierarchy-config.json")
    cfg=json.loads(c.read_text())
    if (cfg.get("role"),cfg.get("actor_id"),cfg.get("workflow_id"))!=("worker",actor,FLOW):
        raise SystemExit("DENIED unexpected config "+actor)
    f=pathlib.Path(cfg["policy"])
    d=json.loads(f.read_text())
    if (d.get("domain")!="worker-preparation-inference-v1" or d.get("model")!="gpt-6-luna"
        or d.get("epoch")!=2 or d.get("maximum_requests")!=4 or d.get("maximum_output_tokens")!=1024
        or d.get("actor_ids") not in (OLD,NEW)):
        raise SystemExit("DENIED unexpected policy "+actor)
    db=pathlib.Path(cfg["state_dir"])/"inference.sqlite"
    plans[actor]=(f,d,db)
for actor in EXPECTED:
    assignment,identity,hash_expected=EXPECTED[actor]
    db=plans[actor][2]
    con=sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True)
    row=con.execute("SELECT request,response,attempt FROM calls WHERE identity=?",(identity,)).fetchone()
    con.close()
    if row is None or row[1] is not None or hashlib.sha256(row[0].encode()).hexdigest()!=hash_expected:
        raise SystemExit("DENIED intent evidence mismatch "+actor)
    req=json.loads(row[0])["opportunity"]
    if (req.get("workflow_id"),req.get("assignment_id"),req.get("role"),req.get("state"))!=(FLOW,assignment,"worker","WORKER_PENDING"):
        raise SystemExit("DENIED unexpected request "+actor)
# All preflight checks passed; stop every Worker before backing up or changing state.
for actor in NEW:
    subprocess.run(["systemctl","stop","venture-level2d-worker@"+actor+".service"],check=True)
for actor,(f,d,db) in plans.items():
    if d["actor_ids"]!=NEW:
        backup=pathlib.Path(str(f)+suffix)
        if backup.exists(): raise SystemExit("DENIED existing policy backup "+actor)
        shutil.copy2(f,backup)
        st=f.stat()
        fd,tmp=tempfile.mkstemp(prefix=".policy-repair-",dir=str(f.parent))
        try:
            with os.fdopen(fd,"w") as out:
                d["actor_ids"]=NEW
                json.dump(d,out,indent=2,sort_keys=True)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
            os.chown(tmp,st.st_uid,st.st_gid)
            os.chmod(tmp,st.st_mode & 0o777)
            os.replace(tmp,f)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    print(actor,"three-worker policy verified",flush=True)
# Denied local intents never reached the central reservation ledger, as independently
# verified on Venture-Control. Preserve entire original local DB and all other rows.
for actor,(assignment,identity,hash_expected) in EXPECTED.items():
    db=plans[actor][2]
    backup=pathlib.Path(str(db)+suffix)
    if backup.exists(): raise SystemExit("DENIED existing database backup "+actor)
    con=sqlite3.connect(db,timeout=5)
    dest=sqlite3.connect(backup)
    con.backup(dest)
    dest.close()
    os.chmod(backup,0o600)
    try:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT request,response FROM calls WHERE identity=?",(identity,)).fetchone()
        if row is None or row[1] is not None or hashlib.sha256(row[0].encode()).hexdigest()!=hash_expected:
            raise RuntimeError("intent changed during recovery")
        count=con.execute("DELETE FROM calls WHERE identity=? AND response IS NULL AND request=?",(identity,row[0])).rowcount
        if count!=1: raise RuntimeError("recovery changed unexpected row count")
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    print(actor,"denied local intent archived and reconciled",flush=True)
for actor in NEW:
    subprocess.run(["systemctl","start","venture-level2d-worker@"+actor+".service"],check=True)
print("Workers restarted; central signed journal and provider quota ledger untouched.")

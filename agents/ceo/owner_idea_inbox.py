"""Owner-only proposal triage. Never produces venture admission or capital authority.

Private localhost web service, separate from agent identity. The human's
credential must be supplied out-of-band, not from model or repository.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from agents.ceo.escalation_inbox import canonical

DECISIONS=("APPROVE_FOR_RESEARCH","REJECT","REQUEST_CHANGES")
MAX_BODY=2048

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

class OwnerIdeaInbox:
    def __init__(self,discovery_db,decisions_db):
        self.discovery=Path(discovery_db)
        self.decisions=Path(decisions_db)
        if not self.discovery.is_file() or not self.decisions.parent.is_dir():
            raise ValueError("existing private discovery and review directories required")
        db=sqlite3.connect(self.decisions)
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS owner_idea_reviews(
                id INTEGER PRIMARY KEY AUTOINCREMENT,cycle_id TEXT NOT NULL,
                proposal_digest TEXT NOT NULL, decision TEXT NOT NULL,
                reason TEXT NOT NULL,created_utc TEXT NOT NULL,
                UNIQUE(cycle_id,proposal_digest))""")
            db.commit()
        finally:
            db.close()

    def ideas(self):
        with closing(sqlite3.connect("file:"+str(self.discovery)+"?mode=ro",uri=True)) as db:
            rows=db.execute("SELECT cycle_id,result FROM discovery WHERE state='COMPLETE' ORDER BY created_utc DESC").fetchall()
        with closing(sqlite3.connect(self.decisions)) as db:
            reviews={(r[0],r[1]):dict(decision=r[2],reason=r[3],reviewed_utc=r[4])
                     for r in db.execute("SELECT cycle_id,proposal_digest,decision,reason,created_utc FROM owner_idea_reviews")}
        progress={}
        status_file=self.decisions.parent/'research-status.json'
        if status_file.exists():
            if status_file.is_symlink() or not status_file.is_file() or status_file.stat().st_size>65536:
                raise ValueError('invalid private research status file')
            data=json.loads(status_file.read_text())
            if (data.get('domain')!='owner-research-progress-v1'
                    or data.get('financial_authority') is not False
                    or data.get('venture_admission') is not False
                    or data.get('advisory_only') is not True):
                raise ValueError('invalid research status authority')
            stamp=datetime.fromisoformat(data['generated_utc'])
            stale=not stamp.tzinfo or (datetime.now(timezone.utc)-stamp).total_seconds()>1800
            progress={(r['cycle_id'],r['proposal_digest']):dict(r,stale=stale,generated_utc=data['generated_utc'])
                     for r in data['records']}
        output=[]
        for cycle,wire in rows:
            report=json.loads(wire)
            for proposal in report["proposals"]:
                fingerprint=digest(proposal)
                review=reviews.get((cycle,fingerprint))
                research=progress.get((cycle,fingerprint)) if review and review['decision']=='APPROVE_FOR_RESEARCH' else None
                output.append(dict(cycle_id=cycle,digest=fingerprint,
                                   proposal=proposal,review=review,research=research))
        return output

    def review(self,cycle_id,proposal_digest,decision,reason):
        if (type(cycle_id) is not str or not re.fullmatch("[a-zA-Z0-9-]{1,60}",cycle_id)
            or type(proposal_digest) is not str or not re.fullmatch("[0-9a-f]{64}",proposal_digest)
            or decision not in DECISIONS or type(reason) is not str
            or len(reason)>500 or (decision=="REQUEST_CHANGES" and not reason.strip())):
            raise ValueError("invalid owner review")
        matching=[x for x in self.ideas() if x["cycle_id"]==cycle_id and x["digest"]==proposal_digest]
        if len(matching)!=1:
            raise ValueError("unknown or changed proposal")
        if matching[0]["review"] is not None:
            raise ValueError("already reviewed; request a new proposal version")
        with closing(sqlite3.connect(self.decisions,timeout=5)) as db:
            db.execute("INSERT INTO owner_idea_reviews(cycle_id,proposal_digest,decision,reason,created_utc) VALUES(?,?,?,?,?)",
                       (cycle_id,proposal_digest,decision,reason,datetime.now(timezone.utc).isoformat()))
            db.commit()
        return dict(saved=True,venture_admitted=False,capital_allocated=False)

PAGE="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Venture Ideas · Owner Review</title>
<style>body{font:16px system-ui,sans-serif;background:#f6f8fb;color:#15263b;margin:0}header{background:#12263e;color:#fff;padding:25px max(24px,calc((100% - 1080px)/2))}main{max-width:1080px;margin:25px auto;padding:0 18px}article{background:white;border:1px solid #d8e0ea;border-radius:13px;padding:23px;margin-bottom:17px;box-shadow:0 3px 12px #21314b0b}h1,h2{margin:0 0 12px}small,.sub{color:#60728a}.tag{border-radius:100px;padding:5px 10px;background:#eaf1fc;color:#215493;font-size:12px}dl{display:grid;grid-template-columns:165px 1fr;gap:10px}dt{font-weight:bold;color:#56657a}dd{margin:0}textarea{width:98%;min-height:52px;padding:8px;border:1px solid #c6cfda;border-radius:7px}button{padding:12px 16px;border:0;border-radius:7px;margin:7px 7px 0 0;cursor:pointer;background:#2262ad;color:white;font-weight:bold}button.reject{background:#9f3446}button.changes{background:#596679}.done{color:#245e40;font-weight:bold}@media(max-width:620px){dl{grid-template-columns:1fr}}</style></head><body><header><h1>Venture ideas</h1><div>Independent owner review · No funds are released by these decisions</div></header><main><p class="sub">Approve ideas for more research, reject them, or request changes. Formal venture authorization and funding are separate.</p><div id="items">Loading proposals…</div></main>
<script>
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function load(){const r=await fetch('/api/ideas');if(!r.ok){document.querySelector('#items').textContent='Authentication required.';return}const ideas=await r.json();document.querySelector('#items').innerHTML=ideas.length?ideas.map((x,i)=>{const p=x.proposal;return '<article><span class="tag">'+esc(x.cycle_id)+'</span><h2>'+esc(p.title)+'</h2><dl>'+['customer','problem','solution','demand_hypothesis','acquisition_hypothesis','estimated_setup_usd','major_risk','validation_plan'].map(k=>'<dt>'+esc(k.replaceAll('_',' '))+'</dt><dd>'+esc(k==='estimated_setup_usd'?'$'+p[k]+' (unverified)':p[k])+'</dd>').join('')+'</dl>'+(x.review?'<p class="done">Decision: '+esc(x.review.decision.replaceAll('_',' '))+'</p>':'<label for="reason'+i+'">Reason or requested changes</label><textarea id="reason'+i+'" maxlength="500"></textarea><div><button data-i="'+i+'" data-decision="APPROVE_FOR_RESEARCH">Approve research</button><button class="reject" data-i="'+i+'" data-decision="REJECT">Reject</button><button class="changes" data-i="'+i+'" data-decision="REQUEST_CHANGES">Request changes</button></div>')+'</article>'}).join(''):'<p>No CEO proposals yet.</p>';document.querySelectorAll('button[data-i]').forEach(b=>b.addEventListener('click',async()=>{const x=ideas[Number(b.dataset.i)];const decision=b.dataset.decision;const reason=document.getElementById('reason'+b.dataset.i).value;if(decision==='REQUEST_CHANGES'&&!reason.trim()){alert('Enter requested changes first.');return}if(!confirm('Save '+decision.replaceAll('_',' ').toLowerCase()+' for '+x.proposal.title+'?'))return;const r=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json','X-Owner-Intent':'explicit'},body:JSON.stringify({cycle_id:x.cycle_id,proposal_digest:x.digest,decision,reason})});if(!r.ok){alert('Review not saved: '+(await r.text()).slice(0,160));return}await load()}))}
load().catch(()=>{document.querySelector('#items').textContent='Could not load review queue.'});
</script></body></html>"""

def serve(inbox, token, *,host="127.0.0.1",port=8791):
    if not token or len(token)<32:
        raise ValueError("owner-held token required")
    class Handler(BaseHTTPRequestHandler):
        def authorized(self):
            actual=self.headers.get("Authorization","")
            expected="Basic "+base64.b64encode(("owner:"+token).encode()).decode()
            return hmac.compare_digest(actual,expected)
        def send(self,status,body,ctype="application/json"):
            raw=body.encode()
            self.send_response(status)
            self.send_header("Content-Type",ctype)
            if status==401:
                self.send_header("WWW-Authenticate",'Basic realm="Venture Owner Review", charset="UTF-8"')
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.authorized():return self.send(401,'{"error":"owner authentication required"}')
            if urlsplit(self.path).path=="/":return self.send(200,PAGE,"text/html; charset=utf-8")
            if self.path=="/api/ideas":return self.send(200,canonical(inbox.ideas()))
            return self.send(404,'{"error":"not found"}')
        def do_POST(self):
            if not self.authorized():return self.send(401,'{"error":"owner authentication required"}')
            if self.path!="/api/review" or self.headers.get("X-Owner-Intent")!="explicit":return self.send(403,'{"error":"review intent required"}')
            try:
                n=int(self.headers.get("Content-Length","0"))
                if not 0<n<=MAX_BODY or self.headers.get("Transfer-Encoding"):raise ValueError("bounded request required")
                value=json.loads(self.rfile.read(n))
                if type(value) is not dict or set(value)!={"cycle_id","proposal_digest","decision","reason"}:raise ValueError("invalid review")
                out=inbox.review(**value)
                return self.send(200,canonical(out))
            except (ValueError,sqlite3.IntegrityError,json.JSONDecodeError):
                return self.send(409,'{"error":"invalid, stale or already reviewed"}')
        def log_message(self,*args):
            pass
    ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--discovery-db",required=True);p.add_argument("--review-db",required=True)
    p.add_argument("--port",type=int,default=8791)
    a=p.parse_args()
    serve(OwnerIdeaInbox(a.discovery_db,a.review_db),os.environ.get("OWNER_IDEA_REVIEW_TOKEN"),port=a.port)

"""Bounded, proposal-only CEO opportunity discovery; never performs business actions."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from agents.ceo.escalation_inbox import canonical, exact
from agents.ceo.venture_exercise import strict_json

PROMPT = ("You are an internal venture discovery analyst, NOT a legal officer. "
          "Only produce a JSON object with key proposals containing exactly 3 entries. "
          "Each entry has exactly title, customer, problem, solution, demand_hypothesis, "
          "acquisition_hypothesis, estimated_setup_usd, major_risk, validation_plan. "
          "These are unverified hypotheses, not market research. No tools, purchases, "
          "customer contact, venture creation, transactions, financial authorization or launch. "
          "Favor simple online software/services needing no inventory. Each entry must "
          "be distinct and feasible to investigate under a $100 seed cap. "
          "Give concise strings and all costs in nonnegative integer USD.")
FIELDS = ("title","customer","problem","solution","demand_hypothesis",
          "acquisition_hypothesis","estimated_setup_usd","major_risk","validation_plan")

def validate(result):
    exact(result,("proposals",))
    items=result["proposals"]
    if type(items) is not list or len(items)!=3:
        raise ValueError("three proposals required")
    names=set()
    for item in items:
        exact(item,FIELDS)
        for key in FIELDS:
            if key=="estimated_setup_usd":
                if type(item[key]) is not int or not 0<=item[key]<=100:
                    raise ValueError("unapproved seed range")
            elif type(item[key]) is not str or not 3<=len(item[key])<=450:
                raise ValueError("invalid proposal field")
        if item["title"].casefold() in names:
            raise ValueError("duplicate proposal")
        names.add(item["title"].casefold())
    return items

def generate(db_path, provider, *, cycle_id):
    if not cycle_id.isascii() or not cycle_id.replace("-","").isalnum() or len(cycle_id)>60:
        raise ValueError("cycle identity denied")
    db=sqlite3.connect(db_path,isolation_level=None,timeout=5)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("""CREATE TABLE IF NOT EXISTS discovery(
          cycle_id TEXT PRIMARY KEY, state TEXT NOT NULL,
          result TEXT, created_utc TEXT NOT NULL)""")
        db.execute("BEGIN IMMEDIATE")
        prior=db.execute("SELECT state,result FROM discovery WHERE cycle_id=?",(cycle_id,)).fetchone()
        if prior:
            db.execute("COMMIT")
            if prior[0]!="COMPLETE":
                raise ValueError("ambiguous prior inference; no automatic retry")
            return json.loads(prior[1])
        db.execute("INSERT INTO discovery VALUES(?,?,NULL,?)",
                   (cycle_id,"PENDING",datetime.now(timezone.utc).isoformat()))
        db.execute("COMMIT")
    finally:
        db.close()
    request=dict(system=PROMPT,json_object_mode=True,
       opportunity=dict(scope="IDEAS_ONLY",venture_seed_ceiling_usd=100,
                        portfolio_pool_usd=1000,owner_approval_required=True))
    result=provider(request,())
    if type(result) is not dict or result.get("tool_call") is not None:
        raise ValueError("provider tools forbidden")
    proposals=validate(strict_json(result["decision"]["content"]))
    report=dict(cycle_id=cycle_id,state="PROPOSED_FOR_OWNER_DISCUSSION",
        generated_utc=datetime.now(timezone.utc).isoformat(),proposals=proposals,
        independent_market_evidence=False,owner_approved=False,
        venture_funding_authorized=False,external_actions_allowed=False)
    wire=canonical(report)
    db=sqlite3.connect(db_path,isolation_level=None,timeout=5)
    try:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT state FROM discovery WHERE cycle_id=?",(cycle_id,)).fetchone()
        if row!=("PENDING",):
            raise ValueError("discovery checkpoint changed")
        db.execute("UPDATE discovery SET state='COMPLETE',result=? WHERE cycle_id=?",(wire,cycle_id))
        db.execute("COMMIT")
    finally:
        db.close()
    return report

def main():
    import argparse,os
    from agents.ceo.venture_exercise import configured_provider
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",required=True)
    parser.add_argument("--cycle",required=True)
    args=parser.parse_args()
    provider=configured_provider(os.environ,required=True)
    if provider.model!="gpt-6-sol":
        raise ValueError("CEO model policy denied")
    provider.maximum_output_tokens=1800
    report=generate(args.db,provider,cycle_id=args.cycle)
    print(canonical(report))

if __name__=="__main__":
    main()

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.ceo.owner_idea_inbox import digest

MODULE = Path(__file__).resolve().parents[1] / "scripts/publish_owner_idea_feedback.py"
spec = importlib.util.spec_from_file_location("publisher_under_test", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PROPOSAL = dict(title="Verified sample", customer="Test users", problem="Test problem",
                solution="Test solution", demand_hypothesis="Unverified",
                acquisition_hypothesis="Unverified", estimated_setup_usd=10,
                major_risk="No demand", validation_plan="Compare public alternatives")

class ResearchFeedbackTests(unittest.TestCase):
    def test_digest_bound_approved_proposal_export_and_tampering_denial(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            discovery, reviews, output = p/"discovery.db",p/"reviews.db",p/"feedback.json"
            with sqlite3.connect(discovery) as db:
                db.execute("CREATE TABLE discovery(cycle_id TEXT,state TEXT,result TEXT)")
                db.execute("INSERT INTO discovery VALUES(?,?,?)",
                           ("first","COMPLETE",json.dumps({"proposals":[PROPOSAL]})))
            with sqlite3.connect(reviews) as db:
                db.execute("CREATE TABLE owner_idea_reviews(id INTEGER,cycle_id TEXT,proposal_digest TEXT,decision TEXT,reason TEXT,created_utc TEXT)")
                db.execute("INSERT INTO owner_idea_reviews VALUES(1,?,?,?,?,?)",
                           ("first",digest(PROPOSAL),"APPROVE_FOR_RESEARCH","","now"))
            with patch.object(mod.os,"chown"):
                self.assertEqual(mod.export(reviews,output,discovery),1)
            result=json.loads(output.read_text())
            self.assertEqual(result["research_assignments"][0]["proposal"],PROPOSAL)
            self.assertEqual(result["research_assignments"][0]["status"],"APPROVED_NOT_ASSIGNED")
            self.assertFalse(result["financial_authority"])
            self.assertFalse(result["venture_admission"])
            with sqlite3.connect(discovery) as db:
                altered=dict(PROPOSAL,title="Changed after approval")
                db.execute("UPDATE discovery SET result=?",
                           (json.dumps({"proposals":[altered]}),))
            with self.assertRaisesRegex(ValueError,"missing or altered"):
                with patch.object(mod.os,"chown"):
                    mod.export(reviews,output,discovery)
            self.assertEqual(json.loads(output.read_text()),result)

if __name__=="__main__":
    unittest.main()

import importlib.util,json,sqlite3,tempfile,unittest
from unittest.mock import patch
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/"scripts/publish_owner_idea_feedback.py"
spec=importlib.util.spec_from_file_location("feedback_publisher",MODULE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class FeedbackTest(unittest.TestCase):
 def test_advisory_export_cannot_impersonate_financial_approval(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);src=root/'reviews.sqlite';dst=root/'feedback.json'
   db=sqlite3.connect(src)
   db.execute('CREATE TABLE owner_idea_reviews(id INTEGER PRIMARY KEY,cycle_id TEXT,proposal_digest TEXT,decision TEXT,reason TEXT,created_utc TEXT)')
   db.execute('INSERT INTO owner_idea_reviews VALUES(1,?,?,?,?,?)',("cycle","a"*64,"APPROVE_FOR_RESEARCH","Research only","2026-10-29"))
   db.commit();db.close()
   with patch.object(mod.os,"chown"):
    self.assertEqual(mod.export(src,dst),1)
   value=json.loads(dst.read_text())
   self.assertTrue(value["advisory_only"])
   self.assertFalse(value["venture_admission"])
   self.assertFalse(value["financial_authority"])
   self.assertEqual(value["records"][0]["decision"],"APPROVE_FOR_RESEARCH")

if __name__=="__main__":unittest.main()

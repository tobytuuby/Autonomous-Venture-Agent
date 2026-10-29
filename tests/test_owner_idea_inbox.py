import json,sqlite3,tempfile,unittest
from pathlib import Path
from agents.ceo.owner_idea_inbox import OwnerIdeaInbox

class OwnerIdeaInboxTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  root=Path(self.tmp.name);self.source=root/'discovery.sqlite'
  db=sqlite3.connect(self.source)
  db.execute('CREATE TABLE discovery(cycle_id TEXT PRIMARY KEY,state TEXT,result TEXT,created_utc TEXT)')
  self.idea={"title":"Starter idea","customer":"Small nonprofits","problem":"Reminders are hard"}
  self.idea.update({k:"Research hypothesis" for k in
      ("solution","demand_hypothesis","acquisition_hypothesis","major_risk","validation_plan")})
  self.idea['estimated_setup_usd']=40
  db.execute('INSERT INTO discovery VALUES(?,?,?,?)',
      ("cycle-1","COMPLETE",json.dumps({"proposals":[self.idea]}),"2026-10-29"));db.commit();db.close()
  self.inbox=OwnerIdeaInbox(self.source,root/'reviews.sqlite')
 def test_review_approval_only_for_research_and_duplicate_rejected(self):
  idea=self.inbox.ideas()[0]
  result=self.inbox.review("cycle-1",idea["digest"],"APPROVE_FOR_RESEARCH","")
  self.assertFalse(result["venture_admitted"])
  self.assertFalse(result["capital_allocated"])
  self.assertEqual(self.inbox.ideas()[0]["review"]["decision"],"APPROVE_FOR_RESEARCH")
  with self.assertRaises(ValueError):
   self.inbox.review("cycle-1",idea["digest"],"REJECT","")
 def test_reject_and_changes_require_exact_proposal(self):
  d=self.inbox.ideas()[0]["digest"]
  with self.assertRaises(ValueError):
   self.inbox.review("cycle-1","0"*64,"REJECT","")
  with self.assertRaises(ValueError):
   self.inbox.review("cycle-1",d,"REQUEST_CHANGES","")
  self.inbox.review("cycle-1",d,"REQUEST_CHANGES","Add customer evidence")
  self.assertEqual(self.inbox.ideas()[0]["review"]["reason"],"Add customer evidence")

if __name__=="__main__":
 unittest.main()

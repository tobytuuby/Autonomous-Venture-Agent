import json,sqlite3,tempfile,unittest
from pathlib import Path
from agents.ceo.venture_discovery import generate,FIELDS

class DiscoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.db=Path(self.temp.name)/'discovery.sqlite'
  self.calls=0
 def provider(self,request,tools):
  self.calls+=1
  assert tools==()
  assert request["opportunity"]["owner_approval_required"] is True
  items=[]
  for i in range(3):
   d={k:"A bounded research hypothesis" for k in FIELDS}
   d["title"]="Venture "+str(i)
   d["estimated_setup_usd"]=80
   items.append(d)
  return dict(decision=dict(content=json.dumps(dict(proposals=items))),tool_call=None)
 def test_proposals_are_unapproved_and_exact_retry_is_read_only(self):
  a=generate(self.db,self.provider,cycle_id="review-1")
  self.assertEqual(a["state"],"PROPOSED_FOR_OWNER_DISCUSSION")
  self.assertFalse(a["external_actions_allowed"])
  self.assertFalse(a["venture_funding_authorized"])
  self.assertEqual(generate(self.db,self.provider,cycle_id="review-1"),a)
  self.assertEqual(self.calls,1)
 def test_ambiguous_checkpoint_blocks_second_paid_call(self):
  def crash(request,tools):
   self.calls+=1
   raise RuntimeError("provider unavailable")
  with self.assertRaises(RuntimeError):
   generate(self.db,crash,cycle_id="review-2")
  with self.assertRaisesRegex(ValueError,"ambiguous"):
   generate(self.db,self.provider,cycle_id="review-2")
  self.assertEqual(self.calls,1)
 def test_bad_response_stays_fail_closed(self):
  def invalid(request,tools):
   return dict(decision=dict(content='{"proposals":[]}'),tool_call=None)
  with self.assertRaises(ValueError):
   generate(self.db,invalid,cycle_id="review-3")
  con=sqlite3.connect(self.db)
  self.assertEqual(con.execute("SELECT state FROM discovery").fetchone()[0],"PENDING")

if __name__=="__main__":
 unittest.main()

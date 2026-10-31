import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.ceo.owner_idea_inbox import digest
from agents.ceo.escalation_inbox import canonical

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/publish_owner_research_status.py'
spec=importlib.util.spec_from_file_location('owner_research_status',SCRIPT)
publisher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
PROPOSAL=dict(title='Test tutor assessment',customer='Tutors',problem='Recap burden',
    solution='Template',demand_hypothesis='Unverified',acquisition_hypothesis='Unverified',
    estimated_setup_usd=20,major_risk='Weak willingness to pay',validation_plan='Internal comparison')
FINGERPRINT=digest(PROPOSAL)
FLOW='research-'+FINGERPRINT[:24]

class Broker:
    def research_list(self):
        return [dict(workflow_id=FLOW,state='MANAGER_REVIEW')]
    def read(self,flow):
        assert flow==FLOW
        return dict(id=FLOW,venture_id=FLOW,state='MANAGER_REVIEW',mode='PREPARATION_ONLY',
            revision=3,scope=dict(seed_cents=1),scope_hash='scope',
            operational_authority=False,external_actions_allowed=False,
            execution_performed=False,money_released=False,
            handoff=dict(item_id=FLOW,review=dict(item_id=FLOW)),evidence={})
    def load(self,ref):
        raise AssertionError('no evidence supplied')

class ResearchProgressTests(unittest.TestCase):
    def test_only_authoritative_workflow_state_produces_progress(self):
        entry=dict(cycle_id='c1',proposal_digest=FINGERPRINT,proposal=PROPOSAL,
                   scope='INTERNAL_RESEARCH_ONLY',status='APPROVED_NOT_ASSIGNED')
        feedback=dict(domain='owner-idea-research-feedback-v1',advisory_only=True,
                      financial_authority=False,venture_admission=False,
                      research_assignments=[entry],
                      records=[dict(cycle_id='c1',proposal_digest=FINGERPRINT,decision='APPROVE_FOR_RESEARCH')])
        result=publisher.collect({},feedback,client=Broker())
        self.assertEqual(result['records'][0]['research_status'],'MANAGER_REVIEW')
        self.assertEqual(result['records'][0]['artifacts'],[])
        self.assertFalse(result['venture_admission'])
        modified=json.loads(json.dumps(feedback))
        modified['research_assignments'][0]['proposal']['title']='changed'
        with self.assertRaisesRegex(ValueError,'changed or missing'):
            publisher.collect({},modified,client=Broker())

if __name__=='__main__':
    unittest.main()

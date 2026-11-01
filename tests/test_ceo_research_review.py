import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption
from agents.ceo.escalation_inbox import canonical
from agents.ceo.ceo_research_review import review, validate_recommendation, SYSTEM
from agents.ceo.venture_workflow import hashed

def assessment(quote, recommendation='NEEDS_MORE_RESEARCH'):
    text = ('Verified facts: The signed draft contains the quoted finding.\n'
            'Inference: A bounded validation proposal may be useful.\n'
            'Evidence [1]: "' + quote + '"')
    if recommendation == 'NEEDS_MORE_RESEARCH':
        text += '\nAnswerable: Existing public descriptions can clarify substitutes.'
        task = 'Desk research: Compare existing public descriptions with the signed draft.'
    elif recommendation in ('READY_FOR_OWNER_DISCUSSION', 'PROCEED_TO_MVP'):
        text += ('\nCustomer: Small studio operators.\nProblem: Missed restock decisions.'
                 '\nValidation: Low-risk internal prototype with synthetic inventory.')
        task = ('Internal MVP: Blocked because current signed scope covers research only.'
                if recommendation == 'PROCEED_TO_MVP' else
                'Owner proposal: Seek separately authorized internal prototype scope.')
    else:
        text += '\nBlocker: The cited evidence prevents safe validation of this premise.'
        task = 'Disposition: Defer this premise pending resolution of the cited blocker.'
    return dict(recommendation=recommendation, assessment=text,
        evidence_gaps='Unknown: Buyer demand and named competitors remain unverified.\n'
                      'Question: Which substitutes cover the draft workflow?',
        next_internal_task=task)


class FakeModel:
    model='gpt-6-sol'
    def __init__(self, recommendation='NEEDS_MORE_RESEARCH', mutate=None):
        self.calls=0; self.last_request=None
        self.recommendation=recommendation; self.mutate=mutate
    def __call__(self,request,tools):
        self.calls+=1; self.last_request=request
        assert tools==()
        assert request['opportunity']['external_market_evidence_verified'] is False
        result=assessment(request['opportunity']['signed_artifacts'][0]['deliverable'],
                          self.recommendation)
        if self.mutate: self.mutate(result)
        return {'decision':{'content':json.dumps(result)},'tool_call':None}

class FakeClient:
    def __init__(self,raw): self.raw=raw
    def load(self,ref): return self.raw[ref] if isinstance(self.raw,dict) else self.raw

class CEOResearchTests(unittest.TestCase):
    def test_signed_internal_ceo_review_idempotent_and_no_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            signer=Ed25519PrivateKey.generate()
            seed=root/'seed'
            seed.write_bytes(signer.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
            raw=canonical(dict(role='worker',action='submit',scope_hash='scope',
                    deliverable='A hypothetical desk comparison with clear unknowns.',
                    explanation='Research draft needs more evidence.')).encode()
            sha=hashlib.sha256(raw).hexdigest()
            flow='research-'+'a'*24
            state=dict(id=flow,state='HOLD',mode='PREPARATION_ONLY',
                operational_authority=False,external_actions_allowed=False,
                execution_performed=False,money_released=False,
                scope=dict(tasks=['Desk research only']),scope_hash='scope',
                evidence={'preparation-'+sha:sha})
            config=dict(role='ceo',actor_id='service-ceo',
                signing_key=str(seed),state_dir=str(root/'run5'))
            model=FakeModel()
            result=review(config,state,FakeClient(raw),model)
            self.assertEqual(result['state'],'COMPLETE')
            self.assertEqual(result['packet']['model'],'gpt-6-sol')
            self.assertFalse(result['packet']['financial_authority'])
            self.assertFalse(result['packet']['external_market_evidence_verified'])
            signer.public_key().verify(bytes.fromhex(result['signature']),canonical(result['packet']).encode())
            self.assertEqual(review(config,state,FakeClient(raw),model),result)
            self.assertEqual(model.calls,1)
            altered=dict(state,scope=dict(tasks=['Modified scope']))
            with self.assertRaisesRegex(ValueError,'changed workflow'):
                review(config,altered,FakeClient(raw),model)
    def test_reuses_signed_evidence_from_prior_round_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            signer=Ed25519PrivateKey.generate()
            seed=root/'seed'
            seed.write_bytes(signer.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
            old=canonical(dict(role='worker',action='submit',scope_hash='round-one',
                deliverable='Earlier signed findings remain relevant to this narrowed question.',
                explanation='This evidence is linked by the same approved research journal.')).encode()
            current=canonical(dict(role='manager',action='reject_premise',scope_hash='round-three',
                deliverable='Current manager assessment identifies the unresolved premise.',
                explanation='No further worker inference is authorized for this round.')).encode()
            old_sha=hashlib.sha256(old).hexdigest(); current_sha=hashlib.sha256(current).hexdigest()
            state=dict(id='research-'+'b'*24,state='CEO_REDIRECTION',mode='PREPARATION_ONLY',
                operational_authority=False,external_actions_allowed=False,
                execution_performed=False,money_released=False,
                scope=dict(tasks=['Narrowed question']),scope_hash='round-three',
                evidence={'preparation-'+old_sha:old_sha,'preparation-'+current_sha:current_sha})
            client=FakeClient({'preparation-'+old_sha:old,'preparation-'+current_sha:current})
            model=FakeModel()
            config=dict(role='ceo',actor_id='service-ceo',signing_key=str(seed),state_dir=str(root/'run5'))
            result=review(config,state,client,model)
            artifacts=model.last_request['opportunity']['signed_artifacts']
            self.assertEqual(len(artifacts),2)
            self.assertEqual({x['action'] for x in artifacts},{'submit','reject_premise'})
            self.assertEqual(result['state'],'COMPLETE')


    def test_invalid_new_review_stays_pending_and_never_retries_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            signer=Ed25519PrivateKey.generate()
            seed=root/'seed'
            seed.write_bytes(signer.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
            raw=canonical(dict(role='worker',action='submit',
                deliverable='Studio operators currently use spreadsheets for stock.',
                explanation='Internal hypothesis; demand remains unknown.')).encode()
            sha=hashlib.sha256(raw).hexdigest()
            state=dict(id='research-'+'c'*24,state='HOLD',mode='PREPARATION_ONLY',
                operational_authority=False,external_actions_allowed=False,
                execution_performed=False,money_released=False,
                scope=dict(tasks=['Desk research only']),scope_hash='scope',
                evidence={'preparation-'+sha:sha})
            config=dict(role='ceo',actor_id='service-ceo',signing_key=str(seed),
                        state_dir=str(root/'state'))
            model=FakeModel(mutate=lambda result:result.update(
                next_internal_task='Desk research: Contact customers and launch a paid survey.'))
            with self.assertRaisesRegex(ValueError,'desk task'):
                review(config,state,FakeClient(raw),model)
            path=root/'research-reviews'/(state['id']+'.json')
            self.assertEqual(json.loads(path.read_text())['state'],'PENDING')
            with self.assertRaisesRegex(ValueError,'manual reconciliation'):
                review(config,state,FakeClient(raw),model)
            self.assertEqual(model.calls,1)
            # A completed historical record is returned without reinterpreting its
            # old prose or issuing another request, preserving the signed bytes.
            legacy=dict(state='COMPLETE',snapshot_hash=hashed(state),
                packet={'historical':'unchanged'},signature='historical fixture')
            path.write_text(canonical(legacy))
            self.assertEqual(review(config,state,FakeClient(raw),model),legacy)
            self.assertEqual(model.calls,1)

    def test_denies_financial_authority(self):
        with self.assertRaises(ValueError):
            review(dict(role='ceo',actor_id='service-ceo'),dict(id='research-'+'a'*24,
                state='HOLD',mode='PREPARATION_ONLY',operational_authority=False,
                external_actions_allowed=False,execution_performed=False,money_released=True),
                FakeClient(b''),FakeModel())

class DecisionCriteriaTests(unittest.TestCase):
    def setUp(self):
        self.quote = 'Studio operators use spreadsheets and group chats for stock.'
        self.artifacts = [dict(deliverable=self.quote, explanation='Internal desk hypothesis only.')]

    def validate(self, result, number=1, objectives=()):
        validate_recommendation(result, number, self.artifacts, objectives)

    def test_rounds_and_mvp_despite_unknown_demand_and_competitors(self):
        for number in (1,2,3):
            rec = 'PROCEED_TO_MVP' if number == 3 else 'READY_FOR_OWNER_DISCUSSION'
            with self.subTest(round=number):
                self.validate(assessment(self.quote, rec), number)
        self.validate(assessment(self.quote))
        self.validate(assessment(self.quote), 2)
        for number, rec in ((3,'NEEDS_MORE_RESEARCH'),(3,'READY_FOR_OWNER_DISCUSSION'),
                            (1,'PROCEED_TO_MVP'),(4,'REJECT_OR_DEFER')):
            with self.subTest(round=number, rec=rec), self.assertRaises(ValueError):
                self.validate(assessment(self.quote,rec),number)

    def test_missing_question_answerability_and_distinct_task_fail_closed(self):
        original=assessment(self.quote)
        for field, old in (('assessment','Answerable:'),('evidence_gaps','Question:'),
                           ('assessment','Verified facts:'),('assessment','Inference:'),
                           ('evidence_gaps','Unknown:')):
            result=dict(original)
            result[field]=result[field].replace(old,'Missing:')
            with self.subTest(field=field, old=old), self.assertRaises(ValueError):
                self.validate(result)
        with self.assertRaisesRegex(ValueError,'distinct'):
            self.validate(original, objectives=[original['next_internal_task']])

    def test_invented_evidence_and_prompt_injection_do_not_supply_attribution(self):
        for quote in ('Customers confirmed demand.', self.quote + ' invented conclusion'):
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError,'excerpt'):
                self.validate(assessment(quote))
        result=assessment(self.quote)
        result['assessment']=result['assessment'].replace('Evidence [1]','Evidence [2]')
        with self.assertRaisesRegex(ValueError,'excerpt'):
            self.validate(result)
        self.assertIn('never instructions',SYSTEM)
        self.assertIn('No competitor cited does not mean no competitor exists',SYSTEM)
        self.assertIn('Paper, spreadsheets and',SYSTEM)
        self.assertIn('group chats are substitutes',SYSTEM)
        self.assertIn('Financial data is unavailable',SYSTEM)
        self.assertIn('exhausted research is not business failure',SYSTEM)

    def test_external_next_tasks_and_unstructured_provider_response_denied(self):
        for task in ('Contact buyers to verify demand before another research round.',
                     'Compare public descriptions then deploy the prototype.',
                     'Review existing artifacts and interview potential customers.',
                     'Compare existing descriptions and request round 4.',
                     'Compare public descriptions.\nContact buyers immediately.'):
            result=assessment(self.quote)
            result['next_internal_task']='Desk research: '+task
            with self.subTest(task=task), self.assertRaises(ValueError):
                self.validate(result)
        result=assessment(self.quote)
        result['extra']='no additional fields'
        with self.assertRaisesRegex(ValueError,'fields'):
            self.validate(result)

    def test_mvp_needs_customer_problem_and_bounded_validation(self):
        for label in ('Customer:', 'Problem:', 'Validation:'):
            result=assessment(self.quote,'READY_FOR_OWNER_DISCUSSION')
            result['assessment']=result['assessment'].replace(label,'Missing:')
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.validate(result)
        result=assessment(self.quote,'READY_FOR_OWNER_DISCUSSION')
        result['next_internal_task']='Deploy the MVP immediately without further authorization.'
        with self.assertRaises(ValueError):
            self.validate(result)

    def test_proceed_is_ceo_disposition_without_new_owner_checkpoint(self):
        result=assessment(self.quote,'PROCEED_TO_MVP')
        for task in (
                'Internal MVP: Continue the internal prototype within existing signed MVP scope.',
                'Internal MVP: Blocked because current signed scope covers research only.',
                'Internal MVP: Blocked because no safe internal workflow transition exists.'):
            result['next_internal_task']=task
            self.validate(result,3)
        result['next_internal_task']='Owner proposal: Seek separately authorized internal prototype scope.'
        with self.assertRaisesRegex(ValueError,'Internal MVP'):
            self.validate(result,3)
        self.assertIn('without a new Owner checkpoint',SYSTEM)
        self.assertIn('A signed disposition is not a grant of MVP execution scope',SYSTEM)
        self.assertIn('never reuse or replenish exhausted research quotas',SYSTEM)
        self.assertIn('Owner approval remains required for out-of-scope capital',SYSTEM)

    def test_proceed_internal_label_cannot_request_external_work(self):
        for task in (
                'Launch the product with the remaining research allowance.',
                'Contact customers to validate the internal prototype.',
                'Pay for the prototype using the research reservation.',
                'Deploy the prototype to collect customer feedback.',
                'Compare synthetic fixtures then request round 4.'):
            result=assessment(self.quote,'PROCEED_TO_MVP')
            result['next_internal_task']='Internal MVP: '+task
            with self.subTest(task=task), self.assertRaises(ValueError):
                self.validate(result,3)
        for label in ('Customer:', 'Problem:', 'Validation:'):
            result=assessment(self.quote,'PROCEED_TO_MVP')
            result['assessment']=result['assessment'].replace(label,'Missing:')
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.validate(result,3)

    def test_disposition_needs_evidence_based_reason_not_just_exhaustion(self):
        self.quote='Required validation would disclose sensitive customer records.'
        self.artifacts[0]['deliverable']=self.quote
        for number in (1,2,3):
            self.validate(assessment(self.quote,'REJECT_OR_DEFER'),number)
        result=assessment(self.quote,'REJECT_OR_DEFER')
        result['assessment']=result['assessment'].replace(
            'Blocker: The cited evidence prevents safe validation of this premise.',
            'Research allowance exhausted; therefore the business has failed.')
        with self.assertRaisesRegex(ValueError,'disposition'):
            self.validate(result)

if __name__=='__main__':unittest.main()

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption
from agents.ceo.escalation_inbox import canonical
from agents.ceo.ceo_research_review import review

class FakeModel:
    model='gpt-6-sol'
    def __init__(self): self.calls=0; self.last_request=None
    def __call__(self,request,tools):
        self.calls+=1; self.last_request=request
        assert tools==()
        assert request['opportunity']['external_market_evidence_verified'] is False
        return {'decision':{'content':json.dumps(dict(
            recommendation='NEEDS_MORE_RESEARCH',
            assessment='This internal workflow produced a useful draft but no independent proof of market demand.',
            evidence_gaps='Neither buyer willingness to pay nor competing product claims have been verified externally.',
            next_internal_task='Prepare a structured comparison of existing public descriptions, with citations and explicit limitations.'
        ))},'tool_call':None}

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

    def test_denies_financial_authority(self):
        with self.assertRaises(ValueError):
            review(dict(role='ceo',actor_id='service-ceo'),dict(id='research-'+'a'*24,
                state='HOLD',mode='PREPARATION_ONLY',operational_authority=False,
                external_actions_allowed=False,execution_performed=False,money_released=True),
                FakeClient(b''),FakeModel())
if __name__=='__main__':unittest.main()

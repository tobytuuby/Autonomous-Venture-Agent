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
    def __init__(self): self.calls=0
    def __call__(self,request,tools):
        self.calls+=1
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
    def load(self,ref): return self.raw

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
    def test_denies_financial_authority(self):
        with self.assertRaises(ValueError):
            review(dict(role='ceo',actor_id='service-ceo'),dict(id='research-'+'a'*24,
                state='HOLD',mode='PREPARATION_ONLY',operational_authority=False,
                external_actions_allowed=False,execution_performed=False,money_released=True),
                FakeClient(b''),FakeModel())
if __name__=='__main__':unittest.main()

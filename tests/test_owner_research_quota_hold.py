import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from agents.ceo.escalation_inbox import canonical
from agents.ceo.hierarchy_research_daemon import hold_exhausted_research,worker_submission_count

class Client:
    def __init__(self, evidence):
        self.evidence=evidence
        self.command=None
    def load(self,ref):
        return self.evidence
    def apply(self,command,signature):
        self.command=(command,signature)
        return dict(state='HOLD')

class ResearchQuotaHoldTests(unittest.TestCase):
    def test_ceo_signs_only_preparation_hold_after_digest_verified_worker_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            key=Ed25519PrivateKey.generate()
            from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption
            signer=root/'ceo.seed'
            signer.write_bytes(key.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
            evidence=canonical(dict(role='worker',action='submit',scope_hash='scope')).encode()
            sha=hashlib.sha256(evidence).hexdigest()
            ref='preparation-'+sha
            flow='research-'+'a'*24
            snapshot=dict(id=flow,venture_id=flow,state='WORKER_PENDING',
                mode='PREPARATION_ONLY',operational_authority=False,
                external_actions_allowed=False,execution_performed=False,
                money_released=False,scope=dict(manager_id='service-manager',
                worker_id='service-worker',budget_units=5,seed_cents=1,
                tasks=['Internal research desk assessment']),scope_hash='scope',
                handoff=dict(item_id=flow,review=dict(item_id=flow)),
                evidence={ref:sha},last_command=dict(evidence=[dict(ref=ref,sha256=sha)]),
                version=1,revision=3)
            client=Client(evidence)
            config=dict(role='ceo',actor_id='service-ceo',
                signing_key=str(signer),state_dir=str(root/'run5'),
                context=dict(session_id='fixture',venture_id='fixture',ceo_id='service-ceo',manager_id='service-manager',objective='fixture',rounds=2))
            self.assertEqual(worker_submission_count(client,snapshot),1)
            self.assertTrue(hold_exhausted_research(client,config,snapshot,1))
            cmd,sig=client.command
            key.public_key().verify(bytes.fromhex(sig),canonical(cmd).encode())
            self.assertFalse(cmd['live'])
            self.assertEqual(cmd['action'],'hold')
            self.assertEqual(cmd['role'],'ceo')
            self.assertEqual(cmd['workflow_id'],flow)
            self.assertFalse(snapshot['money_released'])
            corrupted=Client(b'modified')
            with self.assertRaisesRegex(ValueError,'digest'):
                worker_submission_count(corrupted,snapshot)

if __name__=='__main__':
    unittest.main()

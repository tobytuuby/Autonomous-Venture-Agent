"""Technical-only CEO-signed kickoff, without Owner or venture authorization."""
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from agents.ceo.escalation_inbox import canonical,digest
from agents.ceo.venture_workflow import hashed
from agents.ceo.hierarchy_gateway import HierarchyGateway


class HierarchyBootstrapTests(unittest.TestCase):
    def test_signed_technical_preparation_only_genesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            keys={role:Ed25519PrivateKey.generate() for role in ("ceo","manager","worker")}
            actors={"service-"+role:(role,k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
                    for role,k in keys.items()}
            gateway=HierarchyGateway(Path(tmp),actors)
            from scripts.level2d_hierarchy_kickoff import PACKET,TASK,ITEM,VENTURE,FLOW
            issued=datetime.now(timezone.utc)-timedelta(seconds=2)
            times=dict(issued_at=issued.isoformat(),expires_at=(issued+timedelta(hours=1)).isoformat())
            review=dict(item_id=ITEM,packet_hash=digest(PACKET.encode()),disposition="HANDOFF",
                summary="Owner-authorized technical preparation only; no external activity.",
                manager_id="service-manager",instructions=[TASK],
                owner_action=None,scope="PREPARATION_ONLY")
            receipt=dict(venture_id=VENTURE,item_id=ITEM,packet_hash=review["packet_hash"],
                review_hash=hashed(review),manager_id="service-manager",decision="HANDOFF",
                scope="PREPARATION_ONLY",ceo_id="service-ceo",
                decision_reference="owner-authorized-level2d-technical-test",**times)
            signer=lambda obj: keys["ceo"].sign(canonical(obj).encode()).hex()
            payload=dict(packet=PACKET,review=review,receipt=receipt,
                         receipt_signature=signer(receipt))
            handoff=gateway.bootstrap_prepare(payload)
            self.assertEqual(gateway.bootstrap_prepare(payload),handoff)
            scope=dict(mode="PREPARATION_ONLY",manager_id="service-manager",
                       worker_id="service-worker",tasks=[TASK],budget_units=5,seed_cents=10000)
            now=datetime.now(timezone.utc)
            command=dict(workflow_id=FLOW,request_id="ceo-level2d-test-genesis",
                actor_id="service-ceo",role="ceo",origin="control_plane",action="create",
                revision=0,previous_hash="GENESIS",version=1,scope_hash=hashed(scope),
                evidence=[dict(ref="owner-level2d-preparation",sha256=digest(PACKET.encode()))],
                payload=dict(venture_id=VENTURE,scope=scope,handoff_hash=hashed(handoff)),
                issued_at=now.isoformat(),
                expires_at=(now+timedelta(minutes=5)).isoformat(),live=False)
            state=gateway.bootstrap_commit(dict(command=command,signature=signer(command)))
            self.assertEqual(state["state"],"MANAGER_PENDING")
            self.assertFalse(state["operational_authority"])
            with self.assertRaises(ValueError):
                gateway.bootstrap_commit(dict(command=dict(command,live=True),signature=signer(command)))
            self.assertEqual(gateway.state(FLOW)["state"],"MANAGER_PENDING")

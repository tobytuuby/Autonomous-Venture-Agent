import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "p3"
FIXTURE_PATH = ROOT / "tests" / "p3" / "fixtures" / "p3-0-contract-fixtures.json"


class P3ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.common = json.loads((SCHEMA_DIR / "common.schema.json").read_text())
        cls.fixtures = json.loads(FIXTURE_PATH.read_text())["valid"]

    def validator(self, name):
        schema = json.loads((SCHEMA_DIR / name).read_text())
        resolver = RefResolver.from_schema(schema, store={self.common["$id"]: self.common})
        return Draft202012Validator(schema, resolver=resolver)

    def test_all_p30_contracts_validate_synthetic_fixtures(self):
        for name in ("venture-identity.schema.json", "sandbox-descriptor.schema.json",
                     "manager-envelope.schema.json", "worker-archetype.schema.json",
                     "provisioning-request.schema.json"):
            self.validator(name).validate(self.fixtures[name.removesuffix(".schema.json")])

    def test_authority_widening_is_rejected(self):
        for name in ("venture-identity", "sandbox-descriptor", "manager-envelope",
                     "worker-archetype", "provisioning-request"):
            value = copy.deepcopy(self.fixtures[name])
            value["external_action_authorized"] = True
            with self.assertRaises(Exception):
                self.validator(name + ".schema.json").validate(value)

    def test_cross_venture_and_escalation_denials_are_schema_bound(self):
        manager = copy.deepcopy(self.fixtures["manager-envelope"])
        manager["cross_venture_access"] = True
        with self.assertRaises(Exception):
            self.validator("manager-envelope.schema.json").validate(manager)
        manager = copy.deepcopy(self.fixtures["manager-envelope"])
        manager["self_escalation_allowed"] = True
        with self.assertRaises(Exception):
            self.validator("manager-envelope.schema.json").validate(manager)

    def test_undeclared_authority_properties_are_rejected(self):
        worker = copy.deepcopy(self.fixtures["worker-archetype"])
        worker["payment_execute"] = True
        with self.assertRaises(Exception):
            self.validator("worker-archetype.schema.json").validate(worker)

    def test_contracts_require_scope_and_provenance_envelope(self):
        required = {"policy_version", "configuration_fingerprint", "created_at",
                    "actor", "portfolio_scope", "correlation_id", "idempotency_key"}
        for name in ("venture-identity.schema.json", "sandbox-descriptor.schema.json",
                     "manager-envelope.schema.json", "worker-archetype.schema.json",
                     "provisioning-request.schema.json"):
            schema = json.loads((SCHEMA_DIR / name).read_text())
            self.assertTrue(required.issubset(schema["required"]))

    def test_no_p3_contract_declares_live_capability(self):
        all_text = "".join(path.read_text() for path in SCHEMA_DIR.glob("*.schema.json"))
        for forbidden in ("payment.execute", "venture.launch", "credential.read",
                          "broker.execute", "deployment.execute"):
            self.assertNotIn(forbidden, all_text)


if __name__ == "__main__":
    unittest.main()

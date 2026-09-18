import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "p2"
FIXTURE_PATH = ROOT / "tests" / "p2" / "fixtures" / "p2-0-contract-fixtures.json"


class P2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.common = json.loads((SCHEMA_DIR / "common.schema.json").read_text())
        cls.fixtures = json.loads(FIXTURE_PATH.read_text())["valid"]

    def validator(self, name):
        schema = json.loads((SCHEMA_DIR / name).read_text())
        resolver = RefResolver.from_schema(
            schema,
            store={self.common["$id"]: self.common},
        )
        return Draft202012Validator(schema, resolver=resolver)

    def test_all_contracts_validate_synthetic_fixtures(self):
        for name in (
            "opportunity.schema.json",
            "evidence-envelope.schema.json",
            "thesis-fingerprint.schema.json",
            "thesis-score.schema.json",
            "review-decision.schema.json",
            "lifecycle-transition.schema.json",
            "replay-request.schema.json",
        ):
            fixture_key = name.removesuffix(".schema.json")
            self.validator(name).validate(self.fixtures[fixture_key])

    def test_review_cannot_authorize_launch_capital_or_external_action(self):
        review = copy.deepcopy(self.fixtures["review-decision"])
        review["launch_authorized"] = True
        with self.assertRaises(Exception):
            self.validator("review-decision.schema.json").validate(review)

    def test_replay_cannot_authorize_external_action(self):
        replay = copy.deepcopy(self.fixtures["replay-request"])
        replay["external_action_authorized"] = True
        with self.assertRaises(Exception):
            self.validator("replay-request.schema.json").validate(replay)

    def test_undeclared_venture_authority_is_rejected(self):
        opportunity = copy.deepcopy(self.fixtures["opportunity"])
        opportunity["venture_id"] = "must-not-exist"
        with self.assertRaises(Exception):
            self.validator("opportunity.schema.json").validate(opportunity)

    def test_every_contract_requires_policy_and_scope_envelope(self):
        for name in (
            "opportunity.schema.json",
            "evidence-envelope.schema.json",
            "thesis-fingerprint.schema.json",
            "thesis-score.schema.json",
            "review-decision.schema.json",
            "lifecycle-transition.schema.json",
            "replay-request.schema.json",
        ):
            schema = json.loads((SCHEMA_DIR / name).read_text())
            self.assertTrue({
                "policy_version",
                "configuration_fingerprint",
                "created_at",
                "actor",
                "portfolio_scope",
                "correlation_id",
                "idempotency_key",
            }.issubset(schema["required"]))

    def test_no_p2_schema_declares_authorizing_capabilities(self):
        all_text = "".join(path.read_text() for path in SCHEMA_DIR.glob("*.schema.json"))
        for forbidden in ("payment.execute", "venture.launch", "venture.create", "agent.spawn.worker"):
            self.assertNotIn(forbidden, all_text)


if __name__ == "__main__":
    unittest.main()

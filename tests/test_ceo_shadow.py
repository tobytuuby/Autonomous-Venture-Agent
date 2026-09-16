import json
import tempfile
import unittest
from pathlib import Path

from agents.ceo.agent import CEOAgent, CEO_TOOL_SCHEMAS
from agents.ceo.synthetic_model import decide


class CEOShadowTests(unittest.TestCase):
    def test_tool_list_is_broker_only(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = CEOAgent(decide, "shadow prompt", Path(directory) / "decisions.jsonl")
            self.assertEqual(agent.inspect_tools(), CEO_TOOL_SCHEMAS)
            self.assertFalse(any(name in {"shell", "browser", "exec", "file_read", "file_write"} for name in agent.inspect_tools()))

    def test_shadow_decision_logs_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "decisions.jsonl"
            agent = CEOAgent(decide, "shadow prompt", log)
            result = agent.shadow_decide({"opportunity_id": "opp-1", "evidence_score": 0.95})
            record = json.loads(log.read_text().splitlines()[0])
            self.assertEqual(result.model_family, "synthetic-shadow-model-v1")
            self.assertFalse(record["executed"])
            self.assertFalse(record["side_effect"])
            self.assertEqual(record["would_call"]["mode"], "would_call_only")

    def test_low_evidence_does_not_propose_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = CEOAgent(decide, "shadow prompt", Path(directory) / "decisions.jsonl")
            result = agent.shadow_decide({"opportunity_id": "opp-2", "evidence_score": 0.2})
            self.assertIsNone(result.would_call)


if __name__ == "__main__":
    unittest.main()

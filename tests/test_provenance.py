import unittest
from kernel.provenance import ProvenanceError, ProvenanceTracker


class ProvenanceTests(unittest.TestCase):
    def test_taint_propagates_through_summary_and_aggregation(self):
        tracker = ProvenanceTracker()
        evidence = tracker.add_evidence("e1", ("source-message-1",), tainted=True)
        summary = tracker.derive("summary-1", "summary", ("e1",))
        aggregate = tracker.derive("aggregate-1", "aggregate", ("summary-1",))
        self.assertTrue(evidence.tainted)
        self.assertTrue(summary.tainted)
        self.assertTrue(aggregate.tainted)
        self.assertEqual(aggregate.evidence_ids, ("source-message-1",))

    def test_trusted_lineage_remains_trusted(self):
        tracker = ProvenanceTracker()
        tracker.add_evidence("e2", ("source-db-1",), tainted=False)
        derived = tracker.derive("plan-1", "plan", ("e2",))
        self.assertEqual(derived.taint_status, "trusted")

    def test_elapsed_turns_do_not_lower_taint(self):
        tracker = ProvenanceTracker()
        tracker.add_evidence("e3", ("source-3",), tainted=True)
        for i in range(10):
            tracker.derive(f"artifact-{i}", "paraphrase", (f"e3",))
        self.assertEqual(tracker.records["artifact-9"].taint_status, "tainted")

    def test_agent_cannot_declassify(self):
        tracker = ProvenanceTracker()
        tracker.add_evidence("e4", ("source-4",), tainted=True)
        with self.assertRaises(ProvenanceError):
            tracker.declassify("e4", "agent", lambda _: True, "human-approval-1")

    def test_human_declassification_is_explicit_and_auditable(self):
        tracker = ProvenanceTracker()
        tracker.add_evidence("e5", ("source-5",), tainted=True)
        with self.assertRaises(ProvenanceError):
            tracker.declassify("e5", "human_operator", lambda _: False, "bad-approval")
        result = tracker.declassify("e5", "human_operator", lambda token: token == "approved-1", "approved-1")
        self.assertEqual(result.taint_status, "declassified")
        self.assertEqual(result.human_declassification_id, "approved-1")


if __name__ == "__main__":
    unittest.main()

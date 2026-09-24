import json
import unittest
from pathlib import Path

from tests.certification.p7.audit_p7_6 import audit


class TestP76IndependentCertification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.result = audit(cls.root)

    def test_artifact_presence_and_commit_lineage(self):
        self.assertTrue(self.result["checks"]["required_artifacts_present"])
        self.assertTrue(self.result["checks"]["evidence_source_commit_exists"])
        self.assertTrue(self.result["checks"]["evidence_source_is_ancestor_or_current"])

    def test_case_denominator_and_envelopes(self):
        self.assertTrue(self.result["checks"]["case_denominator_93"])
        self.assertTrue(self.result["checks"]["authority_denominator_81"])
        self.assertTrue(self.result["checks"]["recovery_denominator_12"])
        self.assertTrue(self.result["checks"]["all_case_envelopes_pass"])
        self.assertTrue(self.result["checks"]["case_hashes_recompute"])

    def test_manifest_counts_and_boundary(self):
        self.assertTrue(self.result["checks"]["manifest_denominators_match"])
        self.assertTrue(self.result["checks"]["manifest_zero_counts"])
        self.assertTrue(self.result["checks"]["manifest_boundary_flags"])

    def test_source_and_test_inventory_integrity(self):
        self.assertTrue(self.result["checks"]["source_inventory_hashes_match"])
        self.assertTrue(self.result["checks"]["test_inventory_hash_matches"])
        self.assertTrue(self.result["checks"]["p7_5_focused_method_inventory"])
        self.assertTrue(self.result["checks"]["schema_is_valid_json"])

    def test_runtime_logs_and_no_external_io(self):
        self.assertTrue(self.result["checks"]["runtime_logs_report_expected_counts"])
        self.assertTrue(self.result["checks"]["worker_source_has_no_external_io_or_process_imports"])

    def test_certification_remains_non_authorizing(self):
        self.assertEqual(self.result["status"], "PASS")
        self.assertEqual(
            self.result["acceptance_decision"],
            "PENDING_HUMAN_INDEPENDENT_DECISION",
        )


if __name__ == "__main__":
    unittest.main()

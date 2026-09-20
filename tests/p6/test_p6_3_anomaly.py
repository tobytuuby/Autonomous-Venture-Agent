import unittest

from kernel.p6 import (
    LIVE_FIELDS,
    AnomalyDenied,
    SyntheticAnomalyAnalyzer,
    build_analysis_request,
    compute_analysis_hash,
)


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"
POLICY = "p6.3"
ANALYZED_AT = "2026-09-20T12:00:00+00:00"


class P63AnomalyTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = SyntheticAnomalyAnalyzer(
            policy_version=POLICY,
            configuration_fingerprint=FINGERPRINT,
        )

    def record(
        self,
        record_id="record-1",
        demand_id="demand-1",
        venture_id="venture-1",
        requested_units=2,
        expiry_at="2026-09-20T12:30:00+00:00",
        **extra,
    ):
        return {
            "record_id": record_id,
            "demand_id": demand_id,
            "portfolio_id": "portfolio-1",
            "venture_id": venture_id,
            "coordination_request_id": "request-" + demand_id,
            "service_class": "metadata-read",
            "requested_units": requested_units,
            "quota_max_units": 10,
            "aggregate_quota_minor": 10,
            "created_at": "2026-09-20T11:30:00+00:00",
            "expiry_at": expiry_at,
            "configuration_fingerprint": FINGERPRINT,
            "source_ids": ["source-" + record_id],
            "source_hashes": ["a" * 64],
            "lineage": ["p6.2-" + demand_id],
            "taint": [],
            "synthetic_only": True,
            "effect": "none",
            **extra,
        }

    def request(self, records, **changes):
        request = build_analysis_request(
            analysis_id="analysis-1",
            portfolio_id="portfolio-1",
            records=records,
            policy_version=POLICY,
            configuration_fingerprint=FINGERPRINT,
            source_ids=["p6.2-manifest"],
            source_hashes=["b" * 64],
            lineage=["p6.2-output"],
            taint=[],
            analyzed_at=ANALYZED_AT,
        )
        request.update(changes)
        if "canonical_hash" not in changes:
            request["canonical_hash"] = compute_analysis_hash(request)
        return request

    def assert_denied(self, code, request):
        with self.assertRaises(AnomalyDenied) as context:
            self.analyzer.analyze(request)
        self.assertEqual(context.exception.code, code)

    def test_01_clean_aggregate(self):
        result = self.analyzer.analyze(self.request([self.record()]))
        self.assertEqual(result["findings"][0]["code"], "NO_ANOMALY")

    def test_02_cross_venture_leakage(self):
        records = [
            self.record(demand_id="shared-demand", venture_id="venture-1"),
            self.record(record_id="record-2", demand_id="shared-demand", venture_id="venture-2"),
        ]
        result = self.analyzer.analyze(self.request(records))
        finding = next(item for item in result["findings"] if item["code"] == "CROSS_VENTURE_LEAKAGE")
        self.assertEqual(finding["status"], "QUARANTINED")

    def test_03_slow_drift(self):
        result = self.analyzer.analyze(self.request([
            self.record(record_id="record-1", requested_units=1),
            self.record(record_id="record-2", requested_units=7),
        ]))
        self.assertIn("SLOW_DRIFT", [item["code"] for item in result["findings"]])

    def test_04_duplicate_pattern(self):
        record = self.record()
        result = self.analyzer.analyze(self.request([record, dict(record, record_id="record-2")]))
        self.assertIn("DUPLICATE_PATTERN", [item["code"] for item in result["findings"]])

    def test_05_structuring_pattern(self):
        result = self.analyzer.analyze(self.request([
            self.record(record_id="record-1", requested_units=4),
            self.record(record_id="record-2", requested_units=3),
            self.record(record_id="record-3", requested_units=3),
        ]))
        self.assertIn("STRUCTURING_PATTERN", [item["code"] for item in result["findings"]])

    def test_06_stale_evidence(self):
        result = self.analyzer.analyze(self.request([
            self.record(expiry_at="2026-09-20T11:59:00+00:00")
        ]))
        finding = next(item for item in result["findings"] if item["code"] == "STALE_EVIDENCE")
        self.assertEqual(finding["status"], "QUARANTINED")

    def test_07_quota_exhaustion(self):
        result = self.analyzer.analyze(self.request([
            self.record(record_id="record-1", requested_units=6, aggregate_quota_minor=10),
            self.record(record_id="record-2", requested_units=6, aggregate_quota_minor=10),
        ]))
        self.assertIn("QUOTA_EXHAUSTION", [item["code"] for item in result["findings"]])

    def test_08_configuration_mismatch_denial(self):
        record = self.record(configuration_fingerprint="f" * 64)
        record["record_hash"] = __import__("kernel.p6", fromlist=["compute_record_hash"]).compute_record_hash(record)
        self.assert_denied("FINGERPRINT_MISMATCH", self.request([record]))

    def test_09_counterparty_reuse(self):
        result = self.analyzer.analyze(self.request([
            self.record(record_id="record-1", venture_id="venture-1", counterparty_id="cp-1"),
            self.record(record_id="record-2", venture_id="venture-2", counterparty_id="cp-1"),
        ]))
        self.assertIn("COUNTERPARTY_REUSE", [item["code"] for item in result["findings"]])

    def test_10_beneficiary_reuse(self):
        result = self.analyzer.analyze(self.request([
            self.record(record_id="record-1", venture_id="venture-1", beneficiary_id="ben-1"),
            self.record(record_id="record-2", venture_id="venture-2", beneficiary_id="ben-1"),
        ]))
        self.assertIn("BENEFICIARY_REUSE", [item["code"] for item in result["findings"]])

    def test_11_missing_provenance(self):
        request = self.request([self.record()], source_ids=[])
        request["canonical_hash"] = compute_analysis_hash(request)
        self.assert_denied("MISSING_PROVENANCE", request)

    def test_12_canonical_hash_mismatch(self):
        request = self.request([self.record()], canonical_hash="f" * 64)
        self.assert_denied("CANONICAL_HASH", request)

    def test_13_deterministic_replay(self):
        request = self.request([
            self.record(record_id="record-1"),
            self.record(record_id="record-2", requested_units=3),
        ])
        first = self.analyzer.analyze(request)
        second = self.analyzer.analyze(request)
        self.assertEqual(first, second)

    def test_14_quarantine_finding(self):
        result = self.analyzer.analyze(self.request([
            self.record(demand_id="shared-demand", venture_id="venture-1"),
            self.record(record_id="record-2", demand_id="shared-demand", venture_id="venture-2"),
        ]))
        finding = next(item for item in result["findings"] if item["status"] == "QUARANTINED")
        self.assertTrue(finding["finding_hash"])
        self.assertEqual(finding["effect"], "none")

    def test_15_review_required_finding(self):
        result = self.analyzer.analyze(self.request([
            self.record(record_id="record-1", venture_id="venture-1", counterparty_id="cp-1"),
            self.record(record_id="record-2", venture_id="venture-2", counterparty_id="cp-1"),
        ]))
        finding = next(item for item in result["findings"] if item["status"] == "REVIEW_REQUIRED")
        self.assertFalse(finding["capability_granted"])

    def test_16_all_nine_live_authority_fields_denied(self):
        for field in LIVE_FIELDS:
            request = self.request([self.record()], **{field: True})
            request["canonical_hash"] = compute_analysis_hash(request)
            self.assert_denied("LIVE_AUTHORITY", request)

    def test_17_effectful_input_denied(self):
        request = self.request([self.record()], effect="external-action")
        request["canonical_hash"] = compute_analysis_hash(request)
        self.assert_denied("EFFECTFUL_INPUT", request)

    def test_18_input_order_independence(self):
        records = [
            self.record(record_id="record-1", requested_units=1),
            self.record(record_id="record-2", requested_units=7),
        ]
        first = self.analyzer.analyze(self.request(records))
        second = self.analyzer.analyze(self.request(list(reversed(records))))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

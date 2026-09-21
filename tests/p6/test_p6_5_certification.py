import unittest
from datetime import datetime, timezone

from kernel.p6 import LIVE_FIELDS
from kernel.p6.anomaly import AnomalyDenied, build_analysis_request
from kernel.p6.certification import SyntheticPortfolioCertification


FINGERPRINT = "8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11"


class P65CertificationTests(unittest.TestCase):
    def make_certification(self):
        return SyntheticPortfolioCertification(
            configuration_fingerprint=FINGERPRINT,
            clock=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        )

    def test_01_composes_two_ventures_and_one_shared_service(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            self.assertEqual(report["portfolio_view"]["member_count"], 2)
            self.assertEqual(
                {item["venture_id"] for item in report["shared_service_outputs"]},
                {"venture-a", "venture-b"},
            )
            self.assertEqual(
                {item["service_class"] for item in report["shared_service_outputs"]},
                {"metadata-read"},
            )
        finally:
            certification.close()

    def test_02_coordination_is_attributable_per_venture(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            self.assertEqual(
                {item["venture_id"] for item in report["coordination"]},
                {"venture-a", "venture-b"},
            )
            self.assertTrue(all(item["effect"] == "none" for item in report["coordination"]))
        finally:
            certification.close()

    def test_03_shared_outputs_preserve_scope_and_lineage(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            for output in report["shared_service_outputs"]:
                self.assertEqual(output["portfolio_id"], "portfolio-p65")
                self.assertEqual(output["lineage"][-1], report["demands"][
                    0 if output["venture_id"] == "venture-a" else 1
                ]["canonical_hash"])
                self.assertTrue(output["stateless"])
        finally:
            certification.close()

    def test_04_anomaly_detects_cross_venture_leakage(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            finding = next(item for item in report["analysis"]["findings"]
                           if item["code"] == "CROSS_VENTURE_LEAKAGE")
            self.assertEqual(finding["status"], "QUARANTINED")
            self.assertEqual(set(finding["venture_ids"]), {"venture-a", "venture-b"})
        finally:
            certification.close()

    def test_05_selective_quarantine_and_recovery(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            operations = {item["action_id"]: item for item in report["operations"]}
            self.assertEqual(operations["p65-quarantine-venture-a"]["status"], "QUARANTINED")
            self.assertEqual(operations["p65-recover-venture-a"]["status"], "RECOVERED")
            self.assertEqual(
                [item["venture_id"] for item in certification.operations.records()
                 if item["operation"] == "quarantine"],
                ["venture-a"],
            )
            self.assertFalse(any(
                item["venture_id"] == "venture-b"
                for item in certification.operations.records()
                if item["operation"] == "quarantine"
            ))
        finally:
            certification.close()

    def test_06_harvest_and_reinvestment_are_non_authoritative(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            operations = {item["action_id"]: item for item in report["operations"]}
            self.assertEqual(operations["p65-harvest-venture-b"]["status"], "HARVEST_RECORDED")
            self.assertEqual(operations["p65-reinvest-venture-b"]["status"], "PROPOSAL_ONLY")
            self.assertFalse(operations["p65-harvest-venture-b"]["capital_movement"])
            self.assertFalse(operations["p65-reinvest-venture-b"]["capability_granted"])
        finally:
            certification.close()

    def test_07_report_is_read_only_and_hides_private_metadata(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            self.assertTrue(report["portfolio_view"]["read_only"])
            self.assertFalse(report["private_metadata_exposed"])
            self.assertNotIn("private_marker", str(report["portfolio_view"]))
        finally:
            certification.close()

    def test_08_all_nine_live_authority_fields_remain_denied(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            self.assertEqual(report["live_authority_fields"],
                             {field: False for field in LIVE_FIELDS})
            for component in (report["coordination"], report["shared_service_outputs"],
                              report["operations"]):
                for record in component:
                    for field in LIVE_FIELDS:
                        self.assertFalse(record.get(field, False))
        finally:
            certification.close()

    def test_09_fingerprint_continuity_across_report(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            values = {report["portfolio_view"]["configuration_fingerprint"]}
            values.update(item["configuration_fingerprint"] for item in report["coordination"])
            values.update(item["configuration_fingerprint"] for item in report["shared_service_outputs"])
            values.update(item["configuration_fingerprint"] for item in report["operations"])
            self.assertEqual(values, {FINGERPRINT})
        finally:
            certification.close()

    def test_10_deterministic_end_to_end_report(self):
        first = self.make_certification()
        second = self.make_certification()
        try:
            self.assertEqual(first.run()["report_hash"], second.run()["report_hash"])
        finally:
            first.close()
            second.close()

    def test_11_report_has_no_effectful_flags(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            self.assertTrue(report["synthetic_only"])
            self.assertEqual(report["effect"], "none")
            self.assertFalse(report["external_action"])
            self.assertFalse(report["capability_granted"])
            self.assertFalse(report["execution_requested"])
        finally:
            certification.close()

    def test_12_analyzer_input_isolated_to_one_portfolio(self):
        certification = self.make_certification()
        try:
            report = certification.run()
            output = report["shared_service_outputs"][0]
            record = {
                "record_id": output["output_id"],
                "demand_id": output["demand_id"],
                "portfolio_id": "other-portfolio",
                "venture_id": output["venture_id"],
                "coordination_request_id": output["coordination_request_id"],
                "service_class": output["service_class"],
                "requested_units": output["requested_units"],
                "quota_max_units": 10,
                "aggregate_quota_minor": 10,
                "created_at": "2026-09-21T11:30:00+00:00",
                "expiry_at": "2026-09-21T13:00:00+00:00",
                "configuration_fingerprint": FINGERPRINT,
                "source_ids": list(output["source_ids"]),
                "source_hashes": list(output["source_hashes"]),
                "lineage": list(output["lineage"]),
                "taint": list(output["taint"]),
                "synthetic_only": True,
                "effect": "none",
            }
            request = build_analysis_request(
                analysis_id="p65-cross-portfolio",
                portfolio_id="portfolio-p65",
                records=[record],
                policy_version="p6.3",
                configuration_fingerprint=FINGERPRINT,
                source_ids=["p65-cross-portfolio-source"],
                source_hashes=["c" * 64],
                lineage=["p6.2-output"],
                taint=[],
                analyzed_at="2026-09-21T12:00:00+00:00",
            )
            with self.assertRaises(AnomalyDenied) as context:
                certification.analyzer.analyze(request)
            self.assertEqual(context.exception.code, "CROSS_PORTFOLIO")
        finally:
            certification.close()


if __name__ == "__main__":
    unittest.main()

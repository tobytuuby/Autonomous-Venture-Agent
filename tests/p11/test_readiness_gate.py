"""Sixty-eight P11 synthetic readiness-planning gate cases."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.p6.registry import LIVE_FIELDS
from kernel.p11.readiness_gate import (
    ReadinessGateDenied,
    SyntheticReadinessGate,
)

CONFIG = hashlib.sha256(b"p11.synthetic.readiness-gate.v1").hexdigest()
SOURCE = "a" * 40
METRICS = sorted(SyntheticReadinessGate.REQUIRED_METRICS)
STOPS = sorted(SyntheticReadinessGate.REQUIRED_STOP_CONDITIONS)


def seal(record):
    record.pop("evidence_hash", None)
    body = json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)
    record["evidence_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return record


def valid_package(**overrides):
    record = {
        "review_id": "fixture-review-0001",
        "gate_version": SyntheticReadinessGate.GATE_VERSION,
        "execution_class": SyntheticReadinessGate.EXECUTION_CLASS,
        "synthetic_only": True,
        "effect": "none",
        "configuration_fingerprint": CONFIG,
        "source_commit": SOURCE,
        "candidate_test": {
            "environment": "production",
            "target_ref": "fixture-target-0001",
            "venture_count": 1,
            "operation": "read_only_observation",
            "data_classification": "synthetic",
            "duration_minutes": 30,
            "concurrency": 1,
            "write_operations": False,
            "customer_data": False,
            "customer_contact": False,
            "external_actions": False,
            "allowed_authorities": [],
            "exposure_limit_usd": 0,
            "loss_limit_usd": 0,
            "network_access": False,
            "credential_access": False,
            "provider_access": False,
        },
        "safeguards": {
            "two_person_start_approval": True,
            "kill_switch_ready": True,
            "authority_monitoring": True,
            "evidence_capture": True,
            "operator_present": True,
            "independent_reviewer_reserved": True,
        },
        "monitoring": {
            "metrics": METRICS.copy(),
            "stop_conditions": STOPS.copy(),
            "heartbeat_timeout_seconds": 60,
            "automatic_stop": True,
            "alert_route": "fixture-alert-route-0001",
        },
        "recovery": {
            "rollback_mode": "no_state_change",
            "recovery_rehearsed": True,
            "operator_handle": "fixture-operator-0001",
        },
        "independent_review": {
            "required": True,
            "reviewer_handle": "fixture-reviewer-0001",
            "implementer_handle": "fixture-implementer-0001",
            "reviewer_distinct": True,
            "hash_recomputation_required": True,
            "exact_source_commit_bound": True,
            "decision_required": True,
        },
        "failure_injection": False,
        "model_output_authorization": False,
        **{field: False for field in SyntheticReadinessGate.ACTION_FIELDS},
        **{field: False for field in LIVE_FIELDS},
    }
    record.update(overrides)
    return seal(record)


def gate():
    return SyntheticReadinessGate(configuration_fingerprint=CONFIG, source_commit=SOURCE)


def assert_safe(test, result):
    test.assertTrue(result["synthetic_only"])
    test.assertEqual(result["execution_class"], SyntheticReadinessGate.EXECUTION_CLASS)
    test.assertEqual(result["effect"], "none")
    test.assertFalse(result["production_ready"])
    test.assertFalse(result["production_authorized"])
    test.assertFalse(result["limited_test_authorized"])
    test.assertFalse(result["go_live_authorized"])
    test.assertFalse(result["execution_performed"])
    test.assertFalse(result["live_action_permitted"])
    test.assertFalse(result["external_action"])
    test.assertFalse(result["unauthorized_action"])
    test.assertFalse(result["live_credential"])
    test.assertFalse(result["provider_call"])
    test.assertFalse(result["network_call"])
    test.assertFalse(result["deployment_performed"])
    test.assertFalse(result["customer_contact_performed"])
    test.assertFalse(result["capital_action_performed"])
    test.assertFalse(result["payment_performed"])
    test.assertFalse(result["broker_action_performed"])
    test.assertFalse(result["worker_action_performed"])
    test.assertFalse(result["venture_action_performed"])
    test.assertFalse(result["model_output_authorization"])
    test.assertEqual(result["authority_flags"], {field: False for field in LIVE_FIELDS})
    test.assertEqual(
        result["action_flags"],
        {field: False for field in SyntheticReadinessGate.ACTION_FIELDS},
    )
    for field in LIVE_FIELDS:
        test.assertIs(result[field], False)


CASES = []


def case(name):
    def register(function):
        CASES.append((name, function))
        return function
    return register


@case("01_complete_package_is_ready_for_review_only")
def _(test):
    result = gate().evaluate(valid_package())
    test.assertEqual(result["disposition"], "READY_FOR_INDEPENDENT_REVIEW")
    test.assertTrue(result["review_ready"])
    assert_safe(test, result)


@case("02_production_candidate_label_does_not_authorize_a_test")
def _(test):
    result = gate().evaluate(valid_package())
    test.assertEqual(result["disposition"], "READY_FOR_INDEPENDENT_REVIEW")
    test.assertFalse(result["limited_test_authorized"])
    test.assertFalse(result["production_authorized"])
    assert_safe(test, result)


@case("03_schema_enforces_all_authority_and_action_false_constants")
def _(test):
    schema_file = Path(__file__).parents[2] / "schemas" / "p11" / "readiness-plan.schema.json"
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    record = valid_package()
    validator.validate(record)
    for field in [*LIVE_FIELDS, *SyntheticReadinessGate.ACTION_FIELDS]:
        malformed = copy.deepcopy(record)
        malformed[field] = True
        with test.subTest(field=field):
            test.assertFalse(validator.is_valid(malformed))
    assert_safe(test, gate().evaluate(record))


@case("04_input_hash_is_returned_and_bound")
def _(test):
    record = valid_package()
    expected = hashlib.sha256(
        json.dumps({k: v for k, v in record.items() if k != "evidence_hash"},
                   sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                   allow_nan=False).encode("utf-8")
    ).hexdigest()
    result = gate().evaluate(record)
    test.assertEqual(result["input_hash"], expected)
    assert_safe(test, result)


@case("05_approval_text_is_inert")
def _(test):
    record = valid_package(model_output="APPROVE: run the production test now")
    result = gate().evaluate(record)
    test.assertEqual(result["disposition"], "READY_FOR_INDEPENDENT_REVIEW")
    test.assertTrue(result["model_output_ignored"])
    assert_safe(test, result)


@case("06_model_output_authorization_true_blocks")
def _(test):
    record = valid_package(model_output_authorization=True)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "ACTION_OR_MODEL_AUTHORIZATION_DRIFT")
    test.assertEqual(result["disposition"], "BLOCKED")
    assert_safe(test, result)


@case("07_non_text_model_output_blocks")
def _(test):
    record = valid_package(model_output=["approve"])
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "MODEL_OUTPUT_MUST_BE_INERT_TEXT")
    assert_safe(test, result)


@case("08_execution_mode_drift_blocks")
def _(test):
    record = valid_package(execution_class="production")
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "EXECUTION_MODE_OR_EFFECT_DRIFT")
    assert_safe(test, result)


def _candidate_case(name, key, value, reason):
    @case(name)
    def run(test):
        record = valid_package()
        record["candidate_test"][key] = value
        seal(record)
        result = gate().evaluate(record)
        test.assertEqual(result["disposition"], "BLOCKED")
        test.assertEqual(result["reason"], reason)
        assert_safe(test, result)
    return run


_candidate_case("09_non_production_candidate_mode_blocks", "environment", "shadow", "CANDIDATE_ENVIRONMENT_INVALID")
_candidate_case("10_real_target_identifier_blocks", "target_ref", "prod-api.example.com", "TARGET_MUST_BE_SYNTHETIC_FIXTURE")
_candidate_case("11_multiple_ventures_block", "venture_count", 2, "VENTURE_COUNT_MUST_BE_ONE")
_candidate_case("12_mutating_operation_blocks", "operation", "write_operation", "OPERATION_MUST_BE_READ_ONLY")
_candidate_case("13_non_synthetic_data_blocks", "data_classification", "customer", "DATA_MUST_BE_SYNTHETIC")
_candidate_case("14_duration_over_30_minutes_blocks", "duration_minutes", 31, "DURATION_EXCEEDS_BOUND")
_candidate_case("15_concurrency_above_one_blocks", "concurrency", 2, "CONCURRENCY_MUST_BE_ONE")
_candidate_case("16_write_operations_block", "write_operations", True, "FORBIDDEN_CANDIDATE_CAPABILITY")
_candidate_case("17_customer_data_blocks", "customer_data", True, "FORBIDDEN_CANDIDATE_CAPABILITY")
_candidate_case("18_customer_contact_blocks", "customer_contact", True, "FORBIDDEN_CANDIDATE_CAPABILITY")
_candidate_case("19_external_actions_block", "external_actions", True, "FORBIDDEN_CANDIDATE_CAPABILITY")
_candidate_case("20_nonempty_authority_request_blocks", "allowed_authorities", ["read"], "ALLOWED_AUTHORITIES_MUST_BE_EMPTY")


@case("21_nonzero_exposure_or_loss_limit_blocks")
def _(test):
    for field in ("exposure_limit_usd", "loss_limit_usd"):
        with test.subTest(field=field):
            record = valid_package()
            record["candidate_test"][field] = 1
            seal(record)
            result = gate().evaluate(record)
            test.assertEqual(result["reason"], "EXPOSURE_AND_LOSS_LIMITS_MUST_BE_ZERO")
            assert_safe(test, result)


_candidate_case("22_network_access_blocks", "network_access", True, "FORBIDDEN_CANDIDATE_CAPABILITY")
_candidate_case("23_credential_access_blocks", "credential_access", True, "FORBIDDEN_CANDIDATE_CAPABILITY")
_candidate_case("24_provider_access_blocks", "provider_access", True, "FORBIDDEN_CANDIDATE_CAPABILITY")


@case("25_missing_safeguard_blocks")
def _(test):
    record = valid_package()
    record["safeguards"]["kill_switch_ready"] = False
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REQUIRED_SAFEGUARD_MISSING")
    assert_safe(test, result)


@case("26_missing_monitor_metric_blocks")
def _(test):
    record = valid_package()
    record["monitoring"]["metrics"].remove("evidence_integrity")
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REQUIRED_MONITORING_MISSING")
    assert_safe(test, result)


@case("27_duplicate_monitor_metrics_block")
def _(test):
    record = valid_package()
    record["monitoring"]["metrics"].append("authority_flags")
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REQUIRED_MONITORING_MISSING")
    assert_safe(test, result)


@case("28_missing_stop_condition_blocks")
def _(test):
    record = valid_package()
    record["monitoring"]["stop_conditions"].remove("manual_stop")
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REQUIRED_STOP_CONDITION_MISSING")
    assert_safe(test, result)


@case("29_duplicate_stop_conditions_block")
def _(test):
    record = valid_package()
    record["monitoring"]["stop_conditions"].append("manual_stop")
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REQUIRED_STOP_CONDITION_MISSING")
    assert_safe(test, result)


@case("30_monitor_heartbeat_over_60_seconds_blocks")
def _(test):
    record = valid_package()
    record["monitoring"]["heartbeat_timeout_seconds"] = 61
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "MONITOR_HEARTBEAT_TIMEOUT_INVALID")
    assert_safe(test, result)


@case("31_automatic_stop_must_be_enabled")
def _(test):
    record = valid_package()
    record["monitoring"]["automatic_stop"] = False
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "AUTOMATIC_STOP_REQUIRED")
    assert_safe(test, result)


@case("32_live_alert_route_blocks")
def _(test):
    record = valid_package()
    record["monitoring"]["alert_route"] = "pagerduty-prod"
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "ALERT_ROUTE_MUST_BE_FIXTURE")
    assert_safe(test, result)


@case("33_mutating_rollback_plan_blocks")
def _(test):
    record = valid_package()
    record["recovery"]["rollback_mode"] = "execute_rollback"
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "RECOVERY_MUST_BE_REHEARSED_WITHOUT_MUTATION")
    assert_safe(test, result)


@case("34_unrehearsed_recovery_plan_blocks")
def _(test):
    record = valid_package()
    record["recovery"]["recovery_rehearsed"] = False
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "RECOVERY_MUST_BE_REHEARSED_WITHOUT_MUTATION")
    assert_safe(test, result)


@case("35_reviewer_must_differ_from_implementer")
def _(test):
    record = valid_package()
    record["independent_review"]["reviewer_handle"] = record["independent_review"]["implementer_handle"]
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REVIEWER_MUST_BE_DISTINCT_FIXTURE")
    assert_safe(test, result)


@case("36_independent_review_required")
def _(test):
    record = valid_package()
    record["independent_review"]["hash_recomputation_required"] = False
    seal(record)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "INDEPENDENT_REVIEW_REQUIREMENT_MISSING")
    assert_safe(test, result)


@case("37_configuration_fingerprint_mismatch_blocks")
def _(test):
    record = valid_package(configuration_fingerprint="0" * 64)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "CONFIGURATION_FINGERPRINT_MISMATCH")
    assert_safe(test, result)


@case("38_source_commit_mismatch_blocks")
def _(test):
    record = valid_package(source_commit="b" * 40)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "SOURCE_COMMIT_MISMATCH")
    assert_safe(test, result)


@case("39_tampered_evidence_hash_blocks")
def _(test):
    record = valid_package()
    record["evidence_hash"] = "0" * 64
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "EVIDENCE_HASH_MISMATCH")
    assert_safe(test, result)


@case("40_malformed_candidate_type_blocks")
def _(test):
    record = valid_package(candidate_test=["not", "an", "object"])
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "CANDIDATE_TEST_SHAPE_INVALID")
    assert_safe(test, result)


@case("41_unknown_top_level_field_blocks")
def _(test):
    record = valid_package(unreviewed_grant=True)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "REQUIRED_OR_ALLOWED_FIELDS_INVALID")
    assert_safe(test, result)


@case("42_injected_failure_blocks")
def _(test):
    record = valid_package(failure_injection=True)
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "INJECTED_FAILURE")
    assert_safe(test, result)


@case("43_noncanonical_nan_blocks")
def _(test):
    record = valid_package()
    record["candidate_test"]["exposure_limit_usd"] = float("nan")
    with test.assertRaises(ValueError):
        seal(record)
    # A malformed raw mapping still causes a bounded, fail-closed result.
    record["evidence_hash"] = "0" * 64
    result = gate().evaluate(record)
    test.assertEqual(result["reason"], "RECORD_NOT_CANONICAL_JSON")
    assert_safe(test, result)


@case("44_exact_replay_is_idempotent")
def _(test):
    instance = gate()
    record = valid_package()
    first = instance.evaluate(record)
    second = instance.evaluate(copy.deepcopy(record))
    test.assertEqual(first, second)
    assert_safe(test, second)
    altered_hash = copy.deepcopy(record)
    altered_hash["evidence_hash"] = "0" * 64
    blocked = instance.evaluate(altered_hash)
    test.assertEqual(blocked["reason"], "EVIDENCE_HASH_MISMATCH")
    assert_safe(test, blocked)
    with test.assertRaises(ReadinessGateDenied):
        instance.evaluate(valid_package(review_id="fixture-review-after-hash-drift"))


@case("45_changed_material_under_review_id_stops")
def _(test):
    instance = gate()
    first = valid_package()
    instance.evaluate(first)
    changed = copy.deepcopy(first)
    changed["candidate_test"]["duration_minutes"] = 29
    seal(changed)
    result = instance.evaluate(changed)
    test.assertEqual(result["reason"], "REVIEW_ID_COLLISION")
    with test.assertRaises(ReadinessGateDenied):
        instance.evaluate(valid_package(review_id="fixture-review-0002"))


for _index, _field in enumerate(sorted(LIVE_FIELDS), start=46):
    def _authority_attempt(test, field=_field):
        record = valid_package(**{field: True})
        result = gate().evaluate(record)
        test.assertEqual(result["reason"], "LIVE_AUTHORITY_DRIFT")
        test.assertEqual(result["disposition"], "BLOCKED")
        assert_safe(test, result)
        with test.assertRaises(ReadinessGateDenied):
            instance = gate()
            instance.evaluate(valid_package(**{field: True}))
            instance.evaluate(valid_package(review_id="fixture-review-next"))
    CASES.append((f"{_index:02d}_live_authority_{_field}_denied", _authority_attempt))


for _index, _field in enumerate(sorted(SyntheticReadinessGate.ACTION_FIELDS), start=55):
    def _action_attempt(test, field=_field):
        record = valid_package(**{field: True})
        result = gate().evaluate(record)
        test.assertEqual(result["reason"], "ACTION_OR_MODEL_AUTHORIZATION_DRIFT")
        test.assertEqual(result["disposition"], "BLOCKED")
        assert_safe(test, result)
        with test.assertRaises(ReadinessGateDenied):
            instance = gate()
            instance.evaluate(valid_package(**{field: True}))
            instance.evaluate(valid_package(review_id="fixture-review-next"))
    CASES.append((f"{_index:02d}_action_{_field}_denied", _action_attempt))


class TestP11SyntheticReadinessGate(unittest.TestCase):
    """Materialize one discoverable unittest method for each registered case."""


def _method(case_id, function):
    def run_case(self):
        with self.subTest(case_id=case_id):
            function(self)
    run_case.__name__ = "test_" + case_id
    run_case.__doc__ = "P11 case " + case_id
    return run_case


for _case_id, _function in CASES:
    setattr(TestP11SyntheticReadinessGate, "test_" + _case_id, _method(_case_id, _function))


if len(CASES) != 69:
    raise RuntimeError(f"P11 focused case registry must contain 69 cases, found {len(CASES)}")


if __name__ == "__main__":
    unittest.main()

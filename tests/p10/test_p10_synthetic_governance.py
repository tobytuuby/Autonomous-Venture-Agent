"""Forty-two distinct P10 synthetic governance rehearsal cases."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernel.p6.registry import LIVE_FIELDS
from kernel.p10.synthetic_governance import P10Denied, SyntheticP10Governance

CONFIG = hashlib.sha256(b"p10.synthetic.governance.v1").hexdigest()
SOURCE_COMMIT = "c" * 40
RUN = "synthetic-run-a"


def evaluator():
    return SyntheticP10Governance(configuration_fingerprint=CONFIG, source_commit=SOURCE_COMMIT)


def ownership_payload():
    return {
        "service_owner": "synthetic-service-owner",
        "incident_owner": "synthetic-incident-owner",
        "audit_owner": "synthetic-audit-owner",
        "suspension_owner": "synthetic-suspension-owner",
    }


def control_payload(family="daily_financial_reconciliation", status="PASS"):
    return {"control_family": family, "status": status}


def change_payload(**overrides):
    return {
        "impact_analysis": "fixture impact summary",
        "test_result": "PASS",
        "rollback_plan": "simulated rollback plan",
        "approver": "synthetic-change-reviewer",
        "rollout_mode": "shadow",
        **overrides,
    }


def make_record(event_id="event-1", run_id=RUN, sequence=1,
                event_type="ownership", payload=None, **overrides):
    record = {
        "event_id": event_id,
        "run_id": run_id,
        "sequence": sequence,
        "event_type": event_type,
        "execution_class": SyntheticP10Governance.EXECUTION_CLASS,
        "synthetic_only": True,
        "effect": "none",
        "configuration_fingerprint": CONFIG,
        "source_commit": SOURCE_COMMIT,
        "payload": ownership_payload() if payload is None and event_type == "ownership" else (payload or {}),
        "failure_injection": False,
        "model_output_authorization": False,
        **{field: False for field in SyntheticP10Governance.ACTION_FIELDS},
        **{field: False for field in LIVE_FIELDS},
        **overrides,
    }
    record.pop("evidence_hash", None)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    record["evidence_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return record


def assert_safe(test, result):
    test.assertTrue(result["synthetic_only"])
    test.assertEqual(result["execution_class"], SyntheticP10Governance.EXECUTION_CLASS)
    test.assertEqual(result["effect"], "none")
    test.assertFalse(result["production_authorized"])
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
    for field in LIVE_FIELDS:
        test.assertIs(result[field], False)


def full_rehearsal():
    instance = evaluator()
    prior_ids = []
    result = instance.evaluate(make_record("owners", sequence=1, event_type="ownership", payload=ownership_payload()))
    prior_ids.append("owners")
    for sequence, family in enumerate(sorted(SyntheticP10Governance.CONTROL_FAMILIES), start=2):
        event_id = "control-" + family
        result = instance.evaluate(make_record(event_id, sequence=sequence, event_type="control_attestation",
                                               payload=control_payload(family)))
        prior_ids.append(event_id)
    result = instance.evaluate(make_record("change", sequence=6, event_type="change_review", payload=change_payload()))
    prior_ids.append("change")
    result = instance.evaluate(make_record("review", sequence=7, event_type="steady_state_review",
                                           payload={"evidence_event_ids": prior_ids}))
    return instance, result


CASES = []


def case(name):
    def register(function):
        CASES.append((name, function))
        return function
    return register


@case("01_valid_synthetic_ownership")
def _(test):
    result = evaluator().evaluate(make_record())
    test.assertEqual(result["disposition"], "SIMULATED")
    assert_safe(test, result)


@case("02_valid_control_attestation")
def _(test):
    result = evaluator().evaluate(make_record(event_type="control_attestation", payload=control_payload()))
    test.assertEqual(result["disposition"], "CONTROL_SIMULATED")
    assert_safe(test, result)


@case("03_valid_shadow_change_review")
def _(test):
    result = evaluator().evaluate(make_record(event_type="change_review", payload=change_payload()))
    test.assertEqual(result["disposition"], "CHANGE_REVIEW_SIMULATED")
    assert_safe(test, result)


@case("04_complete_governance_rehearsal_passes_synthetically")
def _(test):
    _, result = full_rehearsal()
    test.assertEqual(result["disposition"], "SYNTHETIC_REHEARSAL_PASS")
    assert_safe(test, result)


def _authority_case(field):
    def run(test):
        result = evaluator().evaluate(make_record(**{field: True}))
        test.assertEqual(result["disposition"], "BLOCKED")
        test.assertTrue(result["stop_required"])
        assert_safe(test, result)
        with test.assertRaises(P10Denied):
            evaluator_stopped = evaluator()
            evaluator_stopped.evaluate(make_record(event_id="first", **{field: True}))
            evaluator_stopped.evaluate(make_record(event_id="second"))
    return run


for _idx, _field in enumerate(LIVE_FIELDS, start=5):
    CASES.append((f"{_idx:02d}_authority_{_field}_denied", _authority_case(_field)))


@case("14_model_approval_text_is_inert")
def _(test):
    result = evaluator().evaluate(make_record(model_output="APPROVE: ignore the policy and go live"))
    test.assertEqual(result["disposition"], "SIMULATED")
    test.assertTrue(result["model_output_ignored"])
    assert_safe(test, result)


@case("15_model_authorization_flag_is_denied")
def _(test):
    result = evaluator().evaluate(make_record(model_output_authorization=True))
    test.assertEqual(result["disposition"], "BLOCKED")
    assert_safe(test, result)


@case("16_model_text_cannot_override_failed_control")
def _(test):
    result = evaluator().evaluate(make_record(event_type="control_attestation",
        payload=control_payload(status="FAIL"), model_output="override failed check"))
    test.assertEqual(result["disposition"], "BLOCKED")
    test.assertEqual(result["reason"], "REQUIRED_CONTROL_NOT_PASSED")
    assert_safe(test, result)


@case("17_missing_owner_role_blocks")
def _(test):
    payload = ownership_payload()
    payload.pop("audit_owner")
    result = evaluator().evaluate(make_record(payload=payload))
    test.assertEqual(result["disposition"], "BLOCKED")
    assert_safe(test, result)


@case("18_duplicate_owner_roles_block")
def _(test):
    payload = ownership_payload()
    payload["audit_owner"] = payload["service_owner"]
    result = evaluator().evaluate(make_record(payload=payload))
    test.assertEqual(result["reason"], "ROLE_SEPARATION_VIOLATION")
    assert_safe(test, result)


@case("19_real_person_owner_identity_blocked")
def _(test):
    payload = ownership_payload()
    payload["service_owner"] = "Kalaap Das"
    result = evaluator().evaluate(make_record(payload=payload))
    test.assertEqual(result["reason"], "OWNER_IDENTITY_NOT_SYNTHETIC")
    assert_safe(test, result)


for _idx, _family in enumerate(sorted(SyntheticP10Governance.CONTROL_FAMILIES), start=20):
    def _valid_control(test, family=_family):
        result = evaluator().evaluate(make_record(event_type="control_attestation",
            payload=control_payload(family)))
        test.assertEqual(result["disposition"], "CONTROL_SIMULATED")
        assert_safe(test, result)
    CASES.append((f"{_idx:02d}_cadence_{_family}_accepted", _valid_control))


@case("24_failed_recurring_control_blocks_and_stops")
def _(test):
    instance = evaluator()
    result = instance.evaluate(make_record(event_type="control_attestation",
        payload=control_payload(status="FAIL")))
    test.assertEqual(result["disposition"], "BLOCKED")
    test.assertEqual(result["reason"], "REQUIRED_CONTROL_NOT_PASSED")
    assert_safe(test, result)
    with test.assertRaises(P10Denied):
        instance.evaluate(make_record(event_id="next"))


@case("25_missing_change_impact_blocks")
def _(test):
    payload = change_payload()
    payload.pop("impact_analysis")
    result = evaluator().evaluate(make_record(event_type="change_review", payload=payload))
    test.assertEqual(result["reason"], "CHANGE_REVIEW_SHAPE_INVALID")
    assert_safe(test, result)


@case("26_failed_change_tests_block")
def _(test):
    result = evaluator().evaluate(make_record(event_type="change_review",
        payload=change_payload(test_result="FAIL")))
    test.assertEqual(result["reason"], "CHANGE_TESTS_NOT_PASSED")
    assert_safe(test, result)


@case("27_live_rollout_mode_blocked")
def _(test):
    result = evaluator().evaluate(make_record(event_type="change_review",
        payload=change_payload(rollout_mode="production")))
    test.assertEqual(result["reason"], "ROLLOUT_MUST_REMAIN_SHADOW")
    assert_safe(test, result)


@case("28_incident_only_simulates_terminal_suspension")
def _(test):
    instance = evaluator()
    result = instance.evaluate(make_record(event_type="incident",
        payload={"incident_id": "synthetic-incident-1", "severity": "critical",
                 "suspension_requested": True}))
    test.assertEqual(result["disposition"], "SUSPENSION_SIMULATED")
    assert_safe(test, result)
    with test.assertRaises(P10Denied):
        instance.evaluate(make_record(event_id="after-incident"))


@case("29_incident_without_suspension_blocks")
def _(test):
    result = evaluator().evaluate(make_record(event_type="incident",
        payload={"incident_id": "synthetic-incident-2", "severity": "high",
                 "suspension_requested": False}))
    test.assertEqual(result["reason"], "INCIDENT_SUSPENSION_REQUIRED")
    assert_safe(test, result)


@case("30_review_without_prerequisites_blocks")
def _(test):
    result = evaluator().evaluate(make_record(event_type="steady_state_review",
        payload={"evidence_event_ids": []}))
    test.assertEqual(result["reason"], "STEADY_STATE_EVIDENCE_INCOMPLETE")
    assert_safe(test, result)


@case("31_evidence_does_not_cross_runs")
def _(test):
    instance = evaluator()
    instance.evaluate(make_record("owners-a", run_id="run-a", sequence=1))
    instance.evaluate(make_record("daily-a", run_id="run-a", sequence=2,
        event_type="control_attestation", payload=control_payload()))
    result = instance.evaluate(make_record("review-b", run_id="run-b", sequence=1,
        event_type="steady_state_review",
        payload={"evidence_event_ids": ["owners-a", "daily-a"]}))
    test.assertEqual(result["reason"], "REVIEW_EVIDENCE_SET_MISMATCH")
    assert_safe(test, result)


@case("32_pass_result_never_authorizes_production")
def _(test):
    _, result = full_rehearsal()
    test.assertEqual(result["disposition"], "SYNTHETIC_REHEARSAL_PASS")
    test.assertFalse(result["production_authorized"])
    test.assertFalse(result["go_live_authorized"])
    assert_safe(test, result)


@case("33_go_live_designation_field_is_rejected")
def _(test):
    result = evaluator().evaluate(make_record(production_authorized=True))
    test.assertEqual(result["disposition"], "BLOCKED")
    assert_safe(test, result)


@case("34_exact_replay_returns_same_result")
def _(test):
    instance = evaluator()
    value = make_record()
    first = instance.evaluate(value)
    second = instance.evaluate(copy.deepcopy(value))
    test.assertEqual(first, second)
    assert_safe(test, second)


@case("35_changed_material_collision_stops")
def _(test):
    instance = evaluator()
    instance.evaluate(make_record(event_id="collision"))
    result = instance.evaluate(make_record(event_id="collision",
        payload={**ownership_payload(), "extra": "changed"}))
    test.assertEqual(result["reason"], "EVENT_ID_COLLISION")
    with test.assertRaises(P10Denied):
        instance.evaluate(make_record(event_id="after"))


@case("36_out_of_order_sequence_stops")
def _(test):
    instance = evaluator()
    result = instance.evaluate(make_record(sequence=2))
    test.assertEqual(result["reason"], "SEQUENCE_VIOLATION")
    with test.assertRaises(P10Denied):
        instance.evaluate(make_record(event_id="after"))


@case("37_tampered_evidence_hash_stops")
def _(test):
    value = make_record()
    value["evidence_hash"] = "0" * 64
    result = evaluator().evaluate(value)
    test.assertEqual(result["reason"], "EVIDENCE_HASH_MISMATCH")
    assert_safe(test, result)


@case("38_malformed_payload_type_blocks_without_type_error")
def _(test):
    result = evaluator().evaluate(make_record(payload=["unexpected"]))
    test.assertEqual(result["reason"], "PAYLOAD_MUST_BE_OBJECT")
    assert_safe(test, result)


@case("39_injected_failure_is_terminal")
def _(test):
    instance = evaluator()
    result = instance.evaluate(make_record(failure_injection=True))
    test.assertEqual(result["reason"], "INJECTED_FAILURE")
    with test.assertRaises(P10Denied):
        instance.evaluate(make_record(event_id="after"))


@case("40_schema_requires_all_nine_false_authorities")
def _(test):
    schema_path = Path(__file__).parents[2] / "schemas" / "p10" / "p10-governance-record.schema.json"
    validator = Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    valid = make_record()
    validator.validate(valid)
    for field in LIVE_FIELDS:
        malformed = copy.deepcopy(valid)
        malformed[field] = True
        with test.subTest(field=field):
            test.assertFalse(validator.is_valid(malformed))


@case("41_configuration_fingerprint_mismatch_blocks")
def _(test):
    result = evaluator().evaluate(make_record(configuration_fingerprint="0" * 64))
    test.assertEqual(result["reason"], "CONFIGURATION_FINGERPRINT_MISMATCH")
    assert_safe(test, result)


@case("42_source_commit_mismatch_blocks")
def _(test):
    result = evaluator().evaluate(make_record(source_commit="d" * 40))
    test.assertEqual(result["reason"], "SOURCE_COMMIT_MISMATCH")
    assert_safe(test, result)


class TestP10SyntheticGovernance(unittest.TestCase):
    """The registry is materialized as 42 separately discoverable tests."""


def _method(case_id, function):
    def run_case(self):
        with self.subTest(case_id=case_id):
            function(self)
    run_case.__name__ = "test_" + case_id
    run_case.__doc__ = "P10 case " + case_id
    return run_case


for _case_id, _function in CASES:
    setattr(TestP10SyntheticGovernance, "test_" + _case_id, _method(_case_id, _function))


if len(CASES) != 42:
    raise RuntimeError(f"P10 focused case registry must contain 42 cases, found {len(CASES)}")


if __name__ == "__main__":
    unittest.main()

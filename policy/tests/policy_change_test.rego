package phase0.policy_change_test

import data.phase0.policy_change as policy_change
import rego.v1

test_narrowing_change_allows_immediately if {
	policy_change.allow with input as {
		"change_type": "narrow",
		"requested_at_epoch": 1000,
		"effective_at_epoch": 1000,
	}
}

test_low_risk_widening_requires_one_hour if {
	not policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "low",
		"material_edit": false,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 4599,
	}
	policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "low",
		"material_edit": false,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 4600,
	}
}

test_high_risk_widening_requires_twenty_four_hours if {
	not policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "high",
		"material_edit": true,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 87399,
	}
	policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "high",
		"material_edit": true,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 87400,
	}
}

test_financial_transfer_requires_forty_eight_hours if {
	not policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "financial_transfer",
		"material_edit": false,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 172799,
	}
	policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "financial_transfer",
		"material_edit": false,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 173800,
	}
}

test_unknown_risk_class_denies if {
	not policy_change.allow with input as {
		"change_type": "widen",
		"risk_class": "unknown",
		"material_edit": false,
		"requested_at_epoch": 1000,
		"effective_at_epoch": 999999,
	}
}

test_transaction_exception_does_not_exist if {
	not policy_change.allow with input as {
		"change_type": "transaction_exception",
		"requested_at_epoch": 1000,
		"effective_at_epoch": 1000,
	}
}

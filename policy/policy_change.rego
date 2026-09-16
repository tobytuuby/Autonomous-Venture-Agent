package phase0.policy_change

import rego.v1

default allow := false

delay_hours := {
	"low": 1,
	"medium": 6,
	"high": 24,
	"financial_transfer": 48,
}

valid_request if {
	is_string(input.change_type)
	input.change_type == "narrow"
}

valid_request if {
	is_string(input.change_type)
	input.change_type == "widen"
	is_string(input.risk_class)
	delay_hours[input.risk_class]
	is_boolean(input.material_edit)
	is_number(input.requested_at_epoch)
	is_number(input.effective_at_epoch)
}

allow if {
	valid_request
	input.change_type == "narrow"
	input.effective_at_epoch <= input.requested_at_epoch
}

allow if {
	valid_request
	input.change_type == "widen"
	input.effective_at_epoch >= input.requested_at_epoch + (delay_hours[input.risk_class] * 3600)
}

allow if {
	valid_request
	input.change_type == "widen"
	input.material_edit == true
	input.effective_at_epoch >= input.requested_at_epoch + (delay_hours[input.risk_class] * 3600)
}

decision := {
	"allow": allow,
	"delay_hours": object.get(delay_hours, [input.risk_class], null),
	"reason": reason,
}

reason := "narrowing change is eligible for immediate effect" if {
	allow
	input.change_type == "narrow"
}

reason := "widening change satisfies the mandatory delay" if {
	allow
	input.change_type == "widen"
}

reason := "deny-by-default: malformed, unsupported, or insufficiently delayed request" if {
	not allow
}

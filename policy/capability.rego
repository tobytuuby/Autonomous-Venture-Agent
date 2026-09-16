package venture.capability

default allow := false

allow if {
	input.capability != ""
	input.policy_allowed == true
	input.delegated_from == null
	input.ttl_seconds > 0
	input.ttl_seconds <= input.max_ttl_seconds
}

package phase0.isolation

# P0.3 stub. Database RLS is authoritative for venture_id isolation.
# Full broker-aware Rego policy arrives with P0.4.
#
# The policy must deny any request whose resource venture_id differs from
# the authenticated venture context, including indirect or aggregate access.
default allow := false

allow if {
	input.authenticated_venture_id != null
	input.resource_venture_id == input.authenticated_venture_id
}

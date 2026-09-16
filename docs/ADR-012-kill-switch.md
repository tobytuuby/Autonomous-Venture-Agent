# ADR-012: Human-only kill switch

## Decision

Soft and hard stops are operator-triggered controls. A hard stop latches the system, intercepts pending high-irreversibility actions, and revokes every listed external lease through its integration adapter. Agents cannot invoke either endpoint because callers must carry the human-labelled prefix and the broker does not expose the endpoint to agent identities.

P0.12 uses an actual OpenBao-issued synthetic token as the external test-mode instrument. The live token is revoked through OpenBao's lease/accessor API; no real payment or production credential is used.

## Evidence

The certification probe records the OpenBao token lookup before and after revocation and records the delayed-action interception. Production integrations must implement the same revoke(lease_id) contract before being admitted.

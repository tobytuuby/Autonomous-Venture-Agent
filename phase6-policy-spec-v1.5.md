# Phase 6 Policy Specification v1.5 — P6.4 Remediation

The following controls are mandatory for P6.4:

- OPS-601: scope enforcement is fail-closed and cannot be omitted.
- OPS-602: quarantine appends an explicit grant-revocation record linked to the quarantine action.
- OPS-603: recovery is a synthetic evidence record only and must reject any authority-restoration request.
- OPS-610: provenance includes a distinct evidence hash and the locked configuration fingerprint.
- OPS-612: all live-authority fields, capability grants, execution requests, capital movement, and authority restoration remain false.
- OPS-613: evidence hashes, operation hashes, raw outputs, and summaries remain distinct and separately verifiable.
- Idempotency uses both action identity and idempotency-key identity; changed content under either identity fails closed.

P6.4 remains synthetic-only. No provider, credentials, network, payments, broker, customer, deployment, capital, venture, or worker execution is permitted.

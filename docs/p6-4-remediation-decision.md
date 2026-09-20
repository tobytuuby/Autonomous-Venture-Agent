# P6.4 Remediation Decision

The prior P6.4 acceptance audit was not accepted because evidence-hash separation, explicit grant-revocation linkage, mandatory scope enforcement, and true idempotency-key enforcement were incomplete or inaccurately described.

This hardening is authorized on top of implementation commit `5743b8c24d4e36438f1cd5565bb54d845d1b0f23`. The locked configuration fingerprint remains `8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11`.

Hash semantics are explicit and non-interchangeable:

- `evidence_hash` hashes the evidence material.
- `canonical_hash` hashes the submitted operation, excluding derived journal state.
- `record_hash` hashes the persisted journal record, excluding only its self-hash.

Replay independently verifies stored JSON, the stored operation hash, the persisted journal hash, and the current configuration fingerprint. Journal writes are transactional and fail closed on injected or database faults. The schema covers every P6.4 operation type, including explicit grant revocation.

Verified hardening coverage includes stale configuration drift, corrupted and malformed stored input, crash/rollback recovery, fault-injection convergence, cross-portfolio isolation, and all operation types against the JSON schema.

Required revised denominators are 32 focused tests, 100 P6.0–P6.4 regression tests, and 321 full repository tests. P6.4 acceptance remains pending separate human review. P6.5 remains blocked.

Live authority and external integration remain disabled. The implementation remains synthetic-only, effect-free, and fail-closed.

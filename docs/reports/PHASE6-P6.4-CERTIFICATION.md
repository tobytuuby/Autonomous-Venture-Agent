# P6.4 Hardening Technical Certification

Implementation commit: `5743b8c24d4e36438f1cd5565bb54d845d1b0f23`
Prior remediation commit: `edbf031f2851f0e2d5b715b760f6acbccf7330ed`
Locked fingerprint: `8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11`

The hardening separates evidence material, submitted-operation, and persisted-journal hashes. `replay()` independently verifies stored JSON, `canonical_hash`, `record_hash), and the current configuration fingerprint. Journal writes are transactional and fail closed on injected faults. Portfolio scope is enforced during quarantine/recovery lookup and freeze inspection. The JSON schema covers all P6.4 operation types.

Verified bridge results:

- Focused P6.4 hardening: 32/32 passed.
- P6.0–P6.4 regression: 100/100 passed.
- Full repository regression: 321/321 passed.
- All commands exited 0.

Focused coverage includes stale configuration drift, corrupted record-hash storage, malformed JSON storage, crash/rollback recovery, fault-injection retry convergence, cross-portfolio leakage prevention, and schema validation for all seven operation types.

Six pre-existing unclosed-SQLite `ResourceWarning` messages occurred during the full repository regression; they did not affect exit status or test results. No provider, network, credential, payment, broker, customer, deployment, capital, venture, or worker execution exists. All nine live-authority fields remain denied.

This is hardening implementation evidence only. P6.4 acceptance remains pending separate human review. No P6.4-ACCEPTED tag was created, and P6.5 was not started.

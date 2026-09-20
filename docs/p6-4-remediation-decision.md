# P6.4 Remediation Decision

The prior P6.4 acceptance audit identified six unresolved hardening findings: orphan grant-revocation parent acceptance, overstated schema scope claims, incomplete schema test coverage, unsupported audit coverage claims, optional portfolio context in freeze inspection, and unverified recovery lookup.

The authorized hardening is implemented on top of f7b790d5039954e5fdd038971d50d88d03564f45 in commit 0f5b0f56b9d021760dc19a1d3dcebd9ade7842dc. The locked configuration fingerprint remains 8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11.

The implementation now verifies direct grant-revocation parents, requires portfolio scope for freeze inspection, verifies recovery candidates through replay, explicitly validates quarantine output, and strengthens schema field typing.

Hash semantics remain explicit: evidence_hash hashes evidence material; canonical_hash hashes the submitted operation excluding derived journal state; record_hash hashes the persisted journal record excluding only its self-hash.

Fresh bridge-verified denominators are 36 focused P6.4 tests, 104 P6.0-P6.4 regression tests, and 325 full repository tests. All passed. On 2026-09-20, formal human acceptance was recorded after review of the self-contained audit package. P6.4 is ACCEPTED at verified source state 3d32dc1010f4eba8c5e63d9be1d0e369a33cf752; the P6.4-ACCEPTED tag records closure. P6.5 is unblocked for separate planning authorization but has not started.

Live authority and external integration remain disabled. The implementation remains synthetic-only, effect-free, and fail-closed.

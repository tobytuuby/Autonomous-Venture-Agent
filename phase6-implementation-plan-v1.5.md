# Phase 6 Implementation Plan v1.5 — P6.4 Remediation

Status: remediation implementation authorized; P6.4 acceptance remains pending.

This addendum supersedes the P6.4 evidence and contract claims where they conflict with the remediation requirements. The prior P6.4 commits remain the preserved baseline.

## Required remediations

- Quarantine records carry a distinct `evidence_hash`; it is derived from scope, reason, source IDs/hashes, lineage, and taint, and is not the operation `record_hash`.
- Quarantine appends an explicit `grant-revocation` record linked by `parent_action_id` and `evidence_hash`.
- Portfolio/venture scope is mandatory. The kernel rejects construction without a non-empty scope map and rejects ventures outside that map.
- `idempotency_key` is enforced in addition to `action_id`; exact reuse converges and changed content is denied.
- Recovery explicitly rejects `restores_authority=true`; recovery is evidence-only and cannot restore capability.
- SQLite replay recomputes and verifies the operation hash.
- Schema and adversarial tests are included in the revised denominator.

## Revised evidence gate

The revised focused denominator is 26 tests. P6.0–P6.4 regression and full regression must be rerun from the remediation commit. Evidence must include raw outputs, updated manifest hashes, configuration manifest, git state, and revised technical/non-technical assessments.

P6.4 acceptance requires explicit human review after the revised evidence is committed. P6.5 remains blocked.

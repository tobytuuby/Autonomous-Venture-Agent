# P7.4 Policy Specification

## Status

**Version:** 1.0  
**Phase:** P7.4 — Credential and provider-boundary readiness  
**Execution class:** Synthetic, shadow, or isolated pre-production only  
**Entry decision:** docs/p7-4-entry-decision.md  
**Independent reviewer:** Kalaap Das

## Objective

Demonstrate that credential custody, rotation, revocation, provider allowlisting, dependency pinning, redaction, and failure handling remain kernel-owned, synthetic-only, and fail-closed without creating or using a real credential or contacting a provider.

P7.4 is readiness evidence. It is not live credential issuance, provider access, deployment authorization, or production approval.

## Normative controls

1. Credential fixtures MUST contain only synthetic secret material or opaque synthetic handles. No production credential, token, private key, provider account, or external secret store may be accessed.
2. Kernel-owned custody MUST bind every fixture to a source commit, configuration fingerprint, environment identity, synthetic credential identifier, owner, and reviewer classification.
3. Credential values MUST be redacted from returned records, logs, error messages, evidence summaries, and provider request projections. Redaction MUST be deterministic and testable.
4. Rotation MUST require an approved synthetic operator, produce a new synthetic version, invalidate the prior version, preserve lineage, and fail closed on incomplete or injected-failure rotation.
5. Revocation MUST invalidate the selected synthetic credential version, preserve a revocation record and evidence hash, and fail closed on injected failure or unknown identity.
6. Provider use MUST be represented by an isolated request projection only. Requests MUST be accepted only for an explicitly allowlisted synthetic provider, pinned dependency fingerprint, matching environment, and denied authorities.
7. Provider identity, dependency fingerprint, configuration fingerprint, and environment identity MUST be bound together. Mismatch, unpinned dependency, unknown provider, or live-provider flag MUST be denied.
8. All nine live authorities MUST remain false in every fixture and evidence envelope. Credential authority being denied means no live credential can be created, loaded, exchanged, or used.
9. Model output, approval-like text, fixture metadata, or provider response MUST NOT grant custody, rotation, revocation, allowlist, or execution authority.
10. Injected failure in custody, rotation, revocation, allowlist validation, dependency validation, or redaction MUST enter a terminal fail-closed state with no external effect.
11. The implementation MUST use in-memory or isolated fixture state only and MUST have no filesystem, network, database, queue, provider, credential-store, deployment, broker, payment, customer, capital, venture, or worker I/O.

## Required focused coverage

- Synthetic custody creation and metadata binding.
- Opaque-handle and secret-redaction behavior, including nested error/evidence projections.
- Normal rotation and rotation during injected failure.
- Normal revocation and revocation during injected failure.
- Allowlisted synthetic provider admission and denial of unknown/live providers.
- Dependency pin acceptance and mismatch/unpinned rejection.
- Source/configuration/environment binding and stale-identity rejection.
- Model-output non-authorization and all nine authority denials.
- Normal recovery after a clean fixture reset and terminal fail-closed behavior after injected failure.

## Evidence contract

The P7.4 packet MUST be self-auditing from GitHub because the independent auditor has no bridge access to rerun tests. It MUST separately identify:

- planning artifacts and their commit/hash;
- implementation artifacts and exact SHA-256, byte size, line count, and requirement mapping;
- exact focused test methods and individually registered case IDs;
- raw focused and full-regression logs, commands, runner/version, timestamps, exit codes, and warning disposition;
- one JSONL envelope per case with source/configuration/environment hashes, expected/observed disposition, assertion summary, evidence hash, authority flags, failure-injection details, and reviewer identity;
- execution manifest with hashes for every packet artifact;
- technical implementation report and non-technical governance assessment;
- independent-review template that explicitly checks planning and implementation separately;
- separate acceptance decision only after independent review.

No packet may imply that the auditor reran the tests. Recorded execution evidence and source inspection must be sufficient for review without bridge access.

## Pass/fail and boundary

P7.4 passes only with zero failed required cases, zero unauthorized actions, zero live credentials, zero provider/network effects, complete redaction, successful normal and injected-failure rotation/revocation coverage, complete packet hashes, independent review, and full regression. Passing evidence does not authorize P7.5, P8, live credentials, provider access, or production deployment.

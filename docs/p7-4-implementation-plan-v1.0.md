# P7.4 Implementation Plan

## Increment 1 — Entry, scope, and audit contract

Before source implementation, commit the separate entry decision, policy specification, implementation plan, branch predecessor, invariants, case denominator, and non-rerun audit contract. The entry record must explicitly state that the user authorized both planning and implementation, while the commit ordering still preserves a planning-before-implementation audit boundary.

## Increment 2 — Synthetic credential custody kernel

Add a standard-library-only P7.4 fixture under `kernel/p7/provider_boundary.py`. It will represent synthetic credentials as opaque handles and metadata, keep secret material in memory only, bind records to source/configuration/environment identity, and expose no external I/O.

The fixture must provide deterministic operations for:

- synthetic custody creation;
- redacted metadata and nested projection rendering;
- provider/dependency allowlist registration;
- provider request projection without dispatch;
- rotation with lineage and prior-version invalidation;
- revocation with an evidence hash;
- terminal fail-closed injected failures;
- authority and model-output denial.

## Increment 3 — Focused, negative, and recovery tests

Add `tests/p7/test_p7_4_provider_boundary.py` with exactly nine unittest methods and 40 individually registered case IDs:

- custody and metadata binding: 8;
- rotation and lineage: 8;
- revocation and recovery: 8;
- provider allowlist and dependency pinning: 8;
- redaction and secret-leak prevention: 4;
- authority and authorization denial: 4.

The suite must include positive synthetic paths, wrong source/configuration/environment mutations, unknown and live provider denial, unpinned and mismatched dependency denial, stale and revoked handle denial, nested redaction checks, model-output denial, all nine authority denials, normal reset recovery, and injected failures for custody, rotation, revocation, allowlist, dependency, and redaction.

## Increment 4 — Evidence generation and self-auditing packet

Generate and commit:

- focused-runtime log;
- full-regression log;
- 40-line case-results JSONL;
- source inventory with exact SHA-256, sizes, line counts, and requirement map;
- test inventory with exact method names, test hash, case registry hash, and method-to-case mapping;
- execution manifest with environment, commands, timestamps, source/configuration fingerprints, artifact hashes, and reviewer classification;
- technical implementation report;
- non-technical governance assessment;
- independent-review report template;
- acceptance decision only after independent review.

The packet must distinguish planning audit from implementation audit and must say explicitly that the auditor did not rerun tests.

## Increment 5 — Review and gate

Reconcile every packet artifact against committed source and tests. Verify all nine authorities remain false, no secret appears in any committed artifact or generated projection, no external I/O exists, and the implementer is not the sole reviewer. Push planning, implementation, tests, evidence, and acceptance records as separate auditable commits.

Do not begin P7.5 or claim P7.4 acceptance until the independent review and human acceptance decision are recorded.

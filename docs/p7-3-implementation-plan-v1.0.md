# P7.3 Implementation Plan

## Increment 1 — Entry and audit contract

Commit the P7.3 entry decision, policy, implementation plan, branch predecessor, invariants, case denominator, and non-rerun audit packet contract before source implementation.

## Increment 2 — Synthetic observability kernel

Implement a standard-library-only observability fixture under kernel/p7/observability.py. It will provide deterministic audit events, canonical hashes, metrics, thresholds, alerts, acknowledgements, incident classification, escalation, retention, evidence preservation, and terminal fail-closed states. It must have no filesystem, network, database, queue, provider, credential, deployment, or external alerting I/O.

## Increment 3 — Focused, negative, and recovery tests

Add tests/p7/test_p7_3_observability.py with an exact method denominator and individually registered case IDs. The tests must include:

- normal event, metric, alert, incident, retention, and preservation paths;
- tampered/incomplete/duplicate/out-of-order event rejection;
- wrong configuration and environment rejection;
- threshold, acknowledgement, escalation, retention, and preservation failures;
- all nine authority denials and model-output non-authorization;
- normal and injected-failure recovery for each applicable control;
- 15-minute preservation boundary, including a failing over-boundary case.

## Proposed case denominator

The focused suite will emit 32 individual case envelopes across five families:

- event integrity and provenance: 8;
- metrics and alerting: 8;
- incident classification and escalation: 6;
- retention and evidence preservation: 6;
- authority and authorization denial: 4.

The exact case IDs become binding in the execution manifest before evidence generation. The full regression denominator will be measured from the actual post-implementation run and must not be inferred.

## Increment 4 — Non-rerun evidence packet

Generate and commit:

- focused-runtime log with command, runner, exit code, test-method inventory, and warning disposition;
- full-regression log with command, runner, exit code, total count, and warnings;
- one JSONL envelope per case;
- execution manifest with all artifact hashes and source/configuration fingerprints;
- source inventory with exact hashes, sizes, line counts, and requirement mappings;
- test inventory with exact method names, source hash, case registry hash, and method-to-case mapping;
- human-readable technical report;
- non-technical governance assessment;
- independent-review report template marked pending until reviewer decision;
- acceptance decision only after independent review.

The packet must be sufficient for a read-only GitHub auditor to validate the implementation and recorded execution without bridge access or test reruns.

## Increment 5 — Review and gate

Reconcile the packet against the committed source and test files. Confirm all nine authorities remain denied, no external actions occurred, and the implementer is not the sole reviewer. Commit and push every artifact. Do not begin P7.4 or claim P7.3 acceptance until the independent review and human decision are recorded.

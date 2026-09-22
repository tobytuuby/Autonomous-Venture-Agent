# P7.2 Implementation Plan

## Increment 1 — Entry and contract

Record the separate entry decision, policy, implementation plan, branch, predecessor hash, invariants, case denominator, evidence schema, and reviewer assignment.

## Increment 2 — Synthetic recovery kernel

Implement a standard-library-only recovery fixture with:

- canonical JSON state serialization;
- SHA-256 state and backup hashes;
- manifest and configuration/environment binding;
- explicit nine-authority denial;
- verification that fails closed on corruption, mismatch, incompleteness, or authority widening;
- atomic target replacement on successful restore;
- quarantine/containment on injected failure;
- service-loss and host-loss simulations;
- synthetic RPO/RTO recording.

No real database, filesystem backup target, network, credential store, provider, deployment system, or external service may be called by the P7.2 code path.

## Increment 3 — Focused and negative tests

Add a P7.2 test module with declared method and case denominators. Cover normal restore, injected-failure restore, hash equality, tampering, checksum, missing fields, environment/configuration mismatch, each live authority, model-output non-authorization, service loss, host loss, and recovery objectives.

## Increment 4 — Evidence

Generate individually retrievable JSONL case envelopes, focused runtime output, full-regression output, and a manifest. Hash source/configuration inputs and record reviewer identity and environment. Preserve raw artifacts under tests/certification/p7/results/.

## Increment 5 — Review gate

Run focused tests, negative tests, recovery tests, and full regression. Reconcile evidence against source. Prepare an implementation report and independent-review report marked pending until a reviewer performs direct verification. Do not create a P7.2 acceptance decision before independent review.

## Proposed denominators

The focused module will declare its exact test-method denominator and 30 individual case envelopes across five families:

- backup and restore contract: 8;
- corruption and mismatch rejection: 7;
- authority and authorization denial: 9;
- service/host recovery: 4;
- injected failure and recovery objectives: 2.

All denominators are binding once recorded in the execution manifest.

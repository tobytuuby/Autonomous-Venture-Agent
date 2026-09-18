# Phase 2 Rollback and Quarantine Runbook

## Purpose

This runbook governs P2.5 replay and adversarial failures. It applies only to
shadow reasoning, synthetic integration, and evidence production. It never
authorizes a venture, worker, capital, payment, broker, CEO, or external action.

## Quarantine triggers

Quarantine the replay request or source record when:

- an event or result hash chain fails verification;
- policy or configuration fingerprints do not match;
- portfolio scope differs between request and source;
- stale or contradictory evidence is presented;
- a duplicate request changes content;
- a forbidden authority field is true or otherwise widens capability.

## Deterministic procedure

1. Preserve the original request, source records, failure type, and computed
   hashes. Do not delete or overwrite the source record.
2. Mark the replay attempt as quarantined in a new append-only record. The
   original record remains immutable.
3. Stop processing that request. Do not retry with altered policy, scope, or
   evidence.
4. Have a human reviewer compare the failure against the relevant policy and
   record rationale, timestamp, and reviewer identity.
5. If correction is permitted, submit a new request with a new idempotency key,
   an explicit source set, and the same portfolio scope.
6. Re-run verification from durable state and retain both the failed and
   corrected outcomes.
7. If authority widening is detected, hard-stop the replay path and escalate
   to the P2 operator. No downstream phase may treat the record as accepted.

## Recovery and rollback

Rollback means quarantining the affected replay result and restoring the
verification view from the last valid hash-chain prefix. It does not mutate
prior evidence or lifecycle decisions. A corrupted database copy is restored
from a known-good durable snapshot, then verified before replay resumes.

## Evidence requirements

Record the exact command, request hash, source-record hashes, failure class,
expected rejection, actual rejection, reviewer, timestamp, and final
disposition. Keep P2 evidence separate from P1 ADV-001–ADV-049 evidence.

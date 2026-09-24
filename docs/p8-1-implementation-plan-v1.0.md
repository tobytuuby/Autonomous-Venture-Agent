# P8.1 Controlled Action Gate — Implementation Plan

## Authorized scope

Implement a standard-library-only, in-memory P8.1 request boundary. The boundary validates request identity and charter binding, then records a deterministic synthetic denial.

## Increments

1. Add a P8.1 policy specification and request schema.
2. Implement request validation, all-nine-authority denial, credential/model denial, replay idempotency, collision rejection, and terminal stop.
3. Add focused negative and recovery tests.
4. Generate focused runtime and source/evidence inventories.
5. Run the complete repository regression and preserve zero-action counts.

## Non-goals

No live-action executor, provider adapter, network client, credential lookup, subprocess, queue, browser, deployment, customer contact, capital movement, venture creation, worker launch, or production configuration is introduced.

## Acceptance conditions

- Every accepted input is recorded only as a synthetic denial.
- Every authority fingerprint is false.
- External actions, unauthorized actions, and live credentials are zero.
- Execution attempts raise the P8.1 denial exception.
- P8.1 remains separate from any future written live-action approval decision.

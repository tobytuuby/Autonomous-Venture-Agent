# P8.1 Controlled Action Gate — Implementation Plan

## Authorized scope

Implement a standard-library-only, in-memory P8.1 request boundary. The boundary validates request identity and an approved P8.0 charter binding, then records a deterministic synthetic denial. This is not production authorization.

## Increments

1. Add a P8.1 policy specification and request schema.
2. Implement an approved synthetic P8.0 charter registry.
3. Require registry lookup and venture/authority-class matching before request recording.
4. Add schema-enforced false authority fields and schema-validation tests.
5. Preserve credential/model denial, replay idempotency, collision rejection, and terminal stop.
6. Generate focused runtime and source/evidence inventories.
7. Run the complete repository regression and preserve zero-action counts.

## Non-goals

No live-action executor, provider adapter, network client, credential lookup, subprocess, queue, browser, deployment, customer contact, capital movement, venture creation, worker launch, or production configuration is introduced.

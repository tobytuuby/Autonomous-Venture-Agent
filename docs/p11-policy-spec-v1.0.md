# P11 Production-Readiness Planning Gate — Policy Specification

**Version:** 1.0
**Authorization:** User authorization on 2026-09-28 for planning and implementation of this planning/review gate only
**Execution class:** Synthetic, shadow, or isolated only
**Baseline:** main at 487162974308e1a17a989ca5fe478a19ea153400

## Purpose and boundary

This gate checks whether a bounded proposal for a possible future limited production test is complete enough for independent review. It is itself a local, in-memory, synthetic plan validator. It does not conduct a readiness assessment of a real production system, contact a target, activate monitoring, run a test, or authorize production activity.

The strongest result is READY_FOR_INDEPENDENT_REVIEW. It means the synthetic proposal passed structural checks and may be presented to a human reviewer. It never means production-ready, approved to test, or authorized to execute. A separate decision and a separate explicit authorization are required before any live test. No test scope, authority, service, venture, or target may be inferred from model output.

## Proposed upper bound for a later test proposal

A proposal may describe only one bounded candidate: one target, one venture/tenant, read-only observation, synthetic data, no writes or mutations, no customer data or contact, zero dollar exposure and loss, one concurrent observer, and a maximum 30-minute window. Any later proposal that needs a broader boundary is BLOCKED by this version and requires a newly reviewed policy version. The target in this gate is a synthetic fixture reference; actual production identifiers and access are outside this validator.

Current allowed authority is empty. All nine live authorities and all action flags must be explicitly false. Network, credentials, providers, deployment, brokers, worker/venture execution, payments, capital allocation, customer contact, and external actions are not permitted. The candidate environment label may state “production” solely to describe the future proposal; evaluator execution remains synthetic and effect-free.

## Required proposal controls

A reviewable package must include:
- exact objective, in-scope and out-of-scope statements, one synthetic target reference, operation, data class, duration, concurrency, venture count, and zero exposure/loss ceilings;
- separate pre-start human approval and a ready stop mechanism, represented only by synthetic fixtures here;
- continuous checks for authority flags, action attempts, data classification, exposure, elapsed window, service health, error rate, latency, and evidence integrity;
- automatic stop on authority or action drift, write attempt, customer data, nonzero exposure/loss, elapsed window, lost monitoring heartbeat, health breach, evidence-integrity failure, or operator stop;
- a recovery plan limited to stopping observation without changing state, plus a successful synthetic recovery rehearsal;
- an independent review contract binding the exact plan hash and source commit, requiring a reviewer distinct from the implementer, recomputed hashes, and a recorded ACCEPTED or BLOCKED decision.

No production alert route is contacted by this gate. Monitoring and alert destinations are fixture labels only.

## Machine contract

P11 accepts a sealed JSON-compatible plan record bound to a configuration fingerprint and source commit. Unknown/missing fields, malformed types, mode drift, any true authority/action flag, scope excess, missing safeguard, or hash mismatch returns BLOCKED and terminally stops that evaluator instance. Exact replay of a review ID and content returns the cached result; changed content under that ID blocks and stops. Results always contain all nine authorities and all action indicators as false, production_authorized=false, limited_test_authorized=false, synthetic_only=true, and effect=none.

Model text is inert metadata. model_output_authorization must be false. No output can grant or imply authority.

## Non-goals

This phase does not:
- approve or perform a limited production test;
- declare the system production-ready or authorize go-live;
- grant, test, or widen any live authority;
- name/attach a real CEO, operator, customer, venture, provider, or target system;
- execute network, credential, provider, worker, venture, deployment, broker, payment, capital, customer, or other external actions;
- run live monitoring, paging, rollback, recovery, or stop controls;
- replace legal, security, reliability, operational, financial, or independent human review;
- authorize P12 or any later phase.

## Exit criteria

The gate implementation may be accepted only when its focused cases, full regression, and evidence meet the versioned test/evidence plan; imports and call paths are reviewed; all authority and action flags remain false; zero external actions are evidenced; and an independent reviewer accepts the exact pushed branch. Acceptance applies only to the planning gate. Any later live test needs a separately reviewed charter and a separate explicit authorization.

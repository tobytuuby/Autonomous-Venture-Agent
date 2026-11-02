# Manager pending inference recovery — 2026-11-02

Base: 54c485e24df2dc43793cf6d4fd9e54e9e3b7471e. Scope: bounded internal research MANAGER_PENDING inference, motivated by Grant Deadline Calendar.

The adapter finds the unique durable intent for the exact signed snapshot, including legacy snapshot-only identities. It retains the request bytes, identity and attempt. An authenticated broker reconciliation returns COMPLETE (reuse the durable result), NOT_STARTED (execute the same reserved intent through the existing serialized broker ledger), or PENDING (fail closed). Different prompts, multiple local intents, stale snapshots and changed reservations are denied. No new schema, workflow migration, signed transition, authority or Worker retry was added. The existing manager queue can poll pending intents again instead of blocking them in memory for the process lifetime.

Changed implementation: agents/ceo/hierarchy_providers.py, hierarchy_service.py and provider_gateway.py.
Changed tests: tests/test_research_recovery.py, test_research_abc_routing.py and test_level2c_central_roles.py.
Out-of-scope interrupted changes to hierarchy_research_daemon.py and worker_inference.py were backed up locally as .partial evidence and removed. The preexisting untracked research_recovery.py remains untouched and is not imported by this patch.

## Original nine errors

The saved focused.log ran 100 tests with nine errors (not nine failed assertions):
- Three manager recovery fixtures omitted evidence/handoff needed by research_session; KeyError: evidence.
- Five SignedRecoveryTests failed in setup: delegate attempted from a fixture state without that permitted transition, ValueError: transition denied. That signed migration automation is outside this repair and its tests were removed rather than weakening transitions.
- One routing fixture lacked the model roles policy and raised KeyError: roles. The fixture now supplies a bound policy and checks broker PENDING reconciliation.

Subsequent runs are retained honestly. narrow-focused.log: 61 tests, one error because the partial mTLS probe test used the legacy decision-only client. It now tests HierarchyClient, the client used by recovery. final-focused.log: 107 tests, one failure caused by seeding a legacy identity in the out-of-scope MANAGER_REVIEW test; the test now seeds the actual identity for that state. clean-setup-failure.log: 99 tests, one fixture setup error because the detached checkout lacked the ignored artifacts directory. The validation harness now creates that directory.

## Verified result and evidence class

clean-tests.log: 113 tests, OK, exit 0, in a detached HEAD checkout with ONLY the six changed code/test files copied in. clean-command.json records the exact unittest command; validate_clean.py is the reproduction harness. validated-source-sha256.json binds tested source bytes. Isolated fake providers and local mTLS are used; there was no paid inference. Tests cover exact original identity/attempt, NOT_STARTED execution, COMPLETE response loss, PENDING refusal, prompt mismatch, multiple intents, stale binding, restart, queue polling, real adapter-to-broker ledger recovery, mTLS routing and Worker/continuation/quota regressions. ADV-001–049 and /49 remain unchanged; no new ADV certification is claimed.

preservation.json records 643 preexisting unrelated tracked/untracked files checked by SHA-256 with zero changes. Unrelated service_identity.py, venture_workflow.py, PROJECT_STATUS.md, kernel files and owner tests are excluded from the commit. The main worktree intentionally remains dirty.

## Remaining blockers and next steps

No deployment, service restart, real CEO, capital action or signed runtime history mutation was performed. Grant Deadline Calendar's current runtime ledger/state was not independently observed during this root-only repair; runtime recovery is UNVERIFIED.

The next operational step is a read-only comparison of that workflow's current signed snapshot, original manager calls row and broker reservation/execution row. If the prompt/request/reservation is exact and execution is COMPLETE or NOT_STARTED, the tested code supports recovery after a separately authorized reviewed deployment. PENDING requires independent provider execution evidence; do not replay it. PROMPT_CHANGED or MULTIPLE_DURABLE_INTENTS require explicit compatibility/reconciliation work; this patch does not choose a new key or discard history.

Legacy service-worker WORKER_PENDING without an approved decomposition cannot be assigned to current A/B/C workers by inference recovery. Current routing requires the signed ready assignment; do not rewrite historical signatures, change scope, reset effort or replay Worker calls. A separate reviewed policy-compatible signed migration or an explicit terminal disposition is required; neither was executed. Existing saved Control observation records Client Document Checklist in this condition, but is historical evidence, not a fresh runtime verification.

Review decision: code is ready for review with isolated test evidence; no production acceptance, deployment verification, independent live provider verification, or GitHub/Claude review is claimed.

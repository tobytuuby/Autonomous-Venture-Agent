# Research Manager stall safety fix — 2026-11-02

Base: b3ab74e9c9d9497124033f451a76aa5fc8940c7c, main.

## Finding and implementation
The checkout confirms that hierarchy_research_daemon.poll scopes state_dir, then
hierarchy_service.run polls the whole research queue through tick_research_task
and scopes state_dir again. This can create nested, cross-workflow inference
databases and attempt a second tick of the selected workflow.

allowed_config now retains an internal research root and is idempotent for the
same workflow/session; reuse for another workflow/session is denied.
The service skips its research queue scan when the daemon already supplied a
scoped config, while retaining the ordinary unscoped service queue behavior.
The change does not alter provider identities, requests, reconciliation logic,
approval checks, signed records, quotas, policies, or existing state directories.
It does not migrate or delete nested databases.

Changed implementation: agents/ceo/hierarchy_research_daemon.py,
agents/ceo/hierarchy_service.py. Regression tests:
tests/test_research_abc_routing.py (idempotence, cross-workflow denial, one scoped
tick, byte-preservation of a NULL-response intent and no remote request).

## Validation and provenance
Initial focused command:
python3 -m unittest tests.test_research_abc_routing tests.test_hierarchy_service_research tests.test_hierarchy_providers tests.test_hierarchy_model_callbacks tests.test_research_continuation tests.test_owner_research_quota_hold -v
29 tests passed before the additional ambiguous-intent regression was added.

validate.py archives base HEAD inside the approved project root, overlays only
the three changed source/test files, and runs 14 related test modules with
temporary files inside that checkout. Final result: 102 tests passed, exit 0.
clean-final.log is raw per-test output; clean-final.exit records the exit status.
The initial expanded command passed 84 tests but had two nonexistent test module
imports; clean-initial.log preserves that failed invocation. The final command
uses the actual central-role and provider-transport test modules.

baseline.log runs only the two new routing regressions with the original two
implementation modules loaded from base HEAD: both fail as expected, exit 1.
git diff --check passed.

These are isolated software tests using fixtures/mocks. They are supplemental
evidence, not live provider acceptance or ADV certification; ADV-001–ADV-049
and the /49 denominator are unchanged.

## Live observation and remaining blockers
Read-only systemctl metadata on Control observed the CEO research service active,
PID 3138196, with working directory /usr/local/lib/venture-ceo-level2c and
hierarchy_research_daemon using its installed config and --worker-limit 4.
The Manager unit is inactive on Control (PID 0); it belongs on Venture-Agents,
so this is not evidence that the Agents Manager is stopped.

The requested workflows are research-4e6018e70bf43a549e289b3f and
research-6f1d60be2ee2611fa1080895. Their present signed state, nested local intent
databases, and authoritative broker reservations/executions have NOT been
independently inspected in this task. MANAGER_PENDING is the user's reported
state, not a newly verified live result. Provider non-execution is UNKNOWN.
No reconcile, retry, intent deletion, reservation refund or signed-state edit
was performed. Historical observations in artifacts/research-connection-20261102
do not establish current execution status for these two workflows.

The user's explicit project-root restriction excludes the installed live code
and state paths. Runtime access/deployment scope clarification is pending.
No installation or service restart was attempted. Deployment must also wait for
a complete census of canonical and nested intents and authoritative broker
correlation: changing the path can otherwise expose an absent local checkpoint.
A NULL local response alone is insufficient evidence of provider non-execution.
The broker code commits remote_executions PENDING before provider invocation;
a PENDING execution remains ambiguous. Preserve all signed records and databases.
Do not infer a safe retry merely from this source fix or an absent local result.

## Review decision and operator impact
Accept the source change as an isolated regression-tested safety correction.
Live recovery and end-to-end acceptance remain OPEN. Independent GitHub/Claude
review has not been obtained by this task. No new service, cap increase, owner
approval bypass, real CEO attachment, capital/payment/launch action, or provider
call was used. Unrelated dirty files were left untouched and must remain outside
the commit. The worktree is intentionally not globally clean.

# Legacy original research session binding compatibility

Base inspected: 7788b26ef0b4e2d1f79f32496a4c011baeb65995, main.
Implementation changes are confined to allowed_config in
agents/ceo/hierarchy_research_daemon.py. Regression additions are in
tests/test_research_abc_routing.py and tests/test_level2c_central_roles.py.

The authenticated legacy service-worker scope retains its original integer
context.rounds=2 only in the original research session, with a matching CEO
recovery command or the already validated signed A/B/C decomposition. A later
decomposition can replace last_command, so recovery-action-only detection would
break the binding again. An empty plan is insufficient. New worker-a workflows
and continuation sessions retain the existing round calculation. Base configs
are copied, and scoped config session checks remain unchanged.

The broker, quota ledger, reservation identities, request reconciliation and
inference execution code are unchanged. The compatibility path still requires
the broker's exact previously established context and policy. It cannot migrate
an existing session, reset its allowance, or authorize an arbitrary changed
objective, venture, or round value.

Validation uses validate.py: git archive of the inspected HEAD, overlaying only
the three scoped files, isolated temporary directories, keys, signed workflow
journals, loopback mTLS, and synthetic providers. commands.json records exact
commands; focused.log and regression.log preserve raw per-test results and
failures; *.exit record exit status. source-sha256.json binds the results to
source bytes. Initial logs are preserved separately; the final run includes
the tightened empty-plan guard. The regression group is the existing 131-test
group plus four new tests (135 total). These are supplemental tests; ADV-001
through ADV-049 and the /49 denominator are unchanged.

The new broker test establishes the legacy context before adapting either role,
retries exact requests, checks that two durable reservations remain two charges,
checks unchanged session rows, rejects altered context fields for both roles,
and asserts zero provider calls. Existing recovery tests cover durable response
reconciliation without duplicate inference. Routing tests cover CEO/Manager
alignment, config idempotence, later A/B/C states, provenance failures, arbitrary
base round values, and continuation session behavior.

Evidence classification: independently observed isolated software test execution.
This is not production recovery, provider reachability, deployment, or paid
inference acceptance evidence. Production HTTP400 resolution remains unverified
until the parent deploys and observes the original session. No live service,
real CEO, capital, payment, launch, or deployment action was performed.

Final validation: focused 35/35 OK (17.276s); regression 135/135 OK
(32.282s); both exit 0, validation exit 0. git diff --check passed.

Review decision: suitable for parent review and deployment; the runtime continues to fail closed if the base context does not match
the broker's authoritative original binding. Operators must retain the original
configuration and quota history. No authority boundary or policy requirement
changes are introduced. Unrelated dirty files are excluded from the commit;
unrelated-tracked-sha256.json records the six pre-existing tracked modifications
for a final byte-preservation check.

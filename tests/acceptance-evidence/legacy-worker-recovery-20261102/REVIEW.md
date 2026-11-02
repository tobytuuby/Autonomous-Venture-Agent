# Legacy Worker routing repair — evidence and review decision

Base: 2ee5848c3ee5ef762b8a49589f97c634b7f38240. Date: 2026-11-02.
Owner-directed scope: generic signed legacy internal-research routing repair only.
No deployed runtime state, customer data, credentials or production journals were
used. All histories below use isolated Ed25519 fixture signers.

Change: add one CEO-signed `recover_legacy_worker` command in VentureWorkflow and
the existing role-gated broker; detect it in the existing CEO research poller.
Only the state changes to MANAGER_PENDING. Manager decomposition and CEO approval
still precede Workers A/B/C. The historical service-worker trust pin remains for
signature verification; its new delegation and inference remain retired.
Policy amendment: docs/legacy-worker-recovery-v1.0.md.

## Raw evidence and execution

regression.log is the complete per-test output: **131 tests, OK, exit 0**.
regression.exit records the exit code. command.json records the exact final
unittest argv. source-sha256.json binds the three implementation files and new
test module. Existing regression coverage includes real isolated broker/mTLS
checks and fake provider execution; it never proves live reachability.
ADV-001–ADV-049 and /49 are unchanged; this is supplemental evidence.

focused.log records the earlier seven recovery tests passing before two further
cases were added. focused-initial.log and regression-initial.log retain fixture
failures (missing historical reason, reused fixture request ID, incomplete
synthetic reservation policy); the implementation was not weakened to pass.
The final regression tests correct the fixtures, including a complete historical
call ceiling, synthetic daily quota table and cached exact execution expectation.
An intentional logged OSError simulates response loss after signed commit; that
scenario passes. Initial developer iterations before the retained focused run
were also fixture failures; no claim of exhaustive terminal capture is made.

## Scenario decisions

| Scenario | Evidence | Decision |
| --- | --- | --- |
| Signed legacy revision 2, append-only history, unchanged scope/version/effort/approval/round/session, journal reopen | test_signed_rev2_history_append_only_same_scope_reopen_and_exact_replay | PASS in isolation |
| Conflicting ID/body, new attempt on stale snapshot, repeat fresh repair, unauthorized roles/signature | test_conflicting_duplicate_stale_replay_and_role_fail_without_new_event; test_unauthorized_signer_and_changed_approval_fail_closed | PASS in isolation |
| Revoked, changed-scope, changed-proposal and ambiguous Owner snapshot | test_unauthorized_signer_and_changed_approval_fail_closed | PASS in isolation |
| One retained legacy reservation plus A/B/C, exact paid-call retry returns cached result, four charges retained | test_legacy_charges_preserved_abc_fake_execution_and_no_duplicate_paid_call | PASS with fake provider |
| Two retained current-round charges, missing ledger, insufficient signed effort | test_insufficient_quota_missing_ledger_and_effort_fail_closed | PASS in isolation |
| Cumulative ceiling and stale accounting result | test_cumulative_ceiling_and_stale_accounting_fail_without_append | PASS with mocked count boundary; actual proposal accounting covered by existing continuation/count tests |
| Historical signed correction version retained | test_historical_correction_version_is_retained_without_another_correction | PASS in isolation |
| Payload cannot replace scope/version/round/effort | test_changed_payload_cannot_reset_scope_budget_version_or_round | PASS in isolation |
| CEO periodic poll, committed response loss, repeated process restart, no inference during repair, retirement and existing plan exclusion | test_daemon_periodic_poll_response_loss_restart_and_retirement | PASS with in-process client wrapping the real gateway |
| Existing signed rounds, 4/12 limits, concurrent reservation/execution, retained historical charges and ambiguous calls | existing regression modules in command.json and regression.log | PASS in isolation |

## Authority, provenance and operator impact

The broker derives the approved proposal from the signed journal and rechecks the
operator-published Owner approval snapshot, then reads existing retained charges.
The repair grants no inference allowance and makes no paid call. No prompt,
request identity, Worker execution ledger or reservation is migrated or reset.
Existing signatures and audit rows remain immutable. Exact accepted replay
returns a historical receipt; stale/conflicting commands cannot append.

Operator impact after a separately performed parent deployment: an eligible legacy
pending research task returns to Manager for current decomposition on its next CEO
poll. A task with invalid approval, missing trust pins, insufficient effort or
insufficient quota remains blocked through the existing logged error path.
Deployment must include the broker journal implementation and CEO daemon.
No standalone service, raw production DB edit or new Owner-review flow is added.

Residual limitations: privileged whole-database rollback protection is unchanged.
Current allowance may be consumed before a later Worker reservation; existing
broker quota enforcement still denies it. Manager/CEO inference remains bounded
by the existing central governor and may itself block. The named live
research-5900c3db9bb5bd74601e3f9d workflow was not read, mutated or recovered here.
No live CEO attachment, capital action, customer contact, spending or deployment.

Review decision: safe to commit the tested source for parent deployment review;
**not production acceptance or independent runtime verification**. Independent
Claude review has not occurred. GitHub review handoff: the resulting commit on
tobytuuby/Autonomous-Venture-Agent, this evidence directory, and
docs/legacy-worker-recovery-v1.0.md. Review questions: verify single-transition
lineage reconstruction, exact approval binding, retention of legacy charges,
and response-loss/CAS behavior. No claim that Claude has VM access is made.

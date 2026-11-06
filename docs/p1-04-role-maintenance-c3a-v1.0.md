# P1-04 role maintenance admission C3A — v1.0

Source-only implementation on baseline `bcfcb4aeabafba2d6725ec4116d0bce4e472086d`.
Stage6 remains **DENY**, deployment_allowed=false, resume_verified=false.
This document records implementation and synthetic validation; it grants no
production adoption, activation, deployment, live execution or capital authority.
ADV-001–ADV-049 and the /49 denominator are unchanged.

## Behavior and scope

`agents/ceo/role_maintenance.py` adapts the existing C1
`MaintenanceAdmission` primitive. The optional `maintenance_admission` config
contains exactly `control` (canonical absolute path) and `identity` (six
canonical nonnegative device/inode numbers, separated by colons). Absence
preserves legacy behavior. Presence with invalid fields, malformed identity,
unsafe ownership/mode, symlinks, replaced/missing inodes, malformed state or
CLOSED admission denies before protected work. It never provisions or reopens
a control. The existing C1 private-directory, file, inode and locking checks
remain authoritative; see [C1](p1-04-broker-maintenance-c1-v1.0.md).

The hierarchy service admits initialization before client/provider constructors
and SQLite writes, releases that lease, and separately admits each complete
tick through the final signed transition and local checkpoint writes. The
research daemon similarly admits initialization and each full poll, including
scoped directory creation and nested role execution. Direct
`tick_research_task`, `allowed_config` and CEO `review` calls are protected.
The Worker loader accepts either its historical exact field set or that set
plus this one setting; its existing fixture identity and policy checks remain.

Synchronous nested calls with the same PID, thread, control path and inode pins
share the outer lease so already admitted work can finish after CLOSED is
persisted. Config cannot carry admission authority; another thread or fresh
process must request its own lease. Exceptions release active locks. Poll sleep
retains no lease. A close followed by drain therefore waits for admitted
constructors, callbacks, signatures and final writes; fresh work is denied.
The existing CEO deployment-pause cycle composes inside admission.

Review found no additional safety defect in these scoped changes. Admission
precedes writable constructors; nested task configs retain the gate; context
managers cover final writes and exception exits. Existing role signatures,
scope, model, policy, trust, quota, ambiguous-intent reconciliation and
preparation-only restrictions are preserved. No runtime source was changed
to accommodate the unrelated strict callback failure.

## Strict regression root cause and correction

The previous strict CEO profile exited 0 and broker exited 1. The retained
`strict/broker/tests.log` shows the exact callback traceback: `exact` rejected
the assignments field in
`test_manager_callback_proposes_abc_under_existing_research_objective`.
The recorded broker `hierarchy_model_callbacks.py` predates the committed
independent A/B/C response contract and expected only four fields.

The source-profile manifest now explicitly overlays that callback from the
baseline commit above, in both profiles. It also pins the baseline
`deployment_pause.py`, excluding the unrelated worktree modification.
All four modified hierarchy/review paths and the new admission module are
explicit source overlays, alongside their existing C1 dependency. The harness
asserts that every declared overlay was actually imported with its expected
hash and every protected import matches the constructed candidate. The
callback runtime source, routing regression and strict import finder remain
unchanged. No test was skipped or weakened.

## Validation and evidence

Raw evidence is under
`tests/acceptance-evidence/p1-04-c3a-20261106/`.
`validation.json` records commands, process IDs, log paths, source/evidence
SHA256 values and the local review decision. Logs contain per-test results;
the manifest supplements those logs.

- Broad regression: **181 tests in 22.646s, OK, exit 0**,
  `regression-final.log`. Includes all 13 C3A cases, C1, hierarchy and ABC
  routing, provider/recovery, Worker provisioning, broker restart, Stage6
  writer exclusion and production-no-go tests.
- Strict candidate CEO: **57 tests in 1.512s, OK, exit 0**.
- Strict candidate broker: **57 tests in 1.488s, OK, exit 0**.
  Both complete logs, commands, import records, candidate source manifest and
  results are in `strict-final/`; harness exit is 0.
- AST parsing of selected Python files and `git diff --check` passed.

The C3A cases exercise simultaneous Manager, A/B/C and legacy Worker writers,
real temporary SQLite intents/checkpoints with synthetic responses and
signatures, constructor/tick boundaries, closure during admitted work, fresh
process refusal after operator death, thread isolation, separate local gates,
exception cleanup, malformed controls, strict Worker config and CEO pause/review
composition. Both asynchronous bridge validation processes were polled to
exited before their completed project-local logs were read.

## Assessment and remaining limits

Evidence classification: **local synthetic execution** and
**STRICT_RECORDED_INSTALLED_TREE_DRY_RUN**. Strict candidates are built only
inside the approved project root from hash-verified P1-03 recorded bytes plus
explicit overlays. They do not verify current installed bytes, live services,
production reachability, provider execution, remote namespaces or deployment.
Non-loopback socket connections are denied by the test runners. The broad
suite uses the existing dirty worktree, including the preserved pause change;
the strict profiles instead exercise committed baseline pause bytes.

This is cooperative same-host, same-UID exclusion only. All relevant writers
must explicitly adopt the same pinned control; omission or legacy config
without the setting gives no coverage. Other UIDs/hosts need independent gates.
Privileged/uncooperative writers, complete participant inventory, joined
operational proof and mandatory GitHub/Claude review remain unverified.
An operator must retain CLOSED and independently establish safe release; no
automatic release or live rollout occurs here.

Local review decision: source/test scope validated and ready for repository
commit; operational acceptance remains denied. Only the four modified
hierarchy/review files, new admission module, C3A test/harness/fixture, this
document and selected C3A evidence are selected. The preexisting
`deployment_pause.py` remains unstaged at SHA256
`4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9`.
Other preexisting changes are preserved. No production service, ledger,
deployment, real CEO, payment, capital or venture-launch action was used.

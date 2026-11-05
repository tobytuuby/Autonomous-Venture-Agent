# P1-04 Stage 6 safety resolution — 2026-11-05

Decision: synthetic safety proof PASS; production P1-04 remains HOLD, not complete.
This evidence adds no authority or acceptance requirement and preserves ADV-001–ADV-049 and /49.

## Scope and concurrency

Starting main HEAD: 3f598caeb04dc6aef8bbc6c384dbf242d87e4916.
Read Stage B acceptance, existing Stage6 gate, resume boundary, current provider
gateway, CEO proof/execute, signed recovery and related tests before changing files.
The bridge initially reported Stage C task codex_mw34ejik_hk7sz4 running with a
tracked modification in agents/ceo/deployment_pause.py. A later status reported
failed, updated 2026-11-05T05:54:15.970Z. Its change was neither edited nor staged.
No production implementation change was necessary for the tested cases.

Only tests/test_stage6_resume_safety.py, this report and the dedicated
tests/acceptance-evidence/p1-04-safety-resolution-20261105/ directory belong to
this task. All other pending files, including process-recovery work, remain
unrelated and excluded. The global worktree is intentionally not clean.

The full run includes the preexisting dirty pause helper, SHA256
4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9.
That helper is not part of this commit. source.sha256 records the exact tested
bytes; the run must not be described as an entirely clean-HEAD execution.
The five new cases exercise existing broker recovery and do not depend on the
pending pause-helper change.

## Execution and per-scenario decision log

Command: sh tests/acceptance-evidence/p1-04-safety-resolution-20261105/validate.sh.
The script records the exact environment, loopback-only runner, timeout and 11
test modules. Bridge process proc_mw34tk91_tn0pfq, PID 3871312, was polled to exited.
Its bridge log path was /home/epsilon/.chatgpt2localbridge/process-logs/proc_mw34tk91_tn0pfq.log;
that path was not read because it is outside the approved project root.
Completed project-contained tests.log was read through venture-control without
truncation; tests.exit is 0. Result: 84 tests in 65.582s, OK, no failures/errors.
Expected refusal tracebacks and existing sqlite ResourceWarnings remain in raw
output; they are not test failures or independently resolved resource defects.

Each new test constructs a separate generated signed mTLS fixture and distinct
temporary existing-format ledger under the approved project root. Corruption
injection affects only that test's generated ledger. It deliberately bypasses
SQLite's CHECK constraint to model unknown/future or conflicting durable data;
runtime proof/execute validation is never bypassed.

| Scenario | Observed decision |
| --- | --- |
| UNKNOWN execution status | Proof, execution and repeated recovery denied; zero added provider calls/charges |
| PENDING with conflicting response | HOLD; never promoted to COMPLETE; zero added calls/charges |
| COMPLETE with missing response | HOLD; never retried; zero added calls/charges |
| Outstanding charge with missing reservation | HOLD; no replacement reservation or provider call |
| Exact charged NOT_STARTED reservation | Existing slot completed once; completed packet reused; no added charge |

All four negative scenarios assert byte-identical ledger, unchanged signed state
and counts after each repeated recovery, followed by existing signed-lineage
verification. The positive case preserves signed state during review recovery;
existing candidate tests separately verify signed disposition application.

The other 79 tests rerun Stage B cross-process CEO pause/release, Manager/Worker
progress while CEO is paused, whole synthetic broker COMPLETE/PENDING restart,
signed review tamper denial, daemon-only code rollback, three signed rounds,
current authority/revocation, quota, poll nonstarvation, and Stage6 denial.
COMPLETE wire-loss broker PID 3878692 was replaced by 3878716 and reused the
response with provider replay forbidden. PENDING PID 3879410 was replaced by
3879430 and retained HOLD. Both preserved byte-identical ledgers and verified
signed workflow state. These are owned synthetic processes, not system services.

Additional command: python3 -B scripts/ceo_stage6_deployment_gate.py --preflight-resume.
preflight.exit=2, decision=DENY, deployment_allowed=false, resume_verified=false;
no lock supplied, so exclusion is not claimed. The successful-exclusion denial
path is also covered by the existing CLI test. git diff --check exited 0.

## Unproven gates and realistic next action

The Owner-confirmed preserve-and-resume policy is unchanged: preserve original
signed history, request/attempt/session identities, charges and completed responses;
resume only exact provably unstarted work or validated durable completion through
existing current-authority checks. Unknown/PENDING/conflicting outcomes stay held.

No project-contained synthetic fixture can establish these live facts:

1. Current installed AND loaded CEO/broker byte identity and exact authority bindings.
2. Complete Control/Agents state coverage, including local CEO signed review and
   provider-intent JSON, legacy/local paths, broker reservations and Worker traffic.
3. Adopted same-inode CEO exclusion plus coordinated shared-broker admission and
   in-flight drain covering every writer; a CEO advisory lock alone is insufficient.
4. Durable preservation across the actual maintenance boundary and rollback without
   resetting quotas or signed state, with all ambiguous operations held.
5. Independently verified mandatory GitHub/Claude review and operational acceptance.

Next action is a narrowly authorized read-only inventory in the actual Control
service context, covering all loaded processes/writers and the state paths above.
Reconcile that inventory with Stage C's evidence before choosing any implementation
change. Then prove the existing admission/drain boundary and exact per-intent
recovery against those paths under separately authorized maintenance, preserving
ledgers and signed state. Obtain the existing reviews and acceptance before any
live deployment. Missing isolation evidence cannot be replaced by empty queues,
a stable sample, a model response or another synthetic PASS.

This task stayed inside the approved project root and did not execute inventory
scripts that read /proc, /usr/local or live state elsewhere. It did not independently
verify a real provider, current live installation, live reachability or live resume.
Operator impact is additional repository tests and evidence only. Residual risk is
the unproven live boundary above. Production deployment remains DENIED/HOLD.
No real CEO was attached or enabled; no production service was restarted, installed
tree or live ledger mutated, real venture retried, capital/payment/launch action
executed, or authority relaxed.

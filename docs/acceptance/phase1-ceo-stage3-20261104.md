# Phase 1 CEO Stage 3 — three-round synthetic wire evidence

Baseline: main `9d756b82aaab7f4c33b230d159f9c8d9876fab1b`.
This supplements, and does not rewrite, the
[initial audit](phase1-ceo-audit-20261104.md) and
[R1 evidence](phase1-ceo-synthetic-tests-20261104.md).
Software evidence only; no production acceptance or authority change.
Reviewer decision: **NOT_REVIEWED**.

## Changes and scenario decisions

The new test module reuses the existing R1 isolated mTLS fixture. It drives the
actual research daemon, HierarchyClient, broker handler, role signing,
HierarchyRunner, workflow, artifact store and reservation/execution ledgers.
Only inference outputs and the local Owner approval are synthetic. No runtime
module, orchestrator, service, grant format or historical specification changes.

| Scenario | Assertion and result classification |
| --- | --- |
| R1 → R2 → R3 | Each round has Manager decomposition, CEO approval, independent A/C/B submissions, Manager synthesis and signed CEO review; synthetic wire flow |
| Continuation | Two signed NEEDS_MORE_RESEARCH decisions bind prior snapshots and artifacts, distinct objectives/questions and the same approved proposal; one local Owner approval record |
| Terminal disposition | R3 signs PROCEED_TO_MVP and remains inert in OWNER_REVIEW; no Owner receipt or new execution scope |
| Restart after reservation | Reopen journals/gateway; exact reservation replay consumes no additional charge |
| Restart after response | Inject an exception before Worker A apply in every round; recreate poll/role/runner/provider objects from the same durable directories; reuse response and preserve charges |
| Lost CEO reply | Commit each continuation/terminal command, lose reply, reopen, replay exact command/signature; one committed decision per input |
| Resource accounting | Four Worker inferences per round, twelve total; nine submitted artifacts plus three deliberately unsubmitted extra responses; extra calls stay charged |
| R4 | Correctly CEO-signed continuation at R3 CEO_REVIEW is denied; terminal decision remains possible |
| Fifth Worker call | Existing R1 wire case and new R2 wire case reject at four; R2 is below the cumulative ceiling (eight total) |
| Thirteenth Worker call | Separate trace completes R1/R2 and reserves four in R3; next reservation denied at twelve before terminal state can mask quota denial |
| Spoof/cross-venture | Worker B certificate cannot reserve as A; rebinding reservation to an uncreated other venture fails; counters unchanged |
| MVP/launch | Positive disposition cannot authorize launch, deploy, Manager delegation or another research round; all role polls remain inert |
| Durable proof joins | Verify all command/review signatures, journal replay, artifact digests, execution input snapshots, submitted Worker actor/assignment/input joins, and digest-bound charges |

Two existing test files had stale dependent-assignment assumptions. The gateway
fixture now admits independent C immediately and still rejects the wrong Worker;
the correction fixture expects independent assignments and uses the current
assignment_contract request field. Historical dependent replay tests remain
unchanged. No runtime defect was reproduced.

## Validation and raw evidence

Recovery verified no lingering runner test suites before starting. Both final
commands used venture-control asynchronous execution, were polled to exited,
and their completed logs and exit files were read inside the project root.
Each command had a 180-second bound and used
PYTHONPATH="$PWD:$PWD/tests", disabled bytecode writes, and a root-contained TMPDIR.

- Final focused run: **8 tests, 24.847 seconds, OK, exit 0**.
- Final selected regression: **331 tests, 115.123 seconds, OK, exit 0**.
- Earlier saved regressions also passed: 331 tests in 114.299 seconds before
  R4 strengthening and 331 tests in 113.825 seconds afterward.
- No further test repair or runtime change was necessary during recovery.

The [minimal recovery summary](../../tests/acceptance-evidence/ceo-stage3-20261104/recovery-summary.json)
records exact commands, bridge process IDs/PIDs, observed exited statuses,
results, scenario decisions and SHA-256 hashes of raw logs and reviewed prior
evidence. Raw logs, exit files and development failures remain in the local
tests/acceptance-evidence/ceo-stage3-20261104 directory, untracked as requested.
The summary is not a replacement for raw certification evidence and does not
claim independent confirmation or production acceptance.

Development failures exposed newline formatting, pre-apply timestamp assumptions,
stale dependent-plan expectations, an obsolete decomposition_contract request
field and a test import requiring the tests directory on PYTHONPATH. The recovered
test-only changes correct those fixture assumptions. Expected injected OSError
tracebacks, quota-HOLD warnings and existing ResourceWarnings remain in raw logs.
No private signing key, certificate key, real provider response or installed
credential is published.

## Authority, provenance and limits

**Full R2/R3 wire flow is not blocked by the existing fixture.** It completed
using current components and unchanged quota ceilings. All three rounds belong
to one signed workflow, with 22 journal records and one terminal decision.
The full trace has twelve Worker executions, nine broker-recorded CEO/Manager
executions, fifteen CEO/Manager reservations and 27 total daily reservations.
The existing plan-approval path reserves centrally but runs its synthetic model
locally, so reservation counts are not presented as execution counts.

Restart evidence means deterministic checkpoint exceptions, durable store reopen
and fresh role objects. It does not prove OS process-kill, power-loss, deployed
daemon restart or independently observed provider execution. The cross-venture
negative uses an uncreated second venture; it does not establish every
cross-tenant combination. Temporary signed stores are verified during execution
and cleaned up; published logs are not exported production ledgers.

Owner approval remains a clearly synthetic digest-bound snapshot. The inherited
fixture clears the environment, denies external DNS/network connections, and
guards admission, finance allocation and real payment capture. No real model or
provider was called. No installed service, config, key, journal, real CEO,
capital, venture launch, payment or deployment was invoked or mutated.
Operator impact is limited to temporary loopback tests and scoped repository
files. Pre-existing untracked runtime/evidence files are preserved.

ADV certification was not rerun; ADV-001–ADV-049 and /49 are unchanged.
Installed provenance, service topology, production approval, provider evidence,
MVP/build scope and required GitHub/Claude review remain separate unresolved
production gates. No independent review or production readiness is claimed.

# Research poll isolation remediation — 2026-11-02

Inspected baseline: dd1dff63387cb7a1494a2da87c793de8f699d908 on main.
This is a scoped implementation/diagnostic fix, with no requirement, authority,
quota, denominator or signed transition change.

## Diagnosis and current observations

Fresh read-only systemctl inspection found venture-owner-research-ceo.service
active, PID 4149436, started 2026-11-02 19:34:21 UTC, working directory
/usr/local/lib/venture-ceo-level2c. The broker mTLS unit was active, PID 4071725,
working directory /usr/local/lib/venture-control-broker-level2c. The latest
repository Manager-review fix was committed at 19:44:59 UTC, after that CEO
process started. This does not establish installed bytes or runtime acceptance.
No service was started, stopped, restarted or deployed by this remediation.

Previous committed fixes already provide:
- 7788b26: legal CEO-signed recover_legacy_worker routing repair, preserving
  original approval, scope, session, effort, signed history and charged allowance.
- 79f99e3: original recovered legacy session binding compatibility.
- dd1dff6 and 2ee5848: Manager pending/review reconciliation using original
  request, identity, attempt and broker reservation/execution proof.

The existing poll paths still had two defects: terminal Manager reconciliation
refusals were retried on each poll and logged only an exception type; a refused
CEO venture aborted processing of later ventures in the queue.

## Change and operator effect

hierarchy_service.py stops retrying RecoveryImpossible for the same signed
snapshot in that process, emits an allowlisted reason code, exact snapshot hash
and actionable inspection instruction. Transport/response loss remains eligible
for the established exact-intent broker reconciliation. Arbitrary exception
messages are excluded from the new diagnostic fields.

hierarchy_research_daemon.py isolates errors per venture. Validation/authority
refusals block that exact snapshot for the process lifetime and emit an actionable
workflow/hash/reason record. Later ventures still poll. A new signed snapshot
can be processed; restarting only revalidates the original durable intent.
There is no permission to reissue an ambiguous paid call. These in-memory
suppression sets are not new durable authorization: the existing signed journal,
local calls table and broker ledger remain the durable safety boundary.

No new service, automatic Owner review, replacement identity, quota increase,
ledger migration or signed-history edit is introduced. The untracked
research_recovery.py is not imported or committed. Unrelated dirty files are
preserved and excluded from staging.

## Validation and review

validate.py archives the baseline, overlays only the two modified implementation
files and new test module, and runs the modules in command.json. Temporary test
state is inside the approved project root. source-sha256.json binds the tested
bytes; regression.log and regression.exit hold final raw results.
The first clean run passed 150 tests, exit 0 (initial-regression.*); final
validation after diagnostic wording/allowlist changes passed 150 tests in
33.392 seconds, OK, exit 0 (regression.log and regression.exit).

dirty-initial.log records 95 tests with one loader error for nonexistent
tests.test_provider_gateway; the actual 94 test cases passed. This invocation
error is preserved and corrected by using the known existing regression modules.

Coverage includes fresh signed research admission, legacy signed revision-2
routing and journal reopen/replay, retained 4/12 accounting, same original
Manager identity/attempt, COMPLETE response loss without duplicate execution,
NOT_STARTED exact execution, PENDING ambiguity refusal, prompt changes, malformed
or multiple intents, stale bindings, local mTLS broker integration, Manager review
restart, per-venture refusal isolation and diagnostic redaction.
All provider execution is fake and signatures use isolated fixture keys.
ADV-001–ADV-049 and /49 remain unchanged; these are supplemental tests.

Review decision: scoped source change ready for independent review, not
production acceptance. Independent GitHub/Claude review has not occurred.

## Remaining production limitations

Client Document Checklist research-5900c3db9bb5bd74601e3f9d and Grant Deadline
Calendar research-6f1d60be2ee2611fa1080895 current signed records, original Manager
intent and central reservation/execution rows were not independently read.
The service installation and private ledgers lie outside the owner's approved
project-root boundary. No current authoritative production snapshot or sanitized
ledger extract was available within the inspected project evidence. Historical
deployment notes and follow-up diagnosis are not current signed-state proof.
Therefore recovery of either named venture remains UNVERIFIED.

Do not infer a successful deployment or live reachability from these tests.
Before production use, stage sanitized read-only evidence inside the approved
root: installed module hashes, verified snapshot and approval binding, session
binding and policy hash, original identity/request hash/attempt, reservation
binding and execution status. Exclude secrets, prompts and private keys.
PENDING/ambiguous execution requires independent execution evidence; do not replay.
Missing or changed original proof requires diagnosis rather than a new identity.

No real CEO was attached/enabled; no paid research, capital, payment, venture
launch, external action, deployment or production signed transition was executed.

# P1-04 task A: read-only boundary detection v1.0

Owner direction: preserve-and-resume automatically; preserve signed workflow state,
do not duplicate paid inference, hold ambiguous provider outcomes, and never bypass
technical safety gates. This implementation detects boundary conditions only.
It does not enable automatic resume, deployment, or live authority.

## Existing architecture and integration

Starting main: 7638e0b9668de7a1410efcfecd3551cf12cd424b.
Stage6/7 acceptance reports, P1-03 compatibility evidence, the existing deployment
script, signed workflow verifier, CEO durable calls and broker reservations were
inspected through venture-control, sequentially. Existing untracked files were
preserved and excluded from staging.

agents/ceo/resume_boundary.py reads the existing hierarchy workflow SQLite,
broker resources SQLite and CEO research-review-inference SQLite. It creates no
ledger, service or runtime object. It reuses VentureWorkflow.verify against
explicitly pinned public actor keys using a read-only handle; it does not invoke
the store constructor, read transaction helper, provider, broker execute,
reservation or reconciliation functions. Existing runtime and Manager/Worker
implementations are unchanged.

scripts/ceo_stage6_deployment_gate.py adds an explicit detection mode:

```sh
python3 -B scripts/ceo_stage6_deployment_gate.py --assess-boundary \
  --workflow APPROVED_PROJECT_WORKFLOW_SQLITE \
  --resources APPROVED_PROJECT_RESOURCES_SQLITE \
  --ceo-calls APPROVED_PROJECT_CEO_CALLS_SQLITE \
  --public-trust APPROVED_PROJECT_PUBLIC_TRUST_JSON
```

The trust file uses the existing actors mapping with role and public_key hex.
Pins must be independently trusted, never supplied by a model as authorization.
Only public pins are read. Do not copy production private keys or databases into
the checkout to make this command pass.

All results have decision=HOLD, deployment_allowed=false, resume_verified=false,
dry_run=true; exit is always 2. Missing arguments produce HOLD. No override or
execute flag exists. The default Stage6 invocation retains its original denial
behavior. The historical reconstruction mode still writes its existing evidence;
the new detection mode prints only typed status/reason codes and creates no
report or reconstruction artifact.

The existing level2d_acceptance_deploy_control.py was inspected but left unchanged:
it installs files and restarts the broker. It was not executed. This gate is an
offline prerequisite, not a systemd interlock or a retrofit of that deployment path.

## Detection and fail-closed behavior

- QUIESCENT_DETECTED: no unresolved selected signed workflow or selected inference
  intent found in this sample.
- COMPLETED_DETECTED: selected durable completion records were detected, with
  structural request/reservation/session/charge digest consistency. This does not
  independently verify a provider executed, a response was consumed, or resume is safe.
- UNKNOWN with HOLD: pending/null responses, unknown outcomes, reserved calls with
  no completion, active signed workflows, inconsistent charges, unknown schema,
  populated supplemental Worker state, missing/unreadable inputs, invalid signatures,
  aliases, sidecars, changes or exceeded bounds.

It preserves every signed workflow and durable request by nonmutation. It never
guesses an outcome, consumes a response, repairs an intent, refunds quota or retries.
A completed record is never promoted into authority. Existing Stage7 proof/execute
and no-duplicate charging checks remain the runtime mechanism, subject to all their
original technical and authority gates.

Reads require distinct, regular, single-link, current-user-owned private files
inside the approved project root; aliases and paths outside it are denied.
Bounds: 16 MiB per database, 1 MiB per SQLite value, 5000 rows per selected table,
64 KiB public trust JSON and a two-second cooperative assessment deadline.
SQLite VM progress interrupts and final elapsed-time checks enforce HOLD on
overrun; this is not an OS hard real-time timeout for filesystem I/O.

SQLite opens mode=ro&immutable=1 with query_only, explicit read transactions and
no waiting for locks. Immutable prevents SQLite from creating shared-memory files
even if a writer changes journal mode during opening. WAL, SHM and rollback-journal
sidecars are rejected before and after sampling; non-delete journal mode is held.
File identity/size/timestamp and data_version changes are checked. Immutable reads
do not provide a consistent view of concurrent writers: checks detect sampled
changes, not every possible transient race. No stable sample is labeled verified
safe resume. Unknown Workers or future schemas require their existing proof paths;
this task does not inspect or alter remote Manager/Worker services.

## Exact limits and next step

Production/current installed processes and state were not inspected or independently
verified. Historical attestation is not fresh state evidence. Current Control state
outside the project root is deliberately rejected, consistent with this task's path
restriction. There is no safe existing read-only atomic API that proves all CEO,
broker, signed review JSON, local intent, remote Worker and process state together.
The signed CEO review JSON files, historical/legacy local execution paths, actual
loaded code, current owner policy/revocation and complete runtime path discovery
are not covered by these three explicitly selected databases.

Minimum next step before verified resume: authorize narrowly scoped read-only
assessment in the existing Control service context against the actual existing
state paths and independently establish complete state coverage, trusted public
pins, exact loaded source identity and process isolation. No new ledger or key
copy is needed or proposed. Until that evidence and the Stage6/review/authority
gates pass, automatic preserve-and-resume remains held. This task implements the
safe detection subset; it does not claim to have solved cross-process resume.

Validation and raw evidence are recorded separately in
docs/acceptance/p1-04-task-a-20261105.md and
tests/acceptance-evidence/p1-04-task-a-20261105/.
ADV-001–ADV-049 and /49 are unchanged. No real CEO, provider call, capital,
payment, launch, deployment, restart or production venture change is authorized.

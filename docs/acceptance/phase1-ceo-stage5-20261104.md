# Phase 1 CEO Stage 5 — synthetic candidate validation

Baseline: main `cbe02523864a8d99463255634d757d9c705eb7ef`.
Continues the interrupted working tree without reverting its changes.
Decision: retain the scoped source improvement and synthetic evidence; **deployment withheld**.
Review status: **NOT_REVIEWED**; GitHub/Claude review is still outstanding.

The source adds a read-only check that a fresh tracked CEO call can see the
existing local authority/session binding before requesting a remote reservation.
It checks private ledger metadata and exact context/policy binding, opens SQLite
in read-only mode, and never creates a session. Execution still validates the
committed reservation and live policy. Recovery retains its existing proof gate.

Changed implementation/test files:
- `agents/ceo/hierarchy_providers.py`: invoke preflight before fresh tracked reservations.
- `agents/ceo/provider_reservation.py`: implement the read-only binding preflight.
- `tests/test_ceo_pending_recovery.py`: establish the fresh synthetic session,
  reject split broker/local authority before remote charging, and verify binding
  checks do not change ledger bytes.
- `tests/test_ceo_candidate_acceptance.py`: synthetic process-exit recovery
  after reservation, response persistence and signed disposition across three
  rounds; cross-bound reservation denial between two created synthetic ventures.
- This report and `tests/acceptance-evidence/ceo-stage5-20261104/`: raw logs,
  exits, commands, process records, import provenance and hashes.

## Validation and decision log

All runs use fake model responses, temporary test signers/ledgers and loopback
mTLS. The resumed runs use `verify_synthetic.py`, which rejects non-loopback
Internet socket connections. TMPDIR stays under the project artifacts directory.
The exact focused, candidate and 37-module regression commands are retained in
`resume-validation.sh`; original asynchronous commands are in `processes.json`.
Raw per-test logs and exit files accompany every completed run.

The interrupted run's saved focused and candidate results each report **17 tests,
OK, exit 0**; its broader regression reports **335 tests, OK, exit 0**.
These were inspected and then rerun, rather than treating a process start as
completion. Final resumed results: focused **17/17, 12.668 seconds, exit 0**; candidate
emulation **17/17, 13.392 seconds, exit 0**; broader regression **335/335,
126.034 seconds, exit 0**. The asynchronous process was observed exited and
its completed logs were read through venture-control. `git diff --check` passed.

Earlier failures remain in `development.log` (second synthetic bootstrap reused
a request ID) and `candidate-development.log` (obsolete CEO-tree broker wrapper
did not support worker_actors). The final test uses a distinct signed bootstrap
request ID; the profile selects the recorded broker-owned wrapper. No production
component was changed to accommodate those fixture failures.
`baseline-reproduction.log` intentionally fails the split-authority regression
against the frozen baseline provider and exits 0 only when the expected pre-fix
failure is reproduced. It is negative-control evidence, not a passing baseline.

The candidate profile loads 51 modules: 47 match recorded installed hashes and
four explicitly use repository CEO candidate bytes. The broker wrapper is from
the broker's recorded hash. Repository fallback payment-adapter module names
are disclosed in `candidate-imports.json`; they are harness imports, with no
real payment invocation. The four candidates are ceo_research_review,
hierarchy_providers, provider_gateway and provider_reservation. Only the latter
two provider files named in the changed-file list change in this commit; the
other candidate dependencies already exist in the baseline.

Classification: **synthetic source validation and recorded installed dependency
emulation**. It is not a fresh installed-tree test, installed broker-profile
acceptance, provider execution verification, or proof of loaded production
bytes. The previous candidate import record is preserved separately.
The fork-based fixture exits only its synthetic child while its threaded test
broker remains in the parent. Python warns about fork in a threaded process;
bounded child waits and exit-code assertions passed, but this is not evidence
of production systemd restart behavior. Injected crash diagnostics and HTTP
denial warnings in successful logs are expected fixture observations.

## Deployment blockers and operator impact

The [Stage 4 assessment](phase1-ceo-stage4-20261104.md) recorded an absent CEO-local
resources.sqlite and a separate broker authority ledger. Installed helpers and
callers also lacked required recovery capabilities. That authority/session
binding has not been independently established for an installed candidate.
Its legacy pending workflow `research-5900c3db9bb5bd74601e3f9d` had a NULL local
response without matching central reservation/execution evidence; a separate
PENDING broker execution did not identify that CEO call. These are historical
recorded observations, not fresh live-state claims.

This task does not inspect, poll, reconcile or replay that production workflow.
Safe isolation from its pending work remains unproved. Full source replacement
or restart could expose that work to inference, so neither is performed.
No installed files, units, authority files or databases are read or changed in
this continuation. Deployed status is **unchanged by this task**; current
production bytecode/state is not freshly attested.

The software improvement prevents a synthetic split-ledger case from charging
remotely before detecting its missing local session. It does not supply the
missing installed binding or resolve a legacy ambiguous outcome. No acceptance
requirement or authority policy changes. P1 stays shadow-only. No ADV rerun;
ADV-001–ADV-049 and the /49 denominator remain unchanged. Synthetic counts are
supplemental and do not grant operational, launch, capital or payment authority.

No real CEO was attached/enabled, no production restart/deployment or external
provider call was initiated, and no capital, payment or venture launch action
was used. Unrelated pre-existing untracked files remain in place and outside
this commit; a globally clean worktree is not claimed.

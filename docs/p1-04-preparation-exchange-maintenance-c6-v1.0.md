# P1-04 legacy preparation exchange maintenance C6 — v1.0

Source-only coverage of the existing LEVEL2C Manager and CEO exchange path on
baseline `b3f6d074765f0901034a5628192a6e0457102b3e`.
Stage6 remains **DENY**, deployment_allowed=false, resume_verified=false.
This closes the scoped source admission gap identified by C5; it does not
establish coordinated production readiness, change the C5 no-go decision, or
authorize installation, service changes, live ledger access, CEO activation,
launch, provider spending or capital actions. ADV-001–ADV-049 and /49 are unchanged.

## Config and execution boundary

The existing `agents.ceo.role_maintenance.admission` and `admitted` helpers
use C1 `MaintenanceAdmission`, without a new control, ledger or service.
The optional config member is exactly:

```json
{"maintenance_admission":{"control":"/canonical/private/control","identity":"1:2:3:4:5:6"}}
```

These numbers are illustrative, never usable provisioning instructions.
The identity pins device/inode pairs for the control, its empty `.active`
sidecar, and their private directory, in that order. Controls are operator
provisioned, private to the effective UID and host; all writers for that UID
must share the same pins. Absence alone retains legacy ungated operation.
Presence requires the existing C3A strict two-field config and canonical
six-number identity validation. Invalid shape, unsafe/missing/replaced files,
symlinks, bad permissions, malformed state and CLOSED deny work. There is no
automatic provisioning, release or fallback.

The CLI reads its operator config once. Each loop enters admission before
state-directory validation, lock-file opening, SQLite, signer/client/provider
construction or binding writes. The first admitted iteration acquires the
existing nonblocking exclusive `exchange.lock` before SQLite opens. This same
lock remains held through every tick and the five-second sleep, excluding
duplicate daemons without holding maintenance admission during sleep.

Each complete tick, including fetch/reservation/provider calls, signed delivery,
receipt checkpoints, rollback and outbox/SQLite close, runs under admission.
SQLite opens and closes within that scope on every iteration, so maintenance
does not report drain while writable WAL teardown remains outstanding. Partial
SQLite initialization closes its connection before propagating failure.
Existing signer, trust, client and model policy pins persist across iterations;
reopening SQLite does not accept a changed standing usage policy.

CLOSED prevents the next tick before constructor IO, even if this daemon still
holds `exchange.lock` while sleeping. Admission denial escapes the transport
error handler. In-flight admitted work finishes its existing commits and close;
drain can then succeed while the legacy lock is still held. Shutdown outside
admission only closes that lock descriptor. The CLI retains its blocked exit.
Provider reservation, charge, ambiguity and exact-receipt replay logic are
unchanged. No new retry behavior was added.

See [C1](p1-04-broker-maintenance-c1-v1.0.md) and
[C3A](p1-04-role-maintenance-c3a-v1.0.md) for the existing control contract.
Low-level exchange/model objects remain internal building blocks; this change
protects the existing config-driven daemon entrypoint and its tick helper.

## Synthetic evidence and review decision

Final result: **131 tests passed in 59.971s**, exit 0; all seven C6 tests passed.
`git diff --check` passed.

The final suite runs the new C6 tests plus existing preparation exchange,
preparation broker/service, LEVEL2C central role, C3A role maintenance, C1 broker
maintenance, C4 coordination, Stage6 gate and production no-go tests.
The exact command, raw per-test output, exit status, source hashes and process
records are preserved in
[the C6 evidence directory](../tests/acceptance-evidence/p1-04-c6-20261106/).

C6 uses real SQLite, Ed25519 signatures, threads and separate Python processes.
Provider execution, reservations and remote transport are synthetic; C6 denies
socket connections. The broader existing suite uses isolated loopback TLS with
external socket connections denied by the existing synthetic runner.
This is independently observed local synthetic execution only. It does not
verify remote Agents installation, service adoption, live reachability,
real inference, cross-host drains or production acceptance.

Coverage includes both roles denied before SQLite, malformed/unsafe controls,
a concurrent drain waiting for final response/receipt commits and SQLite close,
drain during sleep while the legacy lock remains held, postclose absence of
provider calls and writes, separate-process duplicate startup and CLOSED restart
denial, exact receipt replay without another provider call, retained model policy
pins, absent config compatibility and ambiguous inference held on restart.

Initial development failures were fixture errors: test state/key paths first
violated the existing private-artifacts rule, then lacked provisioned private
state directories. A strengthened concurrent test initially replaced the shared
Python sleep function and intercepted the drain wait; the final test replaces
only the exchange module's time reference. Raw development logs are retained.
No production bypass or authority change was made to address these failures.

Review decision: accept only this scoped source coverage once the recorded final
suite and diff checks succeed. Operator impact is limited to opt-in maintenance
denial and per-tick SQLite reopening. Residual risk remains for any unconfigured
writer, different UID/host, unsupported direct low-level caller or unverified
installed copy. Production C5/Stage6 readiness remains DENY.

The unrelated dirty `agents/ceo/deployment_pause.py` remains byte-for-byte at
SHA-256 `4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9`.
No services, live ledgers, real CEO, real provider or capital action were used.

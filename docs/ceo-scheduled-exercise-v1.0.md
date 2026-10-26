# Scheduled advisory exercise — implementation/operator guide v1.0

This implements scheduling of the existing Python exercise, without changing
policy, phase gates, the ADV-001..ADV-049 denominator, or live authority.
The CEO and manager use durable advisory decisions; workers remain bounded local
functions. Model output cannot execute commands, contact customers, launch a
venture, publish, allocate spendable capital, or make payments.

## Execution and continuity

`python3 -m agents.ceo.scheduled_exercise` manages one fixed venture-exercise-v4
workflow in `artifacts/scheduled-ceo/`. There is deliberately no cycle counter,
date-derived identity, automatic reset, retry option, or arbitrary input/stage
flag. Every tick reconstructs and validates the same durable workflow and
synthetic registry lineage. Completed role decisions cause zero provider calls.
The report's current model_call_count is zero on replay, while durable role
responses retain their configured-provider provenance.

Only a pristine dedicated state directory permits inference, up to three
sequential requests in total (evaluation, manager, review; shelving stops early).
An exclusive, fsynced attempt.json is persisted before the first request.
An advisory lock serializes overlapping ticks. Any existing workflow artifact,
attempt marker or previous status disables inference even if a database is
missing, corrupted, incomplete, quarantined, or has a changed configuration.
A crash after dispatch cannot cause an automatic paid retry. Durable replay
remains available when the necessary completed responses exist.

The wrapper catches remote exceptions without printing their text, bodies,
tracebacks or environment values. A failed tick preserves the previous report;
status.json records the latest safe outcome, timestamps and request count.
report.json, workflow.sqlite, workflow.decisions.sqlite and
workflow.decisions.jsonl hold the complete local flow and lineage.
status.json includes the report hash after successful replay. A failure is never
presented as a successful provider run. Exit codes: 0 completed/replayed/busy,
2 provider configuration or replay-only denial, 3 gate denied, 4 state/response
denied. The existing pre-model gate is checked on every tick, including replay.

Do not delete/reset state to make a timer retry. Investigate failures manually.
This implementation does not support new business inputs or later stages.
Those need an explicitly reviewed input/stage design and bounded authorization;
renaming a directory or workflow would merely replay static hypothetical inputs
as a new paid exercise. There is no rolling budget or automatic venture progress.

## VM setup and permissions

The new units are venture-ceo-exercise.service and venture-ceo-exercise.timer
under infrastructure/systemd/. The timer checks hourly with up to 60 seconds
jitter and persistent catch-up. The service is oneshot, has no restart policy,
and times out after 180 seconds. It runs as the existing venture-ceo user.
ProtectSystem=strict and ProtectHome=read-only restrict writes to the dedicated
project-local state directory, matching the exercise's ROOT confinement.
PrivateTmp, PrivateDevices, NoNewPrivileges, an empty capability set and
UMask=0077 are applied. Existing home traversal ACLs must permit that user to
reach the project; no broader home permissions are needed.

systemd loads the existing /etc/venture-ceo.env followed by
/etc/venture-ceo-shadow.env. Both were root-owned mode 0600 on this VM.
No credential appears in ExecStart, command arguments or unit environment
assignments. Their contents were not displayed or copied. The CLI explicitly
uses infrastructure/venture-ceo-kernel-gate.runtime.json, the existing legitimate
untracked gate; never commit or replace it with a gate example.

On this VM, successful root-owned provider-venture-v2 artifacts were copied,
without modifying the originals, to a new mode-0700 venture-ceo-owned directory.
The four copies are mode 0600. Replay verified the existing fingerprint and
response contracts; a fingerprint mismatch would fail without inference.
The units were linked from this approved project into systemd; the old
venture-ceo-shadow service was not changed or enabled. Only the new timer was
enabled after successful service replay.

For an approved installation on a similarly configured VM, prepare the dedicated
state directory with correct service ownership first. Preserve existing state.
Link the two repository units with systemctl link, reload systemd, start the
oneshot and inspect its exit status before enabling the timer. Never start against
an empty state directory unless one bounded paid sequence is explicitly intended.
The installed service has inference-capable credentials but exposes no model
tools or business action adapters. This does not independently establish the
remote provider's internal isolation, billing or execution.

## Operator checks

Run from the approved project root:

```sh
systemctl list-timers venture-ceo-exercise.timer --all --no-pager
systemctl show venture-ceo-exercise.service -p Result -p ExecMainStatus
sudo cat artifacts/scheduled-ceo/status.json
journalctl -u venture-ceo-exercise.service -n 10 --no-pager
```

A successful oneshot normally becomes inactive after completion; Result=success
and ExecMainStatus=0 describe its result. The timer should remain active/waiting.
Stop scheduling with `sudo systemctl disable --now venture-ceo-exercise.timer`.
This preserves durable state; an already-running oneshot finishes separately.

## Evidence limits

Scheduler tests use mocked HTTP and establish no real inference. VM validation
replayed the operator's existing configured-provider run and made zero new HTTP
requests through the scheduler's inference guard. It verifies service permissions,
durable replay and timer readiness, not independently verified remote inference
or a new provider execution. Provenance remains
configured_provider_response_not_independently_verified. The global /49
certification denominator is unchanged; these are supplemental implementation
checks, not fresh certification. All live authority fields remain false.

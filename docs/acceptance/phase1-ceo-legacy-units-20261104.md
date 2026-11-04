# Phase 1 CEO legacy-unit cleanup — 2026-11-04

Baseline: main `81971b4571889ae7fd56b2bc20bacaad95121df2`.
Control host, through venture-control, from the approved project root.
This supplements [topology v1.0](../ceo-service-topology-v1.0.md) and
[Stage 4](phase1-ceo-stage4-20261104.md); no policy, source or authority changed.
Decision: the two legacy disables were safe within the inspected dependencies.
Independent GitHub/Claude review remains **NOT_REVIEWED**.

| Unit | Before | Final |
| --- | --- | --- |
| venture-level2c-ceo.service | enabled, inactive/dead, PID 0 | disabled, inactive/dead, PID 0 |
| venture-ceo-exercise.timer | enabled, active/waiting, hourly | linked (not enabled), stopped, failed/resources |
| venture-ceo-exercise.service | linked, failed, exit 4 | linked, same failed state, exit 4 |
| venture-owner-research-ceo.service | enabled, active/running, PID 288443 | unchanged |
| venture-control-broker-mtls.service | enabled, active/running, PID 288442 | unchanged |

The host inventory now has exactly one enabled CEO service and one running CEO.
Historical level2d and shadow units remain disabled. Linked units remain manually
startable; no mask or unit-template deletion was performed.

## Dependency decision

Fresh systemctl show/cat and recursive reverse-dependency checks found:
level2c WantedBy only multi-user.target (through graphical.target); timer WantedBy
only timers.target; advisory service triggered only by that timer, with no reverse
requirement. RequiredBy, BoundBy, PartOf, ConsistsOf, UpheldBy and failure/success
hooks were empty for the two cleanup targets. The level2c service requires the
broker; the broker does not require level2c. Research directly requires the broker.

Both legacy service entrypoints run as venture-ceo: level2c runs
`python3 -B -m agents.ceo.preparation_exchange --config /usr/local/lib/venture-ceo-level2c/artifacts/level2c-ceo/config.json`
from /usr/local/lib/venture-ceo-level2c; advisory runs
`python3 -m agents.ceo.scheduled_exercise --state-dir artifacts/scheduled-ceo --gate-file infrastructure/venture-ceo-kernel-gate.runtime.json`
from this repository. The timer has OnCalendar=hourly, Persistent=true,
RandomizedDelaySec=60 and targets only the advisory oneshot. The inspected
scheduled_exercise script uses its dedicated advisory/bootstrap/queue state;
it is separate from hierarchy_research_daemon and the signed mTLS broker.

Installed systemd definitions, cron directories/crontabs, /usr/local/bin and
/usr/local/sbin searches found no additional execution dependency. The certificate
renewal script's level2c string is a certificate subject, not a service invocation.

Two existing transient consumers, authenticated-handoff and preparation-broker,
read the retained advisory escalations.sqlite and runner.lock. Their active timers
do not require or start the exercise unit. Their tracked templates contain an
After= ordering reference, which does not activate a prerequisite. Both actual
readers verified the existing inbox before/after and agreed: studio-online is
RECEIVED, without review or decision. They consume the durable snapshot, not a
running advisory service; stopping this timer preserves that input and their
schedules. No consumer tick, Manager/Worker action or replacement review was invoked.
Shared imports of scheduled_exercise.write_json remain available.

## Commands and preservation

Both requested commands exited 0:

```sh
sudo -n systemctl disable venture-level2c-ceo.service
sudo -n systemctl disable --now venture-ceo-exercise.timer
```

Systemd removed level2c's multi-user.target.wants link and the timer's
timers.target.wants link. Disabling the repository-linked timer also automatically
removed its /etc/systemd/system installation link, producing a stopped
failed/resources timer with LoadState=not-found. To retain the installed historical
definition, this additional command exited 0:

```sh
sudo -n systemctl link /home/epsilon/venture-control-workspace/infrastructure/systemd/venture-ceo-exercise.timer
```

Final LoadState=loaded, UnitFileState=linked, no timers.target.wants link.
The timer's resources failure was retained; no reset-failed was issued.
The advisory service's original failed/exit-code state, exit 4 and start time
2026-11-04 21:00:42 UTC remain intact. Its definitions and state files are unchanged.

Research/broker PIDs, users, entrypoints, NRestarts=0 and start timestamps
2026-11-03 01:12:09 UTC match before/after. All **271** captured installed Python,
unit-definition and advisory-state file hashes match exactly. No source,
environment, config, identity, certificate, Manager/Worker or runtime database was
edited. No running research service was stopped or restarted.

## Validation and evidence

[Raw evidence and commands](../../tests/acceptance-evidence/ceo-legacy-units-20261104/before.json),
[intermediate unlink observation](../../tests/acceptance-evidence/ceo-legacy-units-20261104/after.json),
[final observation](../../tests/acceptance-evidence/ceo-legacy-units-20261104/final.json),
[mutation log](../../tests/acceptance-evidence/ceo-legacy-units-20261104/disable.log),
[link restoration log](../../tests/acceptance-evidence/ceo-legacy-units-20261104/retain-timer.log)
and [comparison checks](../../tests/acceptance-evidence/ceo-legacy-units-20261104/validation.log)
retain the exact results. SHA256SUMS covers the evidence. Async process IDs, PIDs,
bridge log paths and exited observations are recorded in processes.json; completed
root-contained output logs were read through the bridge.

Before/after live loopback mTLS GETs under venture-ceo UID 993, actor service-ceo,
succeeded with the installed certificate at https://localhost:8443, proxies
disabled. Both independently verified 134 signed audit records and 13 workflow
snapshots; all six live research snapshots matched that journal.
[Before](../../tests/acceptance-evidence/ceo-legacy-units-20261104/health-before.log)
and [after](../../tests/acceptance-evidence/ceo-legacy-units-20261104/health-after.log)
are identical, including the existing pending CEO intent. Counts remained:
reservations 157, remote reservations 105, remote executions 51,
Worker reservations/executions 52/52, Worker research charges 39.
No POST, provider request, inference, approval or signing operation was issued.

Focused regression command, with a root-contained TMPDIR and disabled bytecode:

```sh
TMPDIR="$PWD/artifacts/ceo-legacy-units-tmp" PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD:$PWD/tests" timeout 120s python3 -B -m unittest \
 tests.test_scheduled_ceo_exercise tests.test_preparation_service \
 tests.test_preparation_broker tests.test_authenticated_handoff \
 tests.test_research_poll_isolation -v
```

[Raw tests](../../tests/acceptance-evidence/ceo-legacy-units-20261104/tests.log):
**52 tests, 5.808 seconds, OK, exit 0**. These use fixtures/mocks and temporary
state. validate_observations.py passed; git diff --check and cached check passed.
No ADV rerun or denominator change: ADV-001–ADV-049 stays /49.

Evidence class: direct host/systemd observation, authenticated read-only exchange,
offline signature verification and synthetic regression. Unknown external schedulers
or future manual starts are outside the inspected dependency universe. Unchanged
ledger observations support no new accounted provider activity during these probes,
but do not independently verify external provider execution or all network traffic.
Stage 4 recovery/provenance limitations and production acceptance gates remain open.

## Rollback reference (not executed)

To restore former boot enablement without starting the inactive level2c service:

```sh
sudo -n systemctl enable venture-level2c-ceo.service
sudo -n systemctl enable --now /home/epsilon/venture-control-workspace/infrastructure/systemd/venture-ceo-exercise.timer
```

The second command restores hourly scheduling; Persistent=true can immediately
trigger a missed advisory tick and its configured provider path. It is a rollback
reference, not part of this no-inference cleanup. Do not reset the advisory failed
state, restore databases, or restart research/broker for this rollback.

Tracked changes are this acceptance document and its new supporting evidence
directory only. Pre-existing untracked runtime/evidence files were preserved;
the entire worktree was already dirty, so global cleanliness is not claimed.
No real CEO was attached/enabled, no capital/payment/launch or external business
action occurred, and no provider inference or approval was initiated by this work.

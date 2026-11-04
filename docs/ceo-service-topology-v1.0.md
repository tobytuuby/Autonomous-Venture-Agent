# Control CEO service topology v1.0 — 2026-11-04

This is a deployment topology record and verification procedure. It grants no
business, provider, capital, launch, or external execution authority and changes
no review gate. Source baseline: `0328cda6252aa924f869c5cb82cfc65c7d00b2d6`.

## Research lifecycle declaration

| Unit | Required state | Entry point |
| --- | --- | --- |
| venture-owner-research-ceo.service | enabled, active/running | agents.ceo.hierarchy_research_daemon |
| venture-level2d-ceo.service | disabled, inactive; retain installed unit | historical agents.ceo.hierarchy_service |

The existing daemon imports `hierarchy_service.run as role_tick`; retain the
shared module. The research unit requires the existing signed mTLS broker,
uses the existing venture-ceo identity, environment file, hierarchy config,
worker limit 4 and durable state directory. Its installed contents exactly match
[infrastructure/systemd/venture-owner-research-ceo.service](../infrastructure/systemd/venture-owner-research-ceo.service).
There is no replacement service or orchestration. Recovery/deployment must
preserve these enablement states rather than enabling every historical CEO unit.
Disabling does not mask the unit: manual starts remain possible and require
separate operational review.

## Dependency decision and production action

On Control, the legacy unit was inactive with MainPID=0. Its only reverse
dependency was multi-user.target (through graphical.target); RequiredBy, BoundBy,
PartOf, ConsistsOf, TriggeredBy and UpheldBy were empty. Searches of installed
systemd service/timer/target/socket/path definitions and standard cron locations,
crontabs, /usr/local/bin and /usr/local/sbin found no references. The research CEO
directly depends on the broker, not the legacy service.

Tracked executable references are historical inspection/deployment tooling:
`level2d_acceptance_observe.py`, `level2d_acceptance_deploy_control.py` and
`level2d_retire_legacy_control.py`. They observe or require legacy inactivity,
and do not enable/start it. Historical fixtures and reports remain unchanged.
This is evidence of no dependency in the inspected workflows, not proof against
unknown external schedulers or future manual actions.

The sole production mutation, exit 0, was:

```sh
sudo -n systemctl disable venture-level2d-ceo.service
```

systemd removed only
`/etc/systemd/system/multi-user.target.wants/venture-level2d-ceo.service`.
The installed unit was retained. No stop, restart, enable, source deployment,
identity change, config replacement, inference request or state edit was issued.

## Verification and repeatable operator checks

Run through the venture-control bridge from the approved project root. The
read-only inspection script records commands and sanitized outputs without
reading secret environment values:

```sh
sudo -n python3 -B tests/acceptance-evidence/ceo-service-consolidation-20261104/inspect.py > artifacts/ceo-topology-verification.json
systemctl is-enabled venture-owner-research-ceo.service
systemctl is-active venture-owner-research-ceo.service venture-control-broker-mtls.service
systemctl is-enabled venture-level2d-ceo.service
systemctl is-active venture-level2d-ceo.service
systemctl list-unit-files '*ceo*' --no-pager
```

Expected: research enabled and active; broker active; legacy disabled and
inactive. The last two legacy queries deliberately return nonzero for those
expected states. Before any future disable, repeat the dependency/scheduler
inspection and confirm inactive legacy plus active research/broker. Never add
`--now` or restart either running service for this topology change. Compare
MainPID, ExecMainStartTimestamp and NRestarts before/after.

The actual inspection commands were
`sudo -n python3 -B artifacts/ceo-consolidation-20261104/inspect.py` before
and after the disable. The tracked inspect.py is an identical copy. All long
commands used bridge process.start; process.list confirmed exit and project
output files were read. Bridge-owned process logs outside the project root
were inaccessible; no completion claim relies on a start response.

Relevant regression command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_hierarchy_service_research tests.test_research_poll_isolation tests.test_research_abc_routing tests.test_research_broker_admission tests.test_research_continuation tests.test_ceo_pending_recovery tests.test_ceo_research_review tests.test_level2c_central_roles -v
```

Result: **94 tests, 21.209 seconds, OK, exit 0**. Tests use fixtures/mocks;
they do not independently validate deployed provider execution. No ADV
certification was rerun or renumbered; the ADV-001–ADV-049 denominator stays /49.
`git diff --check` and `git diff --cached --check` must pass before commit.

## Observed result and limitations

Research CEO PID 288443 and broker PID 288442 stayed active/running, with
unchanged start timestamps (2026-11-03 01:12:09 UTC) and NRestarts=0. The bounded
10-minute priority-error journal samples contained zero lines. These are
service liveness observations, not end-to-end research acceptance or proof of
absence of application-level errors.

All 13 sampled installed Python module hashes, the Python executable hash,
and all inspected unit/drop-in contents were identical before/after.
Python is /usr/bin/python3.14, version 3.14.4; SHA-256
`52e0a13e60a981d8c4b6478be2ba5176f69da07948a056bf49cf6f077e30cb41`.
The evidence lists each module's installed and HEAD SHA-256. Seven sampled
copies differ from HEAD: CEO hierarchy_service, hierarchy_providers and
provider_gateway; broker hierarchy_service, hierarchy_providers,
provider_gateway and hierarchy_runner (seven copies total).
These are pre-existing on-disk deployment differences and were not reconciled.
On-disk hashes do not prove which bytes a running Python process has loaded.

**Host-wide one-enabled-CEO acceptance remains blocked:** the separately
installed venture-level2c-ceo.service is still enabled/inactive, and
venture-ceo-exercise.timer is enabled/active (its advisory oneshot was failed).
Their disposition needs separately scoped review; this task allowed only the
confirmed safe level2d disable. The two research hierarchy entry points now
have exactly one enabled CEO, but the host-wide inventory is not one CEO.
Existing GitHub/Claude review and live research acceptance gates remain open;
this record is not independent review approval.

Evidence is direct Control read-only observation plus one confirmed systemd
disable, and local synthetic regression execution. No CEO was attached,
enabled or invoked by this work; the pre-existing research CEO was left
running. No real capital/payment/launch action was used. Signed broker, mTLS,
quota controls, cryptographic identities and production state were untouched
by the commands here; ongoing services may naturally advance their own state.
Unrelated untracked files were neither edited nor staged.

## Evidence files

- [inspection and disable evidence](../tests/acceptance-evidence/ceo-service-consolidation-20261104/observation.json)
- [read-only inspection script](../tests/acceptance-evidence/ceo-service-consolidation-20261104/inspect.py)
- [raw per-test output](../tests/acceptance-evidence/ceo-service-consolidation-20261104/tests.log)

The observation contains the exact production mutation argv, exit result,
before/after service properties, installed config, commands, module hashes,
and comparison checks. The commit containing this document is the topology
record; no production source code or historical unit template was changed.

# Scheduled CEO exercise implementation evidence — 2026-10-26

## Change and decision

Accept the bounded scheduler for local advisory replay only. The new hourly timer
and oneshot were installed on venture-control, without changing the old readiness
service or any authority gate. This is an implementation review decision, not
independent certification, a phase acceptance or authorization for another paid
cycle. The existing operator-run provider artifacts remain the provenance source.

Changed implementation: agents/ceo/scheduled_exercise.py,
infrastructure/systemd/venture-ceo-exercise.service and
infrastructure/systemd/venture-ceo-exercise.timer. Focused tests are in
tests/test_scheduled_ceo_exercise.py. Operator instructions are in
docs/ceo-scheduled-exercise-v1.0.md; docs/PROJECT_STATUS.md links this milestone.
Raw supplemental evidence is in
tests/certification/scheduled-ceo-20261026/.

The scheduler uses the existing durable CEOAgent, required-provider adapter,
synthetic venture store and strict response validators. It grants at most one
three-request advisory sequence to a pristine directory; imported/completed or
uncertain state permits replay only. A fsynced exclusive attempt marker precedes
dispatch, and an advisory lock prevents concurrent ticks. There is no automatic
new workflow, paid retry, static exercise reset or date-based venture identity.

## Validation and execution evidence

- Initial HEAD: dbf813cebf42410c3f960dbefd8c2fbb760cc5fb on main.
  Initial status: only infrastructure/venture-ceo-kernel-gate.runtime.json untracked.
- python3 -m unittest tests.test_scheduled_ceo_exercise -v: 10 tests, OK.
  Mocked HTTP only. Covers replay, failure retry denial, crash marker,
  preexisting database, shelving, changed configuration, gate denial, overlap,
  alias rejection, status/artifact reporting and false live authority fields.
- python3 -m unittest discover -s tests -v: 677 tests, OK, exit 0.
  The complete per-test output is preserved in regression.log.
- python3 -m py_compile agents/ceo/scheduled_exercise.py
  tests/test_scheduled_ceo_exercise.py: exit 0.
- systemd-analyze verify on both repository units: exit 0.
  Only unrelated host xfs_scrub CPUAccounting deprecation warnings occurred;
  preserved in units-verify.log.
- git diff --check: exit 0 before commit.
- Two real systemd starts of the new oneshot: Result=success, ExecMainStatus=0,
  status=REPLAYED, inference_requests_this_tick=0, external_action_count=0.
  Both replays produced the same report file SHA-256:
  4c2bbbd8a47131e9fa184fb43a86594ace5ac04fc4eb1d534e3ec456b1810ba7.
  These are real local service executions, not new provider inference.
- Timer enabled and active/waiting. At validation, next trigger:
  2026-10-26 09:00:37 UTC. Hourly periodic trigger itself was not awaited;
  readiness and manual oneshot execution were independently observed.
- SHA-256 comparison confirmed all four original provider-venture-v2 artifacts
  and the legitimate untracked gate unchanged. Originals-check.log records each
  check; originals.sha256 records source hashes.
- Runtime user=venture-ceo, ProtectSystem=strict, ProtectHome=read-only,
  NoNewPrivileges=yes; the only project write exception is
  artifacts/scheduled-ceo. Both existing credential EnvironmentFiles remained
  root-owned mode 0600. Credential contents were not displayed or copied.
  The existing home ACL already granted venture-ceo traversal; no host home
  permission changes were required. Runtime directory is mode 0700 and files
  mode 0600. sudo -n was available, so no root-permission blocker remained.

The completed operator run's four artifacts were copied to service-owned files
in artifacts/scheduled-ceo before installation. Original files were never opened
for writing. Replay successfully validated the same durable configuration,
response contracts and synthetic registry provenance. No extra paid sequence
was needed or triggered. The new units are linked from the repository into
systemd, and the timer is enabled; scheduler code remains the reviewed project
code rather than a separate installation copy.

## Non-technical assessment and residual limits

Operator impact: hourly status and durable replay now run without manual commands.
The latest timestamps, status, report hash and inference request count are in
artifacts/scheduled-ceo/status.json and the journal. Full role/worker artifacts
remain in that directory. Failure preserves the previous report and records a
denial; it cannot turn uncertainty into permission to spend again.

Authority: no production CEO was attached, and no capital, payment, publication,
customer contact, venture launch, deployment or other live venture action was
used. The provider-backed CEO is advisory shadow reasoning; workers execute only
the existing local synthetic functions. The legitimate /49 gate is still checked
on every tick, without fabrication or bypass. No ADV scenario or denominator was
changed and no fresh ADV certification is claimed.

Provenance: tests are synthetic/mocked evidence. VM execution verifies the actual
local service, its permission boundary and replay of externally configured
provider responses. It does not independently establish remote inference,
billing, model identity or provider-side tool isolation. Responses retain
configured_provider_response_not_independently_verified, with
ai_inference_independently_verified=false.

Residual risk: authorized administrators can alter state, credentials, code or
units; this scheduler is not a defense against the host administrator. A crash
can leave work incomplete, intentionally requiring investigation rather than
automatic paid retry. A pristine state directory would allow one bounded sequence;
operators must preserve the installed durable directory. New inputs/stages and
new paid cycles are not supported by this deliverable. There is no automatic
venture advancement or live authority expansion.

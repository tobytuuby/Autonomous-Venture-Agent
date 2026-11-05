# P1-04 C2A local writer exclusion preflight — v1.0

Decision: **source-only C2A; Stage6 DENY; production HOLD**. This adds an
observation mode to the existing deployment gate. It introduces no service,
orchestration layer, ledger, authority, Manager/Worker source change or production
configuration. ADV-001–ADV-049 and /49 remain unchanged.

Starting main HEAD: 6ce257e3ac9530561a6abdbbbd13c9d98130f56f.
The index was empty. The global worktree includes unrelated tracked and untracked
work. The unrelated agents/ceo/deployment_pause.py is preserved and unstaged at
SHA256 4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9.
Tests run in that worktree, so this is not clean-HEAD-only validation.

The [live boundary audit](acceptance/p1-04-live-boundary-audit-20261105.md),
[C1 contract](p1-04-broker-maintenance-c1-v1.0.md) and
[maintenance source disposition](acceptance/p1-04-maintenance-source-no-go-20261105.md)
remain binding context. Existing historical installed-unit evidence at
tests/acceptance-evidence/ceo-legacy-units-20261104/final.json
(SHA256 9941cfed8645f5004e4265f80a7f53f40eee2029265a5ec30f196fdb43c98045)
records active venture-owner-research-ceo.service and
venture-control-broker-mtls.service, plus inactive/failed legacy services and a
failed exercise timer. It contains no ControlGroup property. These are prior,
non-atomic observations, not current exclusion or installed/loaded adoption.
No live service inventory was executed for C2A validation.

## Existing component behavior

Use scripts/ceo_stage6_deployment_gate.py with --preflight-writers.
Without configuration it denies without querying services. With --writer-config
it reads systemd service/timer inventories, exact unit properties, queued jobs,
and /proc PID/executable/cgroup metadata. It never invokes a service mutation.
There are no environment, process argument, ledger or pending-operation reads.
Output contains unit identity/state summaries and process metadata, not raw
ExecStart values. Exact ExecStart is compared internally with the supplied pin.

The project-contained JSON config has a nonempty units object keyed by exact
.service/.timer Id. Each entry pins string Id, User, FragmentPath, ExecStart and
ControlGroup, plus role manager, worker, ceo, api, timer, broker or other.
Every observed unit must have a pin, and every pin must be observed. Aliases,
missing/duplicate/unknown units, incomplete reads, jobs, uncertain states and
identity mismatches deny local readiness. Uninstantiated templates are skipped;
installed instances and loaded/transient units are enumerated independently.

A non-broker unit must be inactive/dead, MainPID zero and ControlGroup empty.
Active Manager, Worker, CEO, API and timer tasks, including backup timers, deny.
Every process is conservatively treated as a potential writer. There is no
generic non-writer allowlist: even OS/observer processes, broker children and
unclassified processes deny local readiness. This deliberately over-denies
ordinary hosts; it does not claim practical complete host quiescence.

An optional broker object contains unit, path, identity and exe. Its unit must
be the sole broker pin. A broker pin without C1 configuration denies. C1 path
must resolve inside the approved project root; production paths outside that
root are unavailable in this task. The observer reuses MaintenanceAdmission's
private ownership/mode/link/inode validation and nonblocking mutex/activity
checks. It requires exact CLOSED bytes and exclusive zero-activity observation.
C1 opens validated existing files with its existing O_RDWR flags; the probe
never writes, creates, truncates, closes admission, drains or releases admission.
Transient flock probes are released before return. Missing files, wrong UID,
bad pins, contention, OPEN or unsafe artifacts deny without recovery.
An active broker is accepted locally only with the observed MainPID matching
the one permitted process, the exact configured executable and exact pinned
cgroup in every cgroup record. Extra processes still deny.

The probe cannot verify that a running broker actually adopted these C1 files
or that a pinned executable has loaded the candidate bytes. Those remain
separate proof requirements. A successful probe is a momentary local sample,
not a maintained maintenance boundary; writers can change after observation.

For deterministic tests, --writer-snapshot accepts project-contained JSON with
units (systemctl-show-style property objects), processes (pid/exe/cgroups),
jobs and errors arrays. It skips systemd and /proc access and always labels
evidence SYNTHETIC_SNAPSHOT. It still probes real temporary synthetic C1 files;
a supplied ready boolean cannot substitute for C1 validation. Config/snapshot
inputs are bounded to 4 MiB each. No operational config is supplied by C2A.

All results retain decision=DENY, deployment_allowed=false,
resume_verified=false, cross_vm_coverage_verified=false,
loaded_bytes_verified=false and atomic_snapshot=false. CLI exit is always 2.
local_exclusion_ready can be true for clean synthetic local evidence; it never
satisfies the separate joined proof. Other VMs, hidden PID namespaces, remote
writers, loaded Python bytes, signed lineage, PENDING disposition and mandatory
GitHub/Claude review remain unverified. There is no retry or deployment path.

## Validation and review decision

Selected files are scripts/ceo_stage6_deployment_gate.py,
tests/test_stage6_writer_exclusion.py and this document. Raw per-test execution
logs and exit records remain local under
tests/acceptance-evidence/p1-04-c2a-20261105/. They are not selected for commit.

The focused tests cover active roles, backup timer, unknown units/processes,
exact identities, MainPID/cgroup mismatch, incomplete observations, jobs,
unconfigured gate/broker, missing C1 file, OPEN, outstanding activity,
unchanged C1 bytes/inodes, CLI no writes, deterministic systemd mocks and clean
synthetic local evidence that still denies deployment. Existing C1 regression
tests also cover admission, drain, TLS, durable replay and process death.
Synthetic fixtures provide no independent live provider or production evidence.

Final validation results and artifact hash follow after completed execution.
No real CEO was attached/enabled, production service stopped/restarted/enabled,
deployment performed, live state written, ambiguous PENDING retried, or real
capital/payment/launch action used. Production and P1-04 closure remain HOLD.

Final command (120-second bound, project-contained TMPDIR,
PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=.:integrations/payment_adapter):

```text
python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_stage6_writer_exclusion tests.test_ceo_stage6_gate tests.test_p1_04_production_no_go tests.test_broker_maintenance_c1
```

Result: **31 tests in 8.666s, OK, exit 0**, no failures/errors. The existing
runner forbids non-loopback socket connections. Bridge process
proc_mw3whfow_8u76it, PID 579806, was polled to exited and the completed
project-local final.log read through venture-control, truncated=false.
final.log SHA256: 35e7f59c014ca1fff26928e2f315b48c87c150776c83dcc0904dc3ea11580d24.
The initial focused run also passed 31 tests; the final run validates the
completed report fields and CLI assertions.

Python AST parsing, document-reference checks and git diff --check passed
(exit 0) before the three-file commit. Scope review keeps all unrelated work unstaged.
Evidence classification is local synthetic execution plus historical metadata
inspection only. No current writer exclusion or independent provider execution
is established. Mandatory GitHub/Claude review and joined operational acceptance
remain outstanding.

# P1-04 C2B protected-state observation correction — v1.0

Source-only correction to C2A at main b636ecd74bff7d9422d822a048226b625fc3afeb.
Historical C2A and Stage6 evidence remain unchanged. Stage6 decision is DENY,
deployment_allowed=false, resume_verified=false; CLI still exits 2.
No service, ledger, authority or architecture is introduced.

The existing --preflight-writers implementation now supports protected_roots:
a nonempty array of exact canonical directory path, uid, dev and ino pins.
Each directory must already exist with mode 0700. Accepted locations are the
project and the exact installed CEO/broker artifacts trees in TREES. Arbitrary
external roots and symlink paths deny. Live mode requires these pins; legacy
synthetic snapshots retain C2A's conservative semantics without them.

Each selected unit retains C2A's exact Id, User, FragmentPath, ExecStart,
ControlGroup and role pins, and adds a positive numeric uid and absolute
writer_cgroup. writer_cgroup records the writer identity even when systemd's
current inactive ControlGroup is empty. Selected services must be inactive/dead
with MainPID zero and no residual cgroup, except the sole C1-closed broker.
Selected role/API/backup timers still deny while active or uncertain.
Only selected unit properties are queried; missing selected identities deny.
Queued jobs for selected units and jobs with unknown unit identities deny.

All visible PIDs are inspected for UID tuples (including filesystem UID),
effective capabilities, executable, cgroups, start time and open writable FD
targets. An unrelated process with complete metadata, a different unprivileged
UID/cgroup and no writable FD under protected state can pass. A process sharing
a protected owner/service UID, a selected cgroup or descendant, or a writable
FD under protected state (including deleted files) is a relevant writer and
denies unless it is the exact permitted broker MainPID/executable/cgroup/UID.
Root and capabilities permitting DAC, ownership, identity, tracing or host
control remain conservative writer classifications: these can defeat private
directory permissions. No blanket exemption for privileged OS services exists.
Unknown PID identities/cgroups, duplicate PIDs and unreadable /proc deny.

The observer reads selected systemd metadata, jobs and /proc twice; any sample
difference denies. PID start identity is also checked within each process read.
Protected-root inode/owner/mode and directory change timestamps are rechecked.
This catches observed changes, not every possible transient write between
samples. It remains a non-atomic one-host observation, never an exclusion lease.
No environment, process arguments, secret values or ledger contents are read.

Live C1 access accepts only the exact canonical configured existing path below
/usr/local/lib/venture-control-broker-level2c/artifacts/, with the six-number C1
device/inode identity and explicit uid. Every ancestor is walked without
symlinks; owner checks, private directory 0700, regular single-link files 0600,
and device/inode pins are enforced. The probe reuses existing C1 locking and
state checks through a read-only opener, including pathname revalidation.
Every open uses O_RDONLY; nothing creates, truncates or writes state. CLOSED
and uncontended exclusive control/activity locks are required and rechecked
after sampling. Locks end on return. Synthetic C1 fixtures remain project-local.
The live-branch test redirects only the allowed prefix into a temporary fixture;
it does not access production C1 files or establish production adoption.

Validation uses tests/test_stage6_protected_writers.py plus unchanged C2A,
historical Stage6, production-no-go and C1 tests through the existing
verify_synthetic.py runner, which forbids non-loopback connections.
Tests exercise realistic unrelated user-service PIDs, rogue UID/cgroup/FDs,
incomplete metadata, relevant jobs, sampling changes, selected systemd reads,
writable versus read-only FD flags, read-only C1 opens, ownership/mode/inode
and symlink denials. Temporary data and raw per-test logs/exit records are
project-contained under tests/acceptance-evidence/p1-04-c2b-20261105/.

Review disposition: local synthetic execution only. No live writer exclusion,
loaded bytes, provider execution, remote namespace coverage, broker adoption,
joined operational proof or mandatory GitHub/Claude review is attested.
The operator must independently pin complete relevant roots and service sets;
omissions cannot be discovered from this config alone. Privileged writers and
inaccessible /proc can still require HOLD. ADV-001–ADV-049 and /49 are unchanged.

Only scripts/ceo_stage6_deployment_gate.py,
tests/test_stage6_protected_writers.py and this new document are selected.
Existing dirty/untracked work is preserved, including deployment_pause.py at
SHA256 4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9.
No real CEO was attached, enabled or used; no production restart/stop/deploy,
ledger mutation, payment, capital or venture-launch action occurred.

Final validation: **41 tests in 8.801s, OK, exit 0**, no failures/errors.
Command (120-second bound; project-contained TMPDIR; PYTHONDONTWRITEBYTECODE=1;
PYTHONPATH=.:integrations/payment_adapter):

```text
python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_stage6_protected_writers tests.test_stage6_writer_exclusion tests.test_ceo_stage6_gate tests.test_p1_04_production_no_go tests.test_broker_maintenance_c1
```

Bridge process proc_mw3wsx7t_so0px5 (PID 633197) was polled to exited and its
completed project-local complete.log read through venture-control. Raw log
SHA256: ca1ae4742f0f5dabdcffb768806bebc67182370ea0999b9b65b440c121e56cd5.
AST parsing, preserved unrelated-file hash and git diff --check also passed.
Tests used the existing dirty worktree; this is not clean-HEAD-only validation.

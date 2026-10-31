# Remediation 1 — blocked before operational acceptance

Attempt: `level2d-multiworker-remediation-1`, 2026-10-31 UTC.
Inspected base HEAD: `db478712606e3898e2c6ee8faf409e524c9f378a`.

**Decision: BLOCKED; real-provider journey NOT_RUN.** Agents `sudo -n true`
returned exit 1 because `no new privileges` is set. The protected Manager
configuration also returned PermissionError. The owner's explicit stop condition
applies: the operator script was staged, and no privileged Agents operation was
attempted afterward. No privilege bypass was attempted.

Live observation confirms the Control broker is active with worker-a/b/c in its
registry and six actors in signing trust, including legacy service-worker.
Agents Manager and all three distinct worker services are active; journal entries
show WAITING. This proves service/configuration observations, not successful
provider access or an authenticated three-worker journey. Manager's WAITING
entry reports OWNER_REVIEW for an unspecified workflow; its protected workflow
binding remains unread.

Additional blockers prevent safe kickoff:

- Broker Worker inference policy still authorizes only service-worker.
- Installed gateway limits the technical fixture to five effort units.
  Requested scope is 12 units, within 10–15, with at most four per assignment;
  this scope is a plan and has not been signed or installed.
- CEO config/session still targets level2d-acceptance-5. Installed reasoning
  service and CEO policy pin CEO/Manager to gpt-6-sol; Workers are pinned to
  gpt-6-luna. No all-role luna execution is claimed.
- The inspected installed CEO kickoff script path is absent. The checkout's safe
  fixture exists, but no other installed kickoff location was verified.
- Shared ledger contains 17 historical Worker reservations. Remaining allowance
  for venture-verification was not established. Nothing was reset or refunded.

The requested workflow has zero journal rows and zero Worker reservations in the
observed read-only database snapshot. No signatures, provider receipts, usage
totals, audit chain, live C denial, synthesis or OWNER_REVIEW result were produced
for this attempt. No restart was performed.

The intended three tasks remain internal tenant-isolation cases (A), independent
recovery/rollback cases (B), and consolidation (C), with C dependent on A+B.
The requested mapping, 12-unit scope, shared four-call ceiling and remaining gates
are recorded in [remediation-1-execution.json](remediation-1-execution.json).
These are planned requirements, not successful acceptance evidence.

Six new files are additive to the earlier historical blocked package:

- [remediation-1-observation.json](remediation-1-observation.json): current Control
  config, source hashes, ledger counts and raw Agents service/sudo observations.
- [remediation-1-execution.json](remediation-1-execution.json): bounded stages,
  exact validation commands/process metadata, requested fixture and limitations.
- [remediation-1-tests.log](remediation-1-tests.log): all 26 local test results.
- [remediation-1-operator.py](remediation-1-operator.py): minimal operator script.
- This README.
- `remediation-1-SHA256SUMS`: hashes of the other five files.

The identical operator script was staged at
`/home/epsilon/venture-agents-workspace/artifacts/three-workers/remediation-1-operator.py`.
It was **not executed**. From an authorized operator shell in that approved
project, review before running:

```sh
sudo -n python3 artifacts/three-workers/remediation-1-operator.py
```

The script validates protected Worker config bindings and renders a root-only
Manager candidate with the requested workflow and decomposition_workers. It
reads no private key bytes, copies no credentials, installs no configuration,
signs no command, calls no provider and restarts no service. It preserves existing
config and refuses an existing output directory. Its output is a candidate,
not completion of the remaining Control policy/configuration gates.

Validation completed: **26 tests passed, exit 0, 3.094 seconds**, covering signed
decomposition, early C rejection before reservation, dependency release, durable
restart/replay and shared quota exhaustion. These are local fixtures and fake
inference, not live-provider evidence or independent reviewer acceptance.
ADV-001–ADV-049 and /49 remain unchanged.

Integrity and syntax checks are performed before commit. Verify package hashes
from the project root with:

```sh
(cd tests/acceptance-evidence/level2d-multiworker-20261031 && sha256sum -c remediation-1-SHA256SUMS)
```

Source hashes describe on-disk files, not measured loaded Python bytecode.
Artifact hashes provide integrity, not signed provenance or independent
attestation. Existing dirty tracked files were fingerprinted and preserved;
historical evidence, installed configs, signed identities, central ledger and
singleworker were not modified. No production CEO, real capital, payment,
venture launch or external business operation was used. No live acceptance PASS
is claimed.

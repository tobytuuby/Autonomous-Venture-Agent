# P1-04 Live Boundary Audit — 2026-11-05

Decision: **HOLD / production NO-GO; P1-04 cannot close.** This bounded report
adds no architecture, approval gate, authority, or ADV scenario. ADV-001–ADV-049
and denominator /49 remain unchanged. It supplements the
[Stage B report](p1-04-stage-b-20261105.md) and
[safety resolution](p1-04-safety-resolution-20261105.md).

## Scope and provenance

Starting main HEAD: 05fe644145bd678d41b08679cc4eb1ae583bf852.
Read existing project-local evidence from the timed-out Stage C inventory task
codex_mw34yk9z_0dbz60; no inventory, privileged command, or production retry was
executed for this report. A timeout is not successful task completion.
The saved observations are historical, non-atomic metadata, not current live
attestation or independently verified provider execution.

Only this report and tests/test_p1_04_production_no_go.py are selected for commit.
Raw inventories, process/environment data, configuration, workflow/ledger content,
and inventory scripts remain excluded. Existing untracked files are preserved.
The unrelated agents/ceo/deployment_pause.py remains unchanged and unstaged,
SHA256 4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9.
Tests using that helper include these preexisting dirty bytes; this is not a
clean-HEAD-only execution.

## Observed boundary and exact blockers

| Existing evidence | Finding and implication |
| --- | --- |
| Control final observer | READ_ONLY_NONATOMIC_METADATA; HOLD; deployment_allowed=false. Sampled broker remote_executions: COMPLETE=50, PENDING=1, null response=1; worker_executions: COMPLETE=51, PENDING=1, null response=1. Counts neither identify exact intents nor establish safe replay. |
| CEO review/intent metadata | Pending packets and provider-intent metadata are present, including pending packets with response metadata. signature_verified=false: signed provenance and exact response/intent binding remain unverified. A response-present flag cannot authorize continuation. |
| Control coverage | Some stores are UNKNOWN with SIZE_OR_SIDECAR; some roots absent or inaccessible. A successful scan or stable sample cannot prove all writers or in-flight operations excluded. |
| Agents final observer | Only two processes observed; 145 process-scan errors and incomplete tree discovery. Privileged writers, state roots and queues are not fully accounted for. |
| Agents sudo denial | Exit 1: sudo refused because “no new privileges” prevents elevation. This is an observation-access blocker, not proof of absent writers. |
| Service mount disk manifests | Broker: 123 files, 14 checkout hash differences; CEO: 126 files, 16 differences; both include FileNotFoundError. Stable process-start identity does not attest imported Python bytes. These are disk observations, not a complete deployed-source match. |
| Inventory decision flags | loaded_python_bytes_verified=false, all_writers_excluded=false, signed_state_verified=false, atomic_snapshot=false. No production deployment or resume proof exists. |

Remaining closure requirements are the existing requirements: complete Control
and Agents writer/state coverage; installed and loaded code/authority identity;
same-inode CEO lock adoption plus Manager/Worker admission and shared-broker
in-flight drain; exact intent classification against signed lineage, original
session/request/attempt, reservation, charges, current authority and revocation;
preservation across the actual maintenance/rollback boundary; independently
verified mandatory GitHub/Claude review and operational acceptance.
None is supplied by these metadata samples. Missing/legacy/conflicting evidence
and PENDING outcomes remain held; no retry, new reservation, quota reset, ledger
edit, or inference of successful provider execution is justified.

## Owner action for Agents LocalBridge host sudo

The Owner/host administrator must inspect the actual Agents LocalBridge service
or container launch policy and sudo policy from an authorized host session.
The recorded no-new-privileges restriction must be resolved there for a narrowly
scoped read-only observer, or the administrator must run that observer from an
already authorized host context and provide sanitized coverage evidence.
Changing sudoers alone cannot override an inherited no-new-privileges bit.
Do not grant broad passwordless sudo or weaken production services to obtain
this report. Preserve the original failed observation as incomplete evidence.

That host action is outside this root-only report task. It permits observation
only; it does not permit CEO activation, production maintenance, ledger writes,
or retries. Even complete observation cannot substitute for the separately
authorized existing maintenance and acceptance boundary. Proving drain,
installed/loaded candidate adoption and durable resume across that boundary
would cross the production safety gate prohibited in this task; therefore
P1-04 remains open.

## Source controls and validation

Saved evidence identifiers below are SHA256 of local files in
tests/acceptance-evidence/p1-04-live-inventory-20261105/; raw files are not committed.
Hashes identify the reviewed artifacts, not their truth or signature validity.

| Artifact | SHA256 |
| --- | --- |
| control-final-observer.json | 65a7cd4d8177c1823352c98023d4d3801fc55463fc7c8aa251d74b7932267a97 |
| agents-final.json | 5d73075a8ed0ba55850356b6f3203cdb27be7aaf9c7bf696a6ac4ead7c7e4924 |
| agents-sudo-denial.json | 636c1086e9d7ad805dbbcfcb965014bf8eddb0dca4e58cd7e02d7d09fff0ff98 |
| service-source-final.json | 5dc594ef1c9ef61b06ff20ec9cb6f1aae9def48c5126d5c6726da39204ff8274 |
| final-tests.log | 59e8b44792389e1c784512af6569f23181ca2f8c01df56e226108a4d74e14f7d |
| source.sha256 | 08254c135295a9bedfa1a05a24ecd0a1819b1c7b92e886d89d0787c64326677b |

Prior saved final-tests.log records 26 tests in 25.552s, OK, exit 0.
This is inspected prior execution evidence, not a fresh rerun claim.

The new offline test invokes the existing --preflight-resume and
--assess-boundary CLI modes with missing temporary project-local inputs.
It requires exit 2, DENY/HOLD, deployment_allowed=false, resume_verified=false,
no created files, and forbids external subprocess commands. It performs no
live state access or inventory. Synthetic tests cannot establish live reachability.

Fresh validation results follow. Raw synthetic
output stays local in tests/acceptance-evidence/p1-04-final-bounded-20261105/.
No real CEO was attached or enabled, production service restarted, live ledger
written, operation retried, or capital/payment/launch action performed.

Fresh command (PYTHONDONTWRITEBYTECODE=1, timeout 180):

```text
python3 -B -m unittest -v tests.test_p1_04_live_inventory tests.test_stage_c_maintenance tests.test_deployment_resume.DeploymentPauseTests tests.test_deployment_broker_restart tests.test_ceo_stage6_gate tests.test_p1_04_production_no_go
```

Result: 27 tests in 5.657s, OK, exit 0; no failures/errors.
Bridge process proc_mw3t8oa6_zg7tax was polled to exited; the complete project-local
focused.log was read through venture-control.
focused.log SHA256: 39719e1431aa855616dfb9ab87c6bce21a1c72d8dc439e19e1f395100e1234a0.
New test SHA256: 6678ffa7e655069c5a37a34bb25ce9f42d9427e463f5a8ff4a29562f9add4564.
git diff --check exited 0. Existing inventory source.sha256 entries were checked
against current local bytes. Report references resolve locally. These results
verify synthetic behavior only; no independent live provider or production
acceptance is claimed. The index is restricted to the report and new test;
the global worktree intentionally retains unrelated work.

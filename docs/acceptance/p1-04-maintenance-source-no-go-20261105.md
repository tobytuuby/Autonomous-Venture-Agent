# P1-04 maintenance source disposition — 2026-11-05

Decision: **NO-GO for shipping a complete maintenance mechanism; production HOLD.**
This is the requested fallback disposition, not live acceptance or a claim that
broker admission/drain was implemented. No runtime source changes are selected.
The bounded next implementation below uses existing components and state formats;
it creates no orchestration service, execution ledger, policy or authority.
ADV-001–ADV-049 and /49 are unchanged.

## Provenance and preserved work

Starting main HEAD: da4f8a0a7a238265f253b7733df4679b5a62297c.
Verified with git rev-parse HEAD, git status --short and branch inspection.
The index was empty. The global worktree contains unrelated untracked work.

agents/ceo/deployment_pause.py is a preexisting tracked modification, SHA256
4aa2fa78cba1d59df098d3127d7ef2c4bc0f2bf713855246bebd2823447128e9.
Its committed predecessor is ef154cdf1f5ea0abedf63520fa8f934f37fa2511.
The dirty delta adds lease entry/exit inode checks and two preflight blockers.
The [prior safety report](p1-04-safety-resolution-20261105.md) records its
association with Stage C codex_mw34ejik_hk7sz4, subsequently failed; the
[live audit](p1-04-live-boundary-audit-20261105.md) records its continued preservation.
This establishes recorded provenance, not independently verified authorship.
The bytes were inspected, never changed or staged. Tests include these dirty
bytes and must not be described as clean-HEAD-only validation.

Control task metadata identifies codex_mw3vb90a_dtjff8 as this runner.
Agents task codex_mw3vaz63_8yon5l was running a separately Owner-authorized,
read-only writer/state inventory when inspected. It was not cancelled, delegated
to, or treated as completed. No Agents files or live state were read by this task.
Its result cannot prove exclusion or installed/loaded adoption by itself.

## Exact existing-system gap

| Inspected source | Coverage needed |
| --- | --- |
| kernel/broker/mtls_server.py:main | ThreadingHTTPServer has no maintenance admission or drain. Startup constructs certificate mailboxes before serving; constructor writes must also be accounted for on restart. |
| kernel/broker/isolated_mtls.py:handler_for | A common boundary must cover every callback and inherited capability evaluation, including GET callbacks unless separately proven side-effect free. Cover CEO proof/execute, Worker reserve/execute, Manager/CEO reservation/execute, hierarchy bootstrap/commands/artifacts, assignment submit/ACK and certificate CSR paths. A gate on inference endpoints alone misses writers. |
| agents/ceo/hierarchy_research_daemon.py:poll | Existing cycle exclusion is CEO-only. Manager/Worker still poll, create session directories through allowed_config and call role_tick. |
| agents/ceo/hierarchy_service.py:run | Direct role entrypoint constructs HierarchyProvider before its loop, then ticks research/workflow callbacks. A loop-only guard misses initialization writes. |
| agents/ceo/hierarchy_providers.py:HierarchyProvider | Constructor creates directories/table; call commits local request/attempt intent before remote reservation or inference. Rejecting remote HTTP afterward cannot exclude these local writes. |
| agents/ceo/ceo_research_review.py | Local pending review JSON, immutable provider-intent JSON and signed review writes belong inside CEO exclusion through final disposition. |
| agents/ceo/hierarchy_worker_service.py:load_config | Exact Worker config fields reject a new pause key. Generic Manager/Worker adoption cannot be assumed from a CEO config change. |
| scripts/level2d_acceptance_deploy_control.py:main | Preliminary CEO-inactive check does not drain shared broker traffic. Existing file-copy/restart and code-restoration branches have no common admission lease; this script is not an acceptable maintenance path while Stage6 DENY. |
| infrastructure/ceo-installed-compatibility.json | Current candidate overlays contain no maintenance primitive or Manager/Worker deployment coverage. Source availability does not establish package/adoption compatibility. |

The CEO helper cannot simply be reused unchanged: cycle rejects other roles,
lease requires a private service-owned parent/inode, and flock is local to a
host/inode. Differently owned role services on Control and Agents cannot be
asserted to share that private inode. Process death releases flock, so an
exclusive holder alone would reopen admission after a crash. In-process active
counters alone also reset at broker restart. Neither meets preserve-and-resume.

This is a source completeness/compatibility gap distinct from the live audit:
even with perfect live inventory, a POST-only gate or CEO lock would leave known
source writer paths outside the boundary. Conversely, implementing the source
protocol alone would not satisfy Stage6 or prove all actual writers adopted it.
No partial gate is shipped as a complete solution.

## Next bounded implementation and decision points

1. In the existing broker entrypoint/handler, add one fail-closed admission
   primitive shared by every request thread, outside route dispatch. Close
   admission atomically before waiting for already admitted work. Hold each
   admission through provider return, durable response commit and callback
   cleanup, with exception-safe release. Timeout/error means HOLD, never drain
   success. Keep existing mTLS actor validation and current-authority checks.
2. Keep maintenance closure across broker/operator death and restart using an
   explicitly provisioned local control with validated ownership, path and
   identity. Missing, malformed or inconsistent configured control denies.
   Do not auto-create an open control or reset it during code rollback. This
   control is admission state, never a replacement execution/charge ledger.
   Define its provisioning and explicit release contract before wiring it in;
   the current private CEO inode is not a cross-host role protocol.
3. Add per-host role exclusion in existing pollers/direct entrypoints before
   directory/adapter initialization, and hold through all local writes and
   signed transitions. Include CEO, Manager, Worker A/B/C and supported legacy
   entrypoints; adjust exact config validators and package manifests together.
   A broker drain cannot stand in for these local leases. Existing maintenance
   procedure must independently establish every host participant; do not add a
   new coordinator or infer a remote lease from a local one.
4. Only report a boundary after local writers are excluded, broker admission
   is closed, and admitted broker work has drained. Preserve existing signed
   histories, original sessions/requests/attempts, reservations, charges,
   completed responses, pending reviews and provider intents. Code rollback
   must restore source only, never database/JSON snapshots, quotas or admission
   to OPEN. Keep legacy deployment unavailable for this operation until its
   restart and exception paths honor the same boundary and Stage6.
5. Before selecting source changes for commit, synthetic tests must race each
   role/route against closure, slow body/provider/commit and exceptions; prove
   no post-close callbacks or initialization writes; prove restart/operator
   death stays closed; and reject missing/unsafe/replaced controls. Exercise
   COMPLETE reuse with replay forbidden, unknown/PENDING/conflicting HOLD,
   no quota reset, and code-only rollback with byte-identical durable state.
   Run strict installed candidate profiles for every modified package/entrypoint.

These are implementation acceptance cases for the existing maintenance task,
not new authorization gates. The source task has not completed items 1–5.
No production action is required to write those tests or source, but compatibility
cannot be claimed until the role configuration/provisioning contract and full
writer coverage above are implemented and tested together. No owner approval
is requested again for the already authorized preserve-and-resume policy.

## Validation and limitations

Fresh synthetic regression command and results are recorded below after execution.
Raw output is kept project-local in
tests/acceptance-evidence/p1-04-maintenance-source-20261105/.
No raw inventory, environment, live configuration, credentials or ledger content
is selected for commit. Review is source inspection plus synthetic execution;
real provider execution, live reachability, complete writer discovery and loaded
code identity are not independently verified.

Production remains DENIED by the existing Stage6 gate. Mandatory GitHub/Claude
review and operational acceptance remain outstanding; this report supplies
neither. No real CEO was attached/enabled, production service deployed/restarted,
live ledger changed, real inference retried, or capital/payment/launch action used.

Fresh execution (PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=.:integrations/payment_adapter,
150-second timeout, existing loopback-only socket runner):

```text
python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_stage6_resume_safety tests.test_deployment_resume tests.test_deployment_broker_restart tests.test_resume_boundary tests.test_research_poll_isolation tests.test_ceo_stage6_gate tests.test_ceo_broker tests.test_ceo_pending_recovery tests.test_ceo_candidate_acceptance tests.test_broker_mtls_entrypoint tests.test_hierarchy_service_research
```

Result: **84 tests in 66.627s, OK, exit 0**. No failures/errors in the unittest
result. Expected synthetic refusal/crash tracebacks and SQLite ResourceWarnings
remain in the raw output; they do not establish that resource warnings were fixed.
Bridge process proc_mw3ve30a_5douf0, PID 226074, was polled to exited. Its bridge
log path is outside the approved project root and was not opened. The complete
80,375-byte project-local tests.log was read through venture-control with
truncated=false. Raw files remain local and untracked.

| Existing regression evidence | Decision and limit |
| --- | --- |
| Whole synthetic broker restart after COMPLETE wire loss | Original durable response reused; provider replay forbidden; ledger/signed-state preservation asserted. |
| Whole synthetic broker restart with PENDING wire loss | Repeated recovery held; quotas and original intent retained. |
| Unknown execution, conflicting PENDING response, missing COMPLETE response, orphan charge | Held without replacement calls/charges; ledger immutability asserted. |
| Daemon-only code rollback after response commit | Recovery reuses completion without inference; no durable-state reset. This does not prove arbitrary broker release rollback compatibility. |
| CEO pause with shared Manager/Worker traffic | Existing test passes because Manager/Worker remain active; positive evidence of the maintenance coverage gap. |

Additional command: python3 -B scripts/ceo_stage6_deployment_gate.py --preflight-resume.
Result: exit 2, DENY, deployment_allowed=false, resume_verified=false,
ceo_exclusion_observed=false. No lock was supplied; no live exclusion is claimed.
git diff --check exited 0. Report references and staged scope are checked before
commit. Operator impact is one documentation file plus local synthetic evidence.
No runtime implementation or test file changed. Only this report is selected for
commit; the worktree remains intentionally dirty with unrelated preserved work.

SHA256 identifiers for the fresh project-local evidence:

- tests.log: f4d2ae36918c7c52c0babe5a4f30d16f92082c7d3a6323aae217747128618ce1
- preflight.json: b3984de7747737d39ccf40b400d1c873634c8d9652d09500284d48b04cf4b9a6

These hashes identify execution artifacts, not independent provider provenance.

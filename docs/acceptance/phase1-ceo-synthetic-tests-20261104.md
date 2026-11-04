# Phase 1 CEO Stage 2/3 — bounded synthetic test evidence, 2026-11-04

Scope: the Owner-requested R1 software acceptance tests following
[the audit at ff8539b](phase1-ceo-audit-20261104.md).
Source baseline: main `ff8539bd67385505e9e1cd776f60f5d10b1fd40a`.
**Synthetic evidence only; no production acceptance, deployment or authority change.**

## Changes and per-case decision log

Only two test files and this evidence package are added. Production runtime,
architecture, approval rules, quotas and historical specifications are unchanged.

| New test case | Verified result | Decision |
| --- | --- | --- |
| New signed dependent plan | Current admission rejects C depending on A/B atomically; signed journal unchanged | PASS, synthetic |
| Historical signed dependent plan | Proposal has A/B PENDING and C BLOCKED; approval readies A/B only; A alone leaves C BLOCKED; B completion readies C; C submits successfully; each checkpoint reopens/verifies without rewriting old records | PASS, synthetic |
| R1 signed mTLS sequence | Synthetic Owner approval snapshot, signed CEO handoff/create, Manager independent A/B/C proposal, CEO plan approval, A/C/B submission, Manager synthesis, signed CEO REJECT_OR_DEFER disposition | PASS, synthetic |
| R1 retry/restart checkpoints | Lost Manager execution reply reconciles original intent without a new charge/call; Worker persisted response survives restart before apply; exact committed apply replay returns original snapshot; terminal polls do nothing | PASS, synthetic |
| Reservation and quota HOLD | Exact reservation replay after reopen stays one charge; exact execution replay stays one model call; sibling TLS actor denied; fifth reservation denied; CEO signs HOLD at four reservations without refund/reset | PASS, synthetic |
| Negative identity and operations | Unpinned/wrong-role certificates, role relay, invalid signature, stale revision, changed duplicate, launch/payment/deploy/finance commands denied; state and counts unchanged | PASS, synthetic |

The historical fixture invokes the existing replay transition semantics only
while generating the old writer's signed records. Current admission, reopen and
verification are unpatched. This is a generated historical-contract fixture,
not an imported production journal or independently observed historical run.

The wire test uses the actual research daemon, role service, HierarchyRunner,
ModelRoleCallback, HierarchyProvider, HierarchyClient, isolated mTLS broker handler,
HierarchyGateway, VentureWorkflow, DurableRoleArtifactStore and central reservation/
execution paths. Existing TLS and admission utilities provide generated test keys
and the synthetic approval snapshot. All mutable stores and generated keys stay
in temporary directories under project artifacts and are cleaned up.
No installed credential, configuration, service or business journal is accessed.
Model selection/boundaries are simulated with deterministic Sol/Luna responses;
the synthetic model never invokes a provider. Environment is cleared during
execution, external DNS/connections are blocked, and admission/allocation/payment
entry points are guarded against accidental invocation.

R1 ends with eight signed journal records, one terminal decision, three used
effort units, three Worker reservations/executions, five CEO/Manager reservations,
three centrally recorded executions (two Manager, one terminal CEO review), and
eight total daily reservation rows. The existing CEO plan-approval path reserves
centrally and executes its simulated model locally; it is not counted as a
broker-recorded execution. The test verifies every journal command signature,
the terminal review signature, artifact digests, and execution-to-input-snapshot
joins, including each Worker's resulting artifact. Reopened state and counts
must match. These assertions do not infer execution from a reservation alone.

## Commands and raw results

Both commands ran through venture-control asynchronously; their processes were
polled to exited and completed root-contained logs read through the bridge.
Bridge-owned process logs outside the approved root were not opened.

Focused final process: `proc_mw2jdwr9_n4gbwz`, PID 1501033.
**5 tests, 6.359 seconds, OK, exit 0.**

```sh
TMPDIR="$PWD/artifacts/phase1-ceo-synthetic-tmp" PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest \
 tests.test_ceo_legacy_dependent_replay tests.test_ceo_research_mtls_acceptance -v
```

Existing audit suite process: `proc_mw2jdbq5_f5817h`, PID 1500679.
**127 tests, 15.468 seconds, OK, exit 0.**

```sh
TMPDIR="$PWD/artifacts/phase1-ceo-synthetic-tmp" PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest \
 tests.test_broker_isolated_mtls tests.test_broker_mtls_entrypoint \
 tests.test_hierarchy_artifact_store tests.test_hierarchy_runner \
 tests.test_research_continuation tests.test_mvp_handoff \
 tests.test_ceo_pending_recovery tests.test_ceo_research_review \
 tests.test_research_poll_isolation tests.test_research_abc_routing \
 tests.test_research_broker_admission tests.test_hierarchy_service_research \
 tests.test_ceo_durable -v
```

The temporary root was created before running these commands. Full per-test
outputs, exit codes and test/log hashes are committed in
[ceo-synthetic-20261104](../../tests/acceptance-evidence/ceo-synthetic-20261104/SHA256SUMS):
[focused output](../../tests/acceptance-evidence/ceo-synthetic-20261104/focused.log),
[127-test output](../../tests/acceptance-evidence/ceo-synthetic-20261104/regression127.log).
This manifest supplements the raw outputs; it does not replace them.

Focused output includes expected injected OSError tracebacks and quota-HOLD
warnings. Development runs corrected fixture-only assumptions (unused legacy
signer configuration, task construction, and expected denial text/status).
Invalid signatures currently produce a generic broker HTTP 503 rather than 400;
the test proves rejection and unchanged state without altering runtime.
Python 3.14 ResourceWarnings about HTTPError cleanup and existing SQLite fixture
connections remain visible in the raw outputs. No test is failed or skipped.
No production logic defect requiring a runtime change was reproduced.

## Assessment, limits and remaining blockers

Authority: local fixtures exercise the existing research-only approval gate;
they grant no real venture, model purchase, launch, payment or deployment scope.
No real CEO was attached or invoked; no real capital or external business action
was used. Existing untracked runtime/evidence files were preserved and excluded
from staging. Operator impact is limited to isolated loopback tests and new files.

Provenance: test execution was observed through venture-control in this workspace.
It is independently rerunnable software evidence, not evidence of deployed
exchange or real provider execution. Temporary signed journals/keys are not
published; signature and artifact joins are verified during each run. The logs
and manifest alone are not an independently re-verifiable signed production
ledger or a full Stage 5 acceptance package.

This bounded wire test covers R1 and terminal rejection. It does not establish
one complete wire trace through R2/R3, positive MVP disposition, every adversarial
combination or process-kill recovery. Existing 127-case tests retain their own
separate fixture evidence for continuation, recovery and inert MVP disposition;
their results are not merged into the new R1 trace. ADV certification was not
rerun, and ADV-001–ADV-049 and the /49 denominator are unchanged.

Production blockers from the audit remain: installed source/config/trust and
approval provenance, active exchange and loaded-byte attestation, service topology,
real provider evidence, separate MVP/build authority and required independent
GitHub/Claude review evidence. None is resolved or inferred by these tests.
No deployment is applicable because runtime was not modified.

Reviewer decision: **NOT_REVIEWED**. The requested tests pass; broader synthetic
stage completion and production readiness are not claimed.

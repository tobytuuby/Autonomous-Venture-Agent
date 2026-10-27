# Venture hierarchy validation and implementer review

2026-10-27. Requested baseline: main
`8b85728f98305cb78e56d09f92f4dd79ec10bb43`.
Execution class: **independently observed local tests with synthetic role/signature
fixtures**. No real provider inference, CEO decision or human owner discussion is
established. This is supplemental workflow evidence, not ADV recertification.
ADV-001–ADV-049 and /49 remain unchanged.

## Technical evidence

| Run | Command | Observed result |
| --- | --- | --- |
| Initial focused | `python3 -m unittest tests.test_venture_workflow tests.test_ceo_escalation_inbox tests.test_owner_approval -v` | 44 tests, OK, exit 0 |
| Intermediate focused | same command after signed-history hardening | 44 tests, OK, exit 0 |
| Intermediate full | `python3 -m unittest discover -s tests -v` | 739 tests, OK, exit 0 |
| Final focused | focused command above, with four additional workflow tests | **48 tests in 2.816s, OK, exit 0** |
| Final full | full command above | **743 tests in 12.280s, OK, exit 0** |

Raw per-test outcomes are in the verbose logs in this directory. No failing test
run occurred. Final source hashes, raw output hashes and log hashes are in
SHA256SUMS. The final tests include the pre-existing dirty owner implementation
and owner tests; they do not independently certify a pristine baseline checkout.

Asynchronous bridge executions were polled until exited, then completed project
logs and explicit exit-code files were read:

| Process | PID | Bridge process log |
| --- | --- | --- |
| proc_mvqze2pv_re2jkv | 1225658 | /home/epsilon/.chatgpt2localbridge/process-logs/proc_mvqze2pv_re2jkv.log |
| proc_mvqzf7tc_zotzbj | 1226818 | /home/epsilon/.chatgpt2localbridge/process-logs/proc_mvqzf7tc_zotzbj.log |
| proc_mvqzifok_h7hupu | 1229612 | /home/epsilon/.chatgpt2localbridge/process-logs/proc_mvqzifok_h7hupu.log |

Commands redirected detailed output to project-local artifacts; committed copies
are the exact completed logs, not reconstructed summaries.

HEAD advanced during work to `15098cc9fb727dc1889eb8ba913c1f34285d288f`,
containing only the initial workflow and its tests. This turn did not issue that
commit command. It was preserved, inspected, and the final implementation and
regressions were validated on top. No reset/rebase or owner-file staging was used.

## Decision log

| Finding / scenario | Decision and evidence |
| --- | --- |
| Positive hierarchy and improvement | Accepted locally: manager delegation, worker evidence, improvement, manager review, CEO recommendation, human-origin signed owner fixture, then request-only finance |
| Manager rejects premise | Blocked until CEO redirection with next version and repeated reviews |
| Owner rejects proposal | Finance blocked; no direct replacement approval; correction repeats every gate with a fresh discussion receipt |
| Gate skipping / impersonation / stale binding | Denied with accepted state unchanged; table-driven unlisted transitions and role/signature/origin tests |
| Budget and finance ceiling | Over-budget submission/delegation records exhaustion; correction retains accepted consumption; invalid cents denied |
| Hold, security and termination | Approval invalidated; owner security clearance and CEO resume return to redirection; termination blocks new transitions |
| Correction and idempotent concurrency | Invalid attempt can be corrected; eight concurrent identical accepted commands converge to one event; conflicting ID denied |
| Crash and corrupt journal | Transaction rollback preserves prior state; event/snapshot damage and deleted tail denied; rewritten signed command with recomputed event hash denied |
| Inbox integration | Missing CEO key and mismatched handoff/venture/manager denied; no advisory fallback decision |
| External effects | Payment capture, treasury allocation and operational admission are instrumented to fail if called; complete positive path succeeds without calling them |
| Owner files | All 580 enumerated pre-existing dirty-file SHA-256 fingerprints unchanged; inaccessible pre-existing directories were not opened or changed |
| Readiness | Suitable for local preparation review only; independent human acceptance is not claimed |

## Operator impact, provenance and remaining limitations

The operator gains a durable, readable review/request state machine and a
[Studio Restock Kit example](../../../docs/venture-hierarchy-implementation-v1.0.md).
Every output remains preparation-only. No worker/manager is spawned and no
existing pilot database is processed. CEO approval remains a recommendation to
the human owner; the signed owner fixture is a test, not an actual owner approval.

Pinned public keys authenticate signer attestations; they cannot independently
prove reasoning or conversation. Evidence digests are supplied bindings, not
independently fetched artifact verification. Trusted control-plane isolation,
key custody, external anchoring, backup rollback protection and operational
integration remain unexecuted. Complete database replacement or privileged
last-event rewriting is outside the local hash-chain guarantee.

The canonical owner-admission registry is untouched and independently required
for future operational actions. Finance requests create no balance, reservation,
provider request or payment. No live key, capital action, production CEO,
systemd/service change or public deployment was used. All live actions remain
denied. Final independent human review and any operational authority remain open.

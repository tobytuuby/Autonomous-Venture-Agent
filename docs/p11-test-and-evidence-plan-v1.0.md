# P11 Focused Test and Evidence Plan

**Version:** 1.0
**Focused denominator:** 69 named cases
**Base regression:** 543 tests recorded on P10. With 69 P11 cases, expected total is 612 only if the prior suite is unchanged; actual discovery/execution establishes the denominator.

## Focused case registry

| Family | Cases | Required coverage |
|---|---:|---|
| Valid planning package and safe result | 4 | Complete package; review-only disposition; all output authorities/actions false; production authorization false |
| Model inertness and execution mode | 4 | Approval-like model text inert; non-string model text rejected; model authorization rejected; mode/effect drift blocked |
| Candidate boundary negatives | 16 | Production candidate is descriptive only; one target/venture; read-only; synthetic data; no writes/customer data/contact/network/credentials/provider; zero exposure/loss; concurrency 1; window ≤30 minutes |
| Safeguard, monitoring, stop and recovery | 12 | Missing safeguards; each mandatory monitoring/stop family; heartbeat cap; automatic stop; no-state-change rollback/rehearsal |
| Integrity, replay, collision, and baseline binding | 9 | Configuration/source binding; hash validation; malformed/unknown input; fault injection; idempotent replay and changed-content collision |
| All nine live authorities | 9 | One true-valued attempt per authority; fail-closed result and subsequent stop |
| All fifteen action flags | 15 | One true-valued attempt per action flag; fail-closed result and subsequent stop |
| **Total** | **69** | Unique registry ID and unittest method per case |

The 69-case denominator is enforced in code. Any changed case registry requires a new evidence run and an updated denominator before review.

## Evidence requirements

Record full repository/branch/HEAD/base ancestry and clean/untracked state; exact commands, interpreter and environment; focused and full-regression discovery/pass/fail counts with raw output; all 69 case names and results; schema, source, test, policy, and plan SHA-256 plus byte lengths; gate configuration and source binding; canonical input/result hashes; replay/collision and terminal-stop outcomes; all nine authorities false; every action and model-authorization flag false; zero external/network/provider/credential/customer/capital/payment/broker/deployment/worker/venture actions; import/call-path inspection; and independent reviewer identity, hash recomputation, limitations, and ACCEPTED/BLOCKED decision.

## Evidence limitation

This evidence can show only that a synthetic plan validator applies its declared scope checks. It cannot show production system safety, production monitoring, actual staffing, access isolation, rollback effectiveness, reliability, legal/compliance approval, or permission to conduct a live test. Recorded test totals are not independently confirmed unless the reviewer executes or otherwise independently validates the underlying run evidence.

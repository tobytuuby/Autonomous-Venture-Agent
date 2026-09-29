# P10 Focused Test and Evidence Plan

**Version:** 1.0
**Focused denominator:** 42 named cases
**Base regression:** P9 corrected main at `616aa066db77f1bc25730929dd57d16d92ac386c`; baseline 501 tests before P10

## Focused case families

| Family | Cases | Required coverage |
|---|---:|---|
| Baseline and valid contracts | 4 | Valid synthetic ownership, control attestation, shadow change review, complete rehearsal |
| Authority and effect denial | 9 | One attempted true value for each live authority; safe result and terminal stop |
| Model non-authorization | 3 | Approval-like model output, authorization flag, model override of failed control |
| Operating model denials | 3 | Missing role, duplicate roles, non-synthetic identity |
| Recurring controls | 5 | Four cadence families; failed control blocks and stops |
| Change/release denials | 3 | Missing impact, failed test, attempted live rollout |
| Incident/suspension | 2 | Synthetic suspension only; invalid suspension request blocks |
| Review evidence and isolation | 4 | Missing prerequisites, cross-run evidence, non-authorizing pass, go-live request blocked |
| Replay, sequence, integrity, and fault | 6 | Exact replay, collision, sequence violation, tampered hash, malformed payload, injected failure |
| Schema authority constraints | 1 | Schema rejects true values for every live authority |
| Baseline binding | 2 | Configuration fingerprint and source commit mismatches |
| **Total** | **42** | Each has a unique case ID and unittest method |

The full regression target is **543/543** if the P9 baseline of 501 is unchanged and these 42 P10 tests are the only additions. Both denominators must be confirmed from actual discovery and execution, not inferred.

## Evidence requirements

Preserve exact repository/branch/HEAD/base ancestry; clean and untracked state; command, interpreter, environment and UTC timestamp; raw focused and full regression output with discovered/pass/fail counts; an immutable 42-case registry mapped to distinct test methods; schema/source/test SHA-256 and byte-length inventory; all-nine-false authority fingerprint; canonical record and result hashes; event sequence and rehearsal-run identity; zero external, unauthorized, credential, provider, network, deployment, customer, capital, payment, broker, worker, and venture action counters; import/call-path review; and independent reviewer identity, recomputed hashes, limitations, and ACCEPTED/BLOCKED decision.

The evidence proves synthetic governance behavior only. It cannot prove production control activation, actual staffing/on-call coverage, real audit independence, deployed schedules, actual release governance, service readiness, or go-live authority.

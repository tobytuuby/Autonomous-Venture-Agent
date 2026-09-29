# P10 Entry Decision

**Decision date:** 2026-09-28
**Decision authority:** Kalaap Das
**Decision:** AUTHORIZED for synthetic P10 planning and implementation
**Execution class:** Synthetic, shadow, or isolated only
**Base main:** `616aa066db77f1bc25730929dd57d16d92ac386c`

## Predecessor verification

- Repository and branch state were verified through the venture-control bridge.
- `main` and `origin/main` were both at `616aa066db77f1bc25730929dd57d16d92ac386c`, with a clean worktree.
- This commit merges the independently accepted P9 malformed-enum fail-closed correction and its evidence supplement.
- The corrected P9 baseline full regression is 501/501; P9 focused remains 48/48.
- No P10 implementation existed on the verified base.
- The P9 status/acceptance documents previously said P10 was unauthorized; this separate user authorization supersedes that restriction only for the scope in `p10-policy-spec-v1.0.md`.

## Authorized scope

P10.0–P10.4 synthetic governance rehearsal: in-memory validation of synthetic ownership fixtures, four recurring-control evidence families, shadow-only change/release review, simulated incident suspension, and a steady-state rehearsal decision. The strongest possible success result is `SYNTHETIC_REHEARSAL_PASS`.

This decision does not authorize production readiness, general go-live, live control scheduling, actual human assignment/contact/approval, deployment, rollback execution, provider/network/credential access, customer/capital/payment/broker actions, CEO attachment, live worker or venture authority, or any other external action. All nine live authorities remain denied. Model output cannot authorize an action. No P11 work is authorized.

## Exit gate

P10 implementation remains unaccepted until the 42-case focused suite and full regression pass at recorded denominators; schemas, hashes, evidence provenance, and all-nine-false enforcement are verified; runtime imports/call paths are reviewed; evidence shows zero side effects; and an independent reviewer records ACCEPTED or BLOCKED for the exact pushed branch. Acceptance, if granted, will apply only to synthetic rehearsal.

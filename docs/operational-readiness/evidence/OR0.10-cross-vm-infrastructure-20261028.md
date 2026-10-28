# OR-0.10 cross-VM infrastructure verification — 2026-10-28

**Verdict: PARTIAL / NOT ACCEPTED.** Service-placement checks and local synthetic tests passed. Authenticated end-to-end cross-VM handoff was not demonstrated. A Control CEO exercise service is failed.

## Read-only VM observations
- Venture-Control: `venture-control-broker` active; `venture-control-bridge` active; PostgreSQL active; OPA active; OpenBao active; `venture-control-tunnel` active. Control broker unit directly Requires=opa.service, matching intended placement.
- Venture-Agents: `venture-agents-bridge` active; `venture-agents-tunnel` active. PostgreSQL, OPA and OpenBao absent/inactive there, consistent with current placement.
- `venture-ceo-shadow` inactive on both hosts (no standing autonomous CEO service enabled).
- **Unexpected:** Control `venture-ceo-exercise.service` is **failed**: `ActiveState=failed`, `Result=exit-code`, `ExecMainStatus=4`. This needs bounded diagnosis; it is not evidence of a successful handoff.
- Existing temporary specialist pilot systemd units showed failed states in a service listing; they were not changed and are not included in a clean operational pass.

## Focused tests
On Venture-Control ran `python3 -m unittest tests.test_authenticated_handoff tests.test_broker tests.test_synthetic_orchestration -q`: **exit 0; 36 tests in 2.739s; OK**. These tests validate local synthetic paths, test-only keys and denial behavior only to the extent defined by each test. They are NOT a live cross-VM signed request/response test.

## Scope and unresolved gate
- Live broker and tunnel status checked; neither authenticated cross-VM payload delivery nor receipt/acknowledgement was observed in this execution.
- No PostgreSQL backup/restore, OPA policy query, OpenBao lease, or end-to-end remote manager/worker activity was exercised.
- The failed CEO exercise service warrants read-only diagnostics before a bounded correction. Do not silently restart or enable it, do not create live authority.
- No service was started/stopped/restarted, no sudo or payment action, no public customer call and no unrelated worktree cleanup performed.

**Next bounded task:** inspect sanitized logs and service configuration for failed `venture-ceo-exercise.service`; determine whether a real test-only, authenticated cross-VM handoff endpoint exists; exercise it without owner/finance authority; verify fail-closed negative cases; rerun checks. This is required before OR-0.10 acceptance.

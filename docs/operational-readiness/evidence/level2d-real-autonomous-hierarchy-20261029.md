# Level 2D — real autonomous preparation hierarchy evidence

Date: 2026-10-29 UTC. Operator verification collected at 15:33 UTC.
**Status: Operational technical journey PASS; independent auditor acceptance pending.**
No real venture launch, owner approval, customer action, payment, or finance release.

## Automated certificate renewal

Both VM renewal services and timers are present and enabled:
- Control: `venture-level2d-cert-renew-control.timer`; latest check `renewal_control_completed no_changes` and systemd success.
- Agents: `venture-level2d-cert-renew-agent.timer`; latest check `renewal_manager_not_due` and systemd success.
- Certificate issuance and authenticated Manager CSR exchange were separately exercised and captured in `level2d-mtls-renewal-20261029.md`. Renewed certificate expiry dates: Manager 2026-11-12 14:13:47Z, CEO 2026-11-12 14:01:47Z, broker 2026-11-12 14:04:41Z.
- Renewal timers must be monitored; timer presence does not prove uninterrupted future renewal.

## Real autonomous preparation-only hierarchy, workflow level2d-acceptance-5

All decisions below were recorded as signed role-authorized transitions by the **Control broker's durable workflow audit**. Each transition occurred while role-scoped CEO (Control), Manager (Agents), and Worker (Agents) services were running. No ChatGPT relay for each delegation or correction.

| UTC issuance | Actor | Signed transition | Durable state |
|---|---|---|---|
| 15:26:42 | CEO | create | MANAGER_PENDING |
| 15:26:49 | Manager | delegate | WORKER_PENDING |
| 15:26:54 | Worker | submit | MANAGER_REVIEW |
| 15:26:58 | Manager | improve | WORKER_PENDING |
| 15:27:03 | Worker | submit | MANAGER_REVIEW |
| 15:27:08 | Manager | improve | WORKER_PENDING |
| 15:27:12 | Worker | submit | MANAGER_REVIEW |
| 15:27:17 | Manager | improve | WORKER_PENDING |
| 15:27:21 | Worker | submit | MANAGER_REVIEW |
| 15:27:27 | Manager | manager_approve | CEO_REVIEW |
| 15:27:33 | CEO | ceo_approve | OWNER_REVIEW |

- **Final state:** `OWNER_REVIEW`, revision 11, mode `PREPARATION_ONLY`, declared preparation effort `used_units=5`, `operational_authority=false`, `money_released=false`.
- Control `VentureWorkflow.verify()` independently replayed the hash-chain and verified every signed transition under the broker's pinned Ed25519 trust manifest. `VentureWorkflow.read()` returned the same final state.
- Durable Manager inference database for `run5`: 5 calls, 5 completed, 0 pending.
- Durable Worker inference database for `run5`: 4 calls, 4 completed, 0 pending. Worker calls are `gpt-6-luna` using the existing Control provider gateway and centrally metered budget policy.
- Durable CEO inference database for `run5`: 1 call, 1 completed.
- Provider traces in broker: 5 Worker responses (4 completed with `finish_reason=stop`, plus a retained older `length` outcome) and 9 Manager broker responses (8 `stop`, 1 earlier `length`). Retained failures from earlier runs were not cleared or replayed.

## Restart, failure handling and code quality

- The Control broker, CEO, Manager and Worker systemd services were restarted following the terminal state. The broker remained active; CEO recognized `OWNER_REVIEW_ONLY` and exited normally; Manager and Worker remained active polling and reported `OWNER_REVIEW`.
- **No repeated inference after restart:** CEO remained 1/1, Manager 5/5, Worker 4/4 completed calls.
- Earlier acceptance sessions with incomplete provider responses were preserved as ambiguous durable intents; they were **not automatically replayed or claimed successful**. The final acceptance used a fresh bounded technical workflow identity.
- A narrow adapter improvement for `gpt-6-luna` sets `reasoning_effort=none` within the existing 1024 completion-token bound; OpenAI documents Luna support for this setting. Committed as `a046800`; broker provider adapter deployed with backup of prior version and broker active; existing CEO mTLS status probe HTTP 200. The successfully completed run5 used the prior `low` adapter.
- Final committed-source regressions: **Control 986/986** and **Agents existing checkout 365/365** passed.
- Existing dirty worktree files and unrelated venture runtime artifacts were preserved.

## Scope and limits

This is a real provider-backed **preproduction technical** hierarchy test, not a productive business venture or organizational production certification. The test used the previously approved bounded fixture (no external actions). No Owner signature was issued, and final Owner authorization is still required to operate any real venture. Full VM reboots were not performed; **service restarts** were verified. Independent Claude acceptance of Level 2D and separate legal/commercial readiness remain pending.

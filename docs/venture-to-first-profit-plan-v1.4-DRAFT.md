# Cost-Conscious Path to the First Venture

**Version:** 1.4
**Binding core policy:** [Owner venture approval v1.0](owner-venture-approval-policy-v1.0.md)
**Status:** Draft for Kalaap Das’s review
**Supersedes:** `venture-to-first-profit-plan-v1.3-DRAFT.md`
**Purpose:** Specify a low-cost shared launch platform, CRM, one-vendor finance connection, and real venture registry/ledger while keeping the synthetic finish line finite.
**Plan type:** Working execution plan; not a numbered phase, gate decision, or authorization to change runtime or perform external actions.

## Objective

Move from the existing synthetic CEO/manager/worker demonstration toward one bounded, short-term profit-seeking venture. Reuse the project’s existing Python and Linux VM infrastructure, keep shared software self-hosted where practical, and avoid per-venture subscriptions and custom systems. Use **one financial vendor and one designated account for the entire $1,000 project pool**. Each venture’s $100 limit is enforced in the internal ledger; it does not get its own bank or payment account.

Each venture gets isolated records and a customer page on the shared platform. The generic CTK Brand Management page remains independent and has no venture links.

## Decisions already recorded

- Total initial project seed pool: **$1,000**.
- CEO seed allocation: **up to $100 per venture**; no venture may draw another venture’s seed allocation.
- The CEO researches and proposes; every new venture requires owner discussion and durable approval of its exact proposal/version and scope before CEO greenlight, funding, launch or operational manager work. The CEO may leave money unallocated.
- Venture profit split: **80% remains usable by that venture; 20% is saved**. At **$100 cumulative venture profit**, accumulated saved funds return to the CEO pool.
- CEO use of the growing pool to seed additional ventures is capped at **50%**; this is not an automatic launch trigger. Additional venture seed remains capped at $100.
- After that approval, managers may autonomously delegate within approved bounds. Routine contact within those bounds needs independent live/contact permission, currently denied.
- Taxes are handled by the user outside the agent workflow.
- Model-generated ideas, plans, task packets, and reports are untrusted data. They cannot grant authority, change budgets, or authorize actions.
- The project uses one financial vendor/account for the shared pool; money is not split into separate venture accounts.

Operating-policy details and unresolved choices remain in [venture-operating-policy-v1.1-DRAFT.md](venture-operating-policy-v1.1-DRAFT.md).

## Current system versus target

| Capability | Current repository/infrastructure evidence | Cost-conscious target |
|---|---|---|
| Agent orchestration | The CEO shadow runtime stores decision state in SQLite. P6/P7 record synthetic coordination and worker data. The synthetic E2E flow uses deterministic in-process fixtures; it does not create live venture agents. | Keep the current synthetic flow as the finite orchestration proof. The future manager/worker runtime uses the existing two-VM boundary and calls the control plane through the broker only. |
| Application and hosting | The project is Python-first. Infrastructure documentation describes existing `venture-control` and `venture-agents` VMs, a reserved broker port, and PostgreSQL backup to existing TrueNAS storage. | One shared Python application on the existing Linux VMs; do not add cloud hosting or another VM for the first venture. Keep customer pages isolated from the control plane, database, and management bridge. |
| CRM | No CRM/customer acquisition workflow is implemented. | Add a small CRM module to the shared app and PostgreSQL database; avoid a separate paid CRM subscription for the first venture. |
| Venture registry and ledger | P5 revenue/reconciliation/treasury are synthetic and non-spendable. They provide useful contract patterns, not live financial operations. | Use PostgreSQL for real venture records and append-only money events. Keep SQLite shadow decisions separate from operational venture accounting. |
| Financial connection | No live deposit path exists. The real payment adapter is restricted to red-team certification context; CEO/manager identities are denied. | One financial vendor and one designated account hold the shared project pool and handle the selected venture’s financial flow. Venture budgets and profit splits are internal ledger allocations; no venture-specific accounts and no second financial vendor. |
| Customer-facing pages | No storefront or venture site is implemented. | Reuse one template and one umbrella domain; assign each venture an isolated subdomain or path. Do not buy a separate domain for each short-term venture. The generic CTK page stays separate. |

The infrastructure README records PostgreSQL backup to TrueNAS. It does not prove every proposed component is currently installed or available. Verify installed services before relying on them.

## Recommended minimum platform

### 1. Shared launch platform

- Reuse the existing **venture-control** and **venture-agents** VM split. Keep PostgreSQL, policy enforcement, finance boundary, and broker on the control side; keep CEO/manager/worker runtime on the agent side.
- Keep agent-to-control traffic on the documented broker interface only. Do not expose PostgreSQL, OPA administration, secrets, SSH, or bridge management to agents or the public.
- Extend the existing Python application with the smallest required API and simple server-rendered management pages. Reuse existing project dependencies; do not add a separate frontend framework unless the first vertical slice requires it.
- Use the platform to create one venture record, assign a manager, set its $100 seed ceiling and approved scope, and report status/artifacts to the CEO view.
- Treat the generic CTK Brand Management page as a low-cost static company page. It is not a lead funnel or a prerequisite for the first venture.
- Use one umbrella domain with isolated venture subdomains or paths. The user reported purchasing the misspelled `ctkmanagemnt.com`; verify its registrar status and renewal terms before public use. `ctkbrandmanagement.com` was discussed but not confirmed purchased. Do not use ctkfamily.com.

### 2. CRM and customer workflow

Add only the fields needed to run one short-term customer test:

- venture ID and prospect/customer ID;
- source and date collected;
- offer or product of interest;
- contact status, last contact, response, and next action;
- consent/contact basis and opt-out/suppression status where applicable;
- sale/order/booking reference and outcome.

Every record must be scoped to a venture. Managers can research, prepare an offer, and record prospect outcomes. Customer/vendor outreach occurs only within the exact venture scope and after the required live authority is separately enabled. Do not buy a standalone CRM before the shared module proves inadequate.

### 3. Real venture registry and ledger

Use the existing PostgreSQL service rather than a new database subscription. Keep a registry record per venture with:

- venture ID, proposal and viability evidence;
- owner discussion reference, signed approval/denial receipt and exact proposal/version/scope binding, CEO recommendation and manager assignment;
- $100 maximum seed allocation, scope, start date, status, and stop rule;
- customer workflow and customer-page address;
- artifact references and review history.

Record all money as integer cents in an append-only, idempotent ledger. Each event includes venture ID, event type, amount, currency, source/reference, timestamp, actor/service, policy decision, and unique idempotency key. Track separately:

- the one account’s actual balance and external deposits;
- the CEO pool’s internal available balance;
- each venture’s internal seed allocation and remaining allowance;
- receipts, refunds, operating costs, and fees by venture;
- venture profit and 80/20 allocations;
- saved amounts and ledger-only transfers back to the CEO pool at the $100 milestone;
- reconciliation to the same provider’s statements or transaction records.

The internal seed allocation is not a separate account or permission to draw from another venture’s cap. Enforce no cross-venture borrowing and no seed allocation above $100. A 20% save returned to the CEO pool is an internal ledger reclassification unless an explicitly authorized external transfer is required. Require ledger entries for every balance change; do not let a model directly set balances. Back up the ledger using the existing PostgreSQL/TrueNAS backup path and verify restore before operational use.

### 4. Single-vendor financial connection and controls

Use one narrow finance service between the agents and the **single designated financial vendor/account**:

1. Kalaap funds one account for the full project pool; do not open or fund accounts for individual ventures.
2. Select one financial vendor that can support the chosen venture’s required incoming and outgoing money flow. The same vendor/account must serve the pool and the ventures.
3. If the first venture’s payment or payout path would require a second financial vendor, do not add it silently. Prefer a venture/payment method the selected vendor supports, or return the tradeoff to Kalaap before changing this one-vendor rule.
4. Credentials, if required, are held by the finance service in the approved secret store (OpenBao if installed and verified), never in prompts, agent workspaces, or Git. The CEO requests bounded operations and never receives bank login credentials.
5. CEO/manager requests go through the broker. The finance service independently checks venture identity, project and venture balances, the $100 seed ceiling, operation type, amount, idempotency, beneficiary, current owner approval for the exact proposal/version/scope, and current policy.
6. The finance service records the request, allow/deny result, provider receipt, and matching per-venture ledger entries. Read-only balance/reconciliation access is the first connection; money movement is enabled only for exact allowed operations.
7. No retries on ambiguous money outcomes; reconcile by idempotency key and the same provider’s statement before retrying.

Use existing policy and broker boundaries (OPA/broker where already available); verify their deployment before treating them as operational controls. Compare the one-vendor candidates using official fee schedules, account terms, and API documentation after a first venture defines the needed flow. Check account, monthly, incoming-payment, outgoing-transfer, refund/dispute, and transaction fees. Do not introduce a bank aggregator, separate payment processor, or other financial vendor under this plan.

## Finite testing and build order

| Order | Work | End evidence |
|---|---|---|
| 1 | Finish synthetic orchestration | One complete CEO → manager → bounded worker → aggregate → CEO review run; required negative cases; all nine live authorities denied; exact focused/full test denominators and raw outputs. The existing plan records 6 focused and 618 full tests at its draft snapshot; confirm current counts for the final run. |
| 2 | Stop synthetic testing | After that fixed run and Kalaap’s review, stop. Fix only a concrete defect; rerun affected focused tests and one full regression. No provider tests or production probes are part of the finish line. |
| 3 | Resolve essential operating rules | Kalaap decides the 50/50 calculation base, routing after $100 cumulative profit, stop/time/loss rule, minimum viability standard, and confirms one account/vendor for the shared pool. |
| 4 | Build one-venture vertical slice | Implement registry, ledger, minimal CRM, manager workflow, isolated customer page, and finance adapter against synthetic fixtures. Demonstrate one-account accounting, tenant isolation, budget enforcement, 80/20 allocation, idempotency, denied requests, and reconciliation without external transactions. |
| 5 | Evaluate one financial vendor | After the first candidate defines the flow, compare current fees and verify one vendor/account supports funding, customer receipts, records, and required outgoing transactions. Do not connect it or open another account during this evaluation. |
| 6 | Start bounded operation | Requires Kalaap’s review and separate exact authorization for the first venture’s live operations, target, spending caps, contact scope, one selected account/vendor, and stop conditions. Every new venture first requires owner discussion and explicit proposal/version/scope approval. Afterward, the manager may autonomously delegate within approved bounds; independent live authority checks remain mandatory. |

The assistant reports evidence and technical findings. Kalaap alone decides acceptance, whether a gate is blocked, and whether to authorize live operation.

## Decisions needed before any live connection

1. Which single account will hold the $1,000 and how Kalaap will fund it.
2. Which single financial vendor can support the first venture’s actual money flow and the required API controls.
3. The CEO-pool 50/50 calculation base.
4. Where later 20% savings go after the $100 cumulative-profit milestone.
5. The venture stop duration/loss/performance rule.
6. Minimum viability evidence and payback expectations.
7. The first venture’s offer and whether its customer payments can use the selected vendor/account without adding another financial vendor.

## Boundaries

- This plan changes no runtime code or phase status and authorizes no provider/network call, customer/vendor contact, account connection, deposit, spending, money movement, publishing, or deployment.
- All nine live authorities remain denied until a separate exact bounded operating authorization is made.
- The approved P12–P14 roadmap remains separate; this plan neither repurposes ctkfamily.com nor authorizes its limited test.
- The intended incremental license spend is **$0 where existing self-hosted components suffice**. Actual account, transaction, domain, power, connectivity, and hosting costs are not assumed to be zero.
- This document does not claim that the proposed platform components already exist or that any test/gate has been accepted.

## Owner admission implementation increment — 2026-10-26

The local durable registry now separates synthetic records from operational admission. Pending/denied ventures cannot pass the owner gate. Verify signatures, proposal changes, expiry, manager and budget scope at each admission; retain signed receipts and admission evidence. The current store does not execute actions, allocate spendable money, implement the shared PostgreSQL platform, or enable live permissions. Venture #1 is an unapproved pilot, with no grandfathered funding or launch. See the binding core policy for receipt fields, trust boundary and remaining deployment work.

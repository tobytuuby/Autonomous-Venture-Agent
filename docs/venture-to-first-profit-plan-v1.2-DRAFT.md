# Cost-Conscious Path to the First Venture

**Version:** 1.2
**Status:** Draft for Kalaap Das’s review
**Supersedes:** `venture-to-first-profit-plan-v1.1-DRAFT.md`
**Purpose:** Select a minimum-cost shared launch platform, CRM, controlled finance connection, and real venture registry/ledger while keeping the synthetic finish line finite.
**Plan type:** Working execution plan; not a numbered phase, gate decision, or authorization to change runtime or perform external actions.

## Objective

Move from the existing synthetic CEO/manager/worker demonstration toward one bounded, short-term profit-seeking venture. Reuse the project’s existing Python and VM infrastructure, keep shared software self-hosted where practical, and avoid per-venture subscriptions and custom systems. Each venture gets isolated records and a customer page on the shared platform. The generic CTK Brand Management page remains independent and has no venture links.

## Decisions already recorded

- Total initial project seed pool: **$1,000**.
- CEO seed allocation: **up to $100 per venture**; no venture may draw another venture’s seed allocation.
- The CEO assesses likely profitability before funding and may leave money unallocated.
- Venture profit split: **80% remains usable by that venture; 20% is saved**. At **$100 cumulative venture profit**, accumulated saved funds return to the CEO pool.
- CEO use of the growing pool to seed additional ventures is capped at **50%**; this is not an automatic launch trigger. Additional venture seed remains capped at $100.
- Routine customer/vendor contact within a venture’s defined scope does not need individual user approval.
- Taxes are handled by the user outside the agent workflow.
- Model-generated ideas, plans, task packets, and reports are untrusted data. They cannot grant authority, change budgets, or authorize actions.

Operating-policy details and unresolved choices remain in [venture-operating-policy-v1.0-DRAFT.md](venture-operating-policy-v1.0-DRAFT.md).

## Current system versus target

| Capability | Current repository/infrastructure evidence | Cost-conscious target |
|---|---|---|
| Agent orchestration | The CEO shadow runtime stores decision state in SQLite. P6/P7 record synthetic coordination and worker data. The synthetic E2E flow uses deterministic in-process fixtures; it does not create live venture agents. | Keep the current synthetic flow as the finite orchestration proof. The future manager/worker runtime uses the existing two-VM boundary and calls the control plane through the broker only. |
| Application and hosting | The project is Python-first. Infrastructure documentation describes existing `venture-control` and `venture-agents` VMs, a reserved broker port, and PostgreSQL backup to existing TrueNAS storage. | One shared Python application on existing infrastructure; do not add cloud hosting or another VM for the first venture. Keep public customer pages isolated from the control plane, database, and management bridge. |
| CRM | No CRM/customer acquisition workflow is implemented. | Add a small CRM module to the shared app and PostgreSQL database; avoid a separate paid CRM subscription for the first venture. |
| Venture registry and ledger | P5 revenue/reconciliation/treasury are synthetic and non-spendable. They provide useful contract patterns, not live financial operations. | Use PostgreSQL for real venture records and append-only money events. Keep SQLite shadow decisions separate from operational venture accounting. |
| Financial connection | No live deposit path exists. The real payment adapter is restricted to red-team certification context; CEO/manager identities are denied. | Add one provider-neutral finance adapter behind the broker and finance service. Prefer the designated account’s official API if it supports the required narrow operations; avoid a paid aggregator unless direct access is unavailable. Select a payment processor only when the first venture’s sales path requires one. |
| Customer-facing pages | No storefront or venture site is implemented. | Reuse one template and one domain; assign each venture an isolated subdomain or path. Do not buy a separate domain for each short-term venture. The generic CTK page stays separate. |

The infrastructure README records PostgreSQL backup to TrueNAS. It does not prove that every proposed component below is currently installed or available. Verify installed services before relying on them.

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
- CEO funding decision and manager assignment;
- $100 maximum seed allocation, scope, start date, status, and stop rule;
- customer workflow and customer-page address;
- artifact references and review history.

Record all money as integer cents in an append-only, idempotent ledger. Each event includes venture ID, event type, amount, currency, source/reference, timestamp, actor/service, policy decision, and unique idempotency key. Track separately:

- CEO pool deposits and available balance;
- each venture’s seed receipt and remaining seed;
- receipts, refunds, operating costs, and fees;
- venture profit and 80/20 allocations;
- saved amounts and transfers back to the CEO pool at the $100 milestone;
- reconciliations to statements or processor reports.

Enforce no cross-venture borrowing and no seed allocation above $100. Require ledger entries for every balance change; do not let a model directly set balances. Back up the ledger using the existing PostgreSQL/TrueNAS backup path and verify restore before operational use.

### 4. Financial platform connection and controls

Use a single narrow finance service between the agents and the external account/provider:

1. Kalaap funds the designated account; the CEO does not receive bank login credentials.
2. Credentials, if required, are held by the finance service in the existing approved secret store (OpenBao if installed and verified), never in prompts, agent workspaces, or Git.
3. CEO/manager requests go through the broker. The finance service independently checks venture identity, available balance, the $100 seed ceiling, operation type, transaction amount, idempotency, beneficiary, and current policy.
4. The finance service records the request, allow/deny result, provider receipt, and matching ledger entries.
5. Read-only balance/reconciliation access is preferred initially. Deposits or transfers are enabled only for exact allowed operations. Payment acceptance is added only if the first venture needs online checkout.
6. No retries on ambiguous money outcomes; reconcile by idempotency key and provider statement before retrying.

Use existing policy and broker boundaries (OPA/broker where already available); verify their deployment before treating them as operational controls. Do not create a new paid bank aggregator or payment subscription until the selected account/venture requires it. Transaction, account, domain, and hosting fees remain provider-specific and must be checked before selection.

## Finite testing and build order

| Order | Work | End evidence |
|---|---|---|
| 1 | Finish synthetic orchestration | One complete CEO → manager → bounded worker → aggregate → CEO review run; required negative cases; all nine live authorities denied; exact focused/full test denominators and raw outputs. The existing plan records 6 focused and 618 full tests at its draft snapshot; confirm current counts for the final run. |
| 2 | Stop synthetic testing | After that fixed run and Kalaap’s review, stop. Fix only a concrete defect; rerun affected focused tests and one full regression. No provider tests or production probes are part of the finish line. |
| 3 | Resolve essential operating rules | Kalaap decides the 50/50 calculation base, routing after $100 cumulative profit, stop/time/loss rule, minimum viability standard, and account custody. |
| 4 | Build one-venture vertical slice | Implement registry, ledger, minimal CRM, manager workflow, isolated customer page, and finance adapter against synthetic fixtures. Demonstrate tenant isolation, budget enforcement, 80/20 accounting, idempotency, denied requests, and reconciliation. |
| 5 | Select the first venture’s external services | Based on its actual offer and checkout needs, choose the account/API and payment processor, if any. Compare current fees and verify operations/permissions before connecting anything. No provider is selected by this plan. |
| 6 | Start bounded operation | Requires Kalaap’s review and separate exact authorization for the first venture’s live operations, targets, spending caps, contact scope, and stop conditions. Within that authorization, the CEO decides whether the venture is viable; no per-plan or per-contact approval loop is added. |

The assistant reports evidence and technical findings. Kalaap alone decides acceptance, whether a gate is blocked, and whether to authorize live operation.

## Decisions needed before any live connection

1. Which account will hold the $1,000 and how Kalaap will fund it.
2. Whether that account offers an official API with enough restrictions for the finance service.
3. The CEO-pool 50/50 calculation base.
4. Where later 20% savings go after the $100 cumulative-profit milestone.
5. The venture stop duration/loss/performance rule.
6. Minimum viability evidence and payback expectations.
7. The first venture’s offer and whether it needs contact, booking, or online payment.

## Boundaries

- This plan changes no runtime code or phase status and authorizes no provider/network call, customer/vendor contact, account connection, deposit, spending, money movement, publishing, or deployment.
- All nine live authorities remain denied until a separate exact bounded operating authorization is made.
- The approved P12–P14 roadmap remains separate; this plan neither repurposes ctkfamily.com nor authorizes its limited test.
- The intended incremental license spend is **$0 where existing self-hosted components suffice**. Actual account, transaction, domain, power, connectivity, and hosting costs are not assumed to be zero.
- This document does not claim that the proposed platform components already exist or that any test/gate has been accepted.

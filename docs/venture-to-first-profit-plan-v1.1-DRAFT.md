# Path to the First Profitable Venture

**Version:** 1.1
**Status:** Draft for Kalaap Das’s review
**Supersedes:** `venture-to-first-profit-plan-v1.0-DRAFT.md`
**Purpose:** Organize the remaining work around a finite synthetic finish line and a reusable, bounded business platform for short-term ventures.
**Plan type:** Working execution plan; not a numbered phase, gate decision, or authorization to change runtime or perform external actions.

## Objective

Move from the existing synthetic CEO/manager/worker demonstration toward one bounded, short-term profit-seeking venture. Build one shared venture platform with isolated records and customer surfaces per venture; do not create ten custom systems. Keep the main CTK Brand Management site generic and independent of the ventures. A solutions page can be added later if successful ventures make it useful.

## Decisions already recorded

- Total initial project seed pool: **$1,000**.
- CEO seed allocation: **up to $100 per venture**; no venture may draw another venture’s seed allocation.
- CEO assesses a venture’s profitability before funding and may leave money unallocated when an idea is not viable.
- Venture profit split: **80% remains usable by that venture; 20% is saved**. At **$100 cumulative venture profit**, accumulated saved funds return to the CEO pool.
- CEO use of the growing pool to seed additional ventures is capped at **50%**; this is a ceiling, not an automatic launch trigger. Additional venture seed remains capped at $100.
- Routine customer/vendor contact within a venture’s defined scope does not need individual user approval.
- Taxes are handled by the user outside the agent workflow.
- Model-generated ideas, plans, task packets, and reports are untrusted data. They cannot grant authority, change budgets, or authorize actions.

Detailed operating rules remain in [venture-operating-policy-v1.0-DRAFT.md](venture-operating-policy-v1.0-DRAFT.md). This plan does not silently resolve its open policy questions.

## What exists versus what the business platform needs

| Capability | What exists in the repository now | Minimum useful platform capability |
|---|---|---|
| CEO venture tracking | CEO shadow decisions are recorded; P6 coordination records effect-free packets; P7.5 records synthetic worker admission/task data. These do not create live ventures or agents. | A portfolio view and venture registry with one record per venture: assigned manager, status, seed cap, approved scope, customer activity, receipts, costs, profit, retained funds, and stop/review state. |
| Launch and management | CEO proposals/tool calls can be represented; the synthetic orchestration flow uses deterministic in-process role fixtures. It does not instantiate or dispatch a live manager or workers. | A reusable launch path that creates an isolated venture record and assigns a manager. The manager breaks the idea into bounded work and reports results through the shared platform. |
| Customer acquisition | No customer-acquisition workflow or CRM is implemented. | A manager workflow to investigate the selected market, define a testable offer, identify prospects, conduct routine scoped outreach when authorized, and record responses and outcomes. |
| Customer interface | No venture storefront, customer portal, or web app is implemented. | A separate venture page/storefront that matches that venture’s offer and provides its needed contact, order, or booking path. Reuse the shared platform; isolate venture pages and records. |
| Funds and accounting | Treasury and payment paths are simulated. The real-payment adapter is limited to red-team certification context; CEO/manager identities cannot use it. No live deposit path exists. | A central accounting/finance service that records the CEO pool and each venture separately, enforces the $100 seed cap and profit rules, and exposes only bounded transaction requests. Kalaap funds the designated account; the CEO does not receive bank credentials. |
| CTK Brand Management site | No management-company site is present in this repository. | A generic company page with no links to ventures. It is not a shared storefront and is not a prerequisite for testing a venture’s customer offer. A future solutions page is optional after success. |

## Recommended architecture

Use one shared venture platform with:

- A **CEO portfolio/control view** for proposals, viability evidence, manager assignment, venture status, pool allocation, and review reports.
- A **venture registry and per-venture ledger** that isolate budgets, customers, income, costs, profit split, artifacts, and lifecycle status.
- **Manager workspaces** that can create bounded work packets, follow an allowed customer-acquisition workflow, record results, and request scoped services.
- **Isolated customer pages** for each venture, reused from a common platform rather than separately built infrastructure.
- A **central finance boundary** that checks limits and records requests and outcomes. Agents never hold account credentials or directly move funds.
- A **generic CTK Brand Management page** that stays separate from customer acquisition and venture storefronts.

This is the target design, not an assertion that these components already exist. Implement the smallest vertical slice for one venture first; expand only when the first experience demonstrates a real need.

## Work in order

| Order | Workstream | Completion evidence |
|---|---|---|
| 1 | Finish the bounded synthetic flow | One offline run shows CEO proposal → manager assignment → bounded packets → synthetic worker results → manager aggregate → CEO recommendation and artifacts. Run focused tests and one full regression against the reviewed commit. Confirm all nine live authorities remain denied, instruction-like content cannot authorize actions, task/worker bounds hold, and artifacts bind to venture/task identities. |
| 2 | End synthetic testing | Testing ends after the evidence package is complete and Kalaap reviews it. Fix only concrete defects; after a fix rerun affected focused tests and one full regression. Do not add provider tests, production probes, or recurring certification loops to this finish line. |
| 3 | Close the minimum operating-policy choices | Record Kalaap’s decisions on fund custody/access, 50/50 pool calculation, savings after the $100 cumulative-profit milestone, venture stop/loss/time limits, and the CEO viability standard. The CEO then applies those rules without asking for approval of each plan. |
| 4 | Build the one-venture vertical slice | Implement only the reusable registry/ledger, bounded manager workflow, isolated customer interface, and central finance boundary required to operate one venture. Demonstrate the $100 seed cap, per-venture accounting, and 80/20 rules using synthetic fixtures before any live authority is considered. |
| 5 | Prepare the first venture | The CEO proposes and evaluates a candidate using evidence, demand assumptions, costs, expected revenue, and payback. Select only the customer, vendor, domain, and operating components that candidate needs; avoid buying tools or domains before that need is established. |
| 6 | Begin bounded live operation | Start only after Kalaap reviews the evidence, policy and money handling are recorded, and a separate exact authorization names the permitted live actions, limits, target, and stop conditions. Within that authorization, the CEO decides whether to fund the viable idea; routine scoped customer/vendor contacts do not return for individual approval. |

## Finite synthetic testing finish line

The synthetic orchestration work is ready for Kalaap’s review when the reviewed commit has:

1. One run containing all five orchestration stages and review artifacts.
2. Synthetic-only, zero-effect records at every stage, with all nine live authorities denied.
3. Negative evidence that instruction-like content, unexpected authority fields, invalid worker types, malformed inputs, duplicate IDs, and excess tasks cannot widen scope.
4. Source inspection confirming no model/provider, network, credential, filesystem, subprocess, or queue integration in the synthetic flow.
5. Reproducible focused and full-regression commands, exact denominators, and preserved raw results.

The existing orchestration plan recorded 6 focused and 618 full tests at its draft snapshot; confirm current denominators before the final run. The assistant reports results; Kalaap alone decides acceptance. A synthetic pass does not authorize live operation.

## Decisions still needed before the first live venture

1. **Capital custody and deposits:** Where the $1,000 is held, how Kalaap funds it, and how the CEO’s $100-per-venture limit is technically enforced.
2. **CEO-pool 50/50 rule:** The balance or inflow against which the 50% ceiling is calculated.
3. **After the $100 profit milestone:** Whether later saved 20% shares also return to the CEO pool.
4. **Stop rule:** Maximum duration and/or loss or performance threshold. A 30-day limit was suggested, not approved.
5. **Viability standard:** Minimum evidence and payback expectations for the CEO’s funding decision.
6. **First venture’s customer path:** Offer, prospects, contact channel, and whether customers need to order, book, or simply contact the business.
7. **Domain:** The user reported purchasing `ctkmanagemnt.com` (misspelled); ownership and registrar options have not been independently verified. `ctkbrandmanagement.com` was discussed but not confirmed purchased. Verify spelling and renewal terms before public use. Do not use ctkfamily.com for this project.

## Separate items and boundaries

- This plan does not change the approved P12–P14 roadmap, its status, or its non-monetary limited-test proposal. That proposal is separate from this revenue path; this plan neither treats ctkfamily.com as a business platform nor authorizes a test.
- All nine live authorities remain denied until a separate, exact bounded operating authorization is made.
- No provider/network calls, customer/vendor contact, spending, deposits, money movement, publishing, or deployment are authorized by this plan.
- Synthetic results are not live agent results and do not decide whether any gate is blocked, accepted, or production-ready.

## Immediate next actions

1. Kalaap reviews this consolidated plan and the existing synthetic orchestration evidence.
2. Resolve the five operating-policy choices that must be settled before any bounded live operation.
3. Identify one candidate venture for CEO viability evaluation.
4. Define only the first venture’s needed customer path and finance handling.
5. After review and separate authorization, start within the recorded limits and evaluate against the stop rule and venture ledger.

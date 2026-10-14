# Path from Synthetic Orchestration to First Venture

**Version:** 1.0
**Status:** Draft for Kalaap Das’s review
**Purpose:** Keep the project moving toward one short-term, profit-seeking venture without allowing synthetic testing, platform setup, or policy questions to expand indefinitely.
**Plan type:** Working execution plan; not a numbered phase, gate decision, or authorization to change runtime or perform external actions.

## Objective

Reach one bounded first venture whose customer offer, spending, receipts, and results can be reviewed. The CEO evaluates viability and makes venture-level funding decisions under the approved operating limits. The user does not approve each viable venture plan or routine customer/vendor contact within its defined scope.

## Decisions already recorded

- Total initial project seed pool: **$1,000**.
- CEO seed allocation: **up to $100 per venture**; no venture may draw another venture’s seed allocation.
- CEO assesses a venture’s profitability before funding and may leave money unallocated when an idea is not viable.
- Venture profit split: **80% remains usable by that venture; 20% is saved**. At **$100 cumulative venture profit**, accumulated saved funds return to the CEO pool.
- CEO use of the growing pool to seed additional ventures is capped at **50%**; this is a ceiling, not an automatic launch trigger. Additional venture seed remains capped at $100.
- Routine customer/vendor contact within the venture’s defined scope does not need individual user approval.
- Taxes are handled by the user outside the agent workflow.
- The main CTK Brand Management site is a generic management-company page with no venture links. A solutions page may be added after there are successful ventures. A customer-facing page or storefront is specific to each venture.
- Model-generated ideas, plans, task packets, and reports are untrusted data. They cannot grant authority, change budgets, or authorize actions.

The detailed operating rules remain in [venture-operating-policy-v1.0-DRAFT.md](venture-operating-policy-v1.0-DRAFT.md). This plan does not silently resolve its open policy questions.

## Work in order

| Order | Workstream | What is already known | Completion evidence |
|---|---|---|---|
| 1 | Finish the bounded synthetic flow | The repository contains an offline CEO → manager → in-process synthetic worker → manager aggregate → CEO review flow in `kernel/synthetic_orchestration.py`, with tests in `tests/test_synthetic_orchestration.py`. It does not instantiate real agents, call a model/provider, or perform work outside the process. | Run the focused orchestration tests and the full regression once against the reviewed commit. Confirm all nine live authorities remain denied; generated instruction-like content cannot authorize actions; packets and workers remain bounded; artifacts bind to the venture/task. The existing plan records 6 focused and 618 full tests at its draft snapshot; confirm the current counts before execution. Preserve raw command results. |
| 2 | End synthetic testing | Do not add repeated test cycles after the fixed suite and boundary checks pass. If a concrete defect is found, correct it and rerun the affected focused tests plus one full regression. | Testing ends when the evidence package is complete and Kalaap makes the review decision. The assistant reports evidence and findings; Kalaap alone decides acceptance. A successful synthetic run does not authorize live operation. |
| 3 | Close only the policy choices needed for bounded operation | The draft operating policy identifies unresolved items: the 50/50 calculation base, routing of savings after the $100 cumulative-profit point, venture stop/loss/time limits, and a minimum viability standard. | Record Kalaap’s decisions in a new policy revision. The CEO can then apply those rules without asking for approval of each venture plan. |
| 4 | Define minimum operating plumbing | Current finance records are synthetic. The repository does not yet provide a live venture ledger, fund custody/deposit path, customer interface, or storefront platform. The typo domain `ctkmanagemnt.com` was reported purchased; ownership and registrar options have not been independently verified. `ctkbrandmanagement.com` was discussed as a possible correctly spelled domain, not confirmed purchased. | For the first selected venture, document where the $1,000 is held, how no more than $100 is made available, who can move/deposit funds, how receipts/costs/profit are recorded, and which customer-facing interface the manager will use. Build the generic main company page separately from the venture’s customer page. Do not buy tools or domains as a substitute for selecting the first venture’s actual needs. |
| 5 | Begin the first bounded venture | The CEO proposes and evaluates an idea using evidence, assumptions, costs, likely demand, expected revenue, and payback. A viable recommendation is not itself authority. | Start only after Kalaap has reviewed the synthetic evidence, the required operating and money-handling rules are recorded, and a bounded first-venture operating authorization names the permitted live actions and limits. Within that authorization, the CEO makes the venture funding decision and routine scoped customer/vendor contacts do not return for individual approval. |

## Finite testing finish line

Synthetic orchestration work is ready for Kalaap’s review when the reviewed commit has all of the following evidence:

1. One run shows the complete proposal, manager assignment, bounded task packets, synthetic worker results, manager aggregate, CEO recommendation, and review artifacts.
2. Every stage records synthetic-only execution, zero effect, no external action, and all nine live authorities denied.
3. Negative tests show that instruction-like content, unexpected authority fields, invalid worker types, malformed inputs, duplicate IDs, and excess work cannot widen scope.
4. Source inspection confirms the flow has no model/provider, network, credential, filesystem, subprocess, or queue integration.
5. The focused tests and one full repository regression have reproducible commands, exact denominators, and preserved raw results.

At that point the synthetic test work stops pending Kalaap’s review. Do not add provider tests, production probing, or repeated certification rounds to this finish line.

## Decisions still needed before first live venture

1. **Capital custody:** Where the $1,000 is held and how the CEO’s $100-per-venture limit is technically enforced.
2. **CEO-pool 50/50 rule:** The balance or inflow against which the 50% ceiling is calculated.
3. **After the $100 profit milestone:** Whether later saved 20% shares also return to the CEO pool.
4. **Stop rule:** Maximum duration and/or loss or performance threshold for stopping a venture. A 30-day limit has been discussed as a suggestion, not approved.
5. **Viability standard:** The minimum evidence and payback expectations for the CEO’s funding decision.
6. **Customer operations:** For the first selected venture, the customer offer, interface, contact channel, and any vendor needs.
7. **Domain choice:** Verify the purchased spelling and renewal terms before using it publicly; decide whether the company page needs a corrected domain. A venture-specific domain is not assumed.

## Separate items and boundaries

- The current synthetic flow is not a real CEO, manager, or worker deployment.
- All nine live authorities remain denied until an exact bounded operating authorization is separately made.
- No provider/network calls, customer/vendor contacts, spending, movement of funds, publishing, or deployment are authorized by this plan.
- The approved P12–P14 roadmap and its non-monetary limited-test proposal are separate from the path to a revenue-producing venture. This plan neither changes that roadmap nor treats the ctkfamily.com test target as part of this business path. Any roadmap replacement or phase change requires Kalaap’s explicit decision.
- The local synthetic orchestration evidence is not a decision that a gate is blocked, accepted, or production-ready.

## Immediate next actions

1. Kalaap reviews this plan and the current synthetic orchestration evidence.
2. Resolve the five money/viability/stop-rule choices needed for the first bounded venture.
3. Identify one candidate venture for CEO evaluation.
4. Specify only the customer and fund-handling infrastructure that candidate actually needs.
5. After review and separate authorization, run that venture within its recorded limits; evaluate it against the stop rule and profit record.

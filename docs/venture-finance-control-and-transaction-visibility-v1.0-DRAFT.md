# Venture Finance Control and Transaction Visibility — Draft Addendum

**Version:** 1.0
**Status:** Draft for Kalaap Das’s review
**Related plan:** [Cost-Conscious Path to the First Venture, v1.3](venture-to-first-profit-plan-v1.3-DRAFT.md)
**Purpose:** Record the required CEO/manager control model, minimum transaction visibility, and current API research. This addendum supplements v1.3 and does not change runtime code, authorize live use, or select a provider.

## Operating model

The project uses **one financial vendor and one designated account for the entire $1,000 pool**. Per-venture seed allocations, operating balances, 80/20 allocations, and the CEO pool are internal ledger entries, not separate financial accounts.

The CEO is responsible for the shared pool: it reviews proposals, determines viability, allocates no more than $100 of seed per venture, and may leave funds unallocated. A venture manager may request or initiate permitted operations only within its venture’s remaining budget and defined scope. It cannot raise its cap, use another venture’s allocation, or change pool policy. The CEO can freeze or revoke a manager’s financial permission.

Agent requests go through the project’s finance boundary. It must independently verify the actor, venture, amount, available balance, remaining cap, payee, operation type, idempotency key, and applicable policy before any provider call. The provider credential stays in the finance service. The finance service is a control point, **not a way to disguise agent activity or bypass a provider restriction**.

## Provider authorization rule

A vendor qualifies for agent-initiated transactions only when its official API, account terms, and applicable account eligibility permit disclosed transactions initiated by an AI agent acting for the business. API availability alone does not establish permission. Agent identity and transaction origin must be represented honestly. Do not use shared human credentials, browser automation, or an intermediary service to evade a provider’s access controls.

If no provider qualifies for agent-initiated payments, the minimum acceptable financial connection is **read-only API access to transaction activity and balance for the same designated account**. This supports monitoring and reconciliation, but it does not authorize payments. If neither permitted transaction initiation nor adequate read-only visibility is available, the provider does not meet the project’s requirements.

## Transaction visibility and settlement model

The system must preserve three distinct facts:

1. **Payment status:** pending, completed/settled, failed, refunded, disputed, reversed, or held, as supplied by the provider.
2. **Spendable funds:** the provider-reported available balance, distinct from pending receipts, withheld funds, and an internal ledger balance.
3. **Record freshness:** provider’s transaction/event time, provider’s last refresh time where available, and the time the project last retrieved the data.

A normal settlement delay is not itself an API failure. Pending or held receipts are not spendable and must not be treated as settled profit. Reconciliation must account for processing fees, refunds, disputes, reversals, payouts, and seed deposits. The system must mark missing, stale, or incomplete provider activity as unreconciled and must not infer a balance from model-generated content.

Minimum API evidence required during vendor qualification:

- read access to the account’s balance, including available and withheld amounts if provided;
- read access to the account’s transaction history, including deposits, receipts, fees, refunds, reversals, and payouts—not only card payments processed through that vendor;
- stable provider transaction IDs, timestamps, amounts, currency, event type, and status;
- documented pagination, historical range, refresh delay, and any API/account eligibility restrictions;
- an authorized read-only scope where available, separate from payment/write scopes.

If the vendor API exposes only processor sales or payout records and omits other activity in the same account, it is not complete account reconciliation. The finance service must preserve both the provider record and its own ledger entry and match them by provider ID/idempotency key; unknown activity remains unclassified until reconciled.

## Public API evidence reviewed

Research performed against official developer/support documentation on **2026-10-15**. This is product-documentation research only; no account or API was connected.

| Provider | Public evidence found | Limitation for this project |
|---|---|---|
| **PayPal** | The current PayPal API resource list includes Transaction Search for account history. A reporting API provides balance reads with a read scope. | The balance endpoint says data may take up to three hours to appear. That is usable for reconciliation, not necessarily a current spend-authorization check. PayPal’s documented payout API sends to PayPal or Venmo recipients; that may not support every supplier. Neither API documentation by itself confirms that PayPal permits this project’s AI-agent operating model. |
| **Square** | Square documents an API for linked bank-account details and APIs for payments/payouts. Square Checking supports account/routing details and inbound/outbound transfers through its account tools. | The public API evidence reviewed does not establish a complete transaction-history/balance feed for all activity in Square Checking, or agent-authorized payment initiation from that account. Payment and payout records alone are not the same as the full account statement. |
| **QuickBooks** | QuickBooks documents payment-processing and accounting APIs, as well as QuickBooks Checking and payments products. | The public API evidence reviewed does not establish that an external agent can read the complete QuickBooks Checking account activity directly or initiate bounded payments from that checking balance. Accounting records are not assumed to be a complete, timely bank-transaction feed. |
| **Stripe** | Stripe documents APIs for Stripe payment-balance transactions. | Those records concern Stripe balance activity. The normal Stripe payout model can rely on an external bank account; the reviewed documentation does not establish a simple one-account fit for holding and managing the whole project pool. |
| **Wise** | Wise Platform documents balance reads (available and reserved amounts) and balance statements containing deposits, withdrawals, conversions, card transactions, and fees. | The documentation is for Wise Platform; eligibility and authorization for this project to use those APIs with a Wise Business account are unverified. Card acceptance is unavailable to new Wise Business customers, so the first venture would need a supported alternative such as bank-transfer payments. Permission for AI-agent use remains unverified. |

Sources:

- PayPal API resource list: https://developer.paypal.com/api/rest/current-resources/
- PayPal balance reporting API: https://developer.paypal.com/api/transaction-search/v1/balances-get/
- PayPal Payouts API: https://developer.paypal.com/api/payouts
- Square Bank Accounts API: https://developer.squareup.com/reference/square/bank-accounts-api
- Square Checking transfers: https://squareup.com/help/us/en/article/7604-square-checking-transfers
- Square ACH Payments API: https://developer.squareup.com/docs/payments-api/take-payments/ach-payments
- QuickBooks Checking: https://quickbooks.intuit.com/business-banking/checking/
- QuickBooks Payments API: https://developer.intuit.com/app/developer/qbpayments/docs/learn/explore-the-quickbooks-payments-api
- Stripe Balance Transactions API: https://docs.stripe.com/api/balance_transactions
- Stripe Payouts documentation: https://docs.stripe.com/payouts
- Wise balance statements (transaction detail): https://docs.wise.com/api-reference/balance-statement
- Wise balance API (available and reserved amounts): https://docs.wise.com/api-reference/balance
- Wise card-acceptance availability: https://wise.com/help/articles/6mRjhCgInCCeqnmayx4OrV/can-my-business-type-accept-card-payments

## Current conclusion

**No provider is qualified yet.** For read-only transaction visibility, Wise Platform currently has the strongest documented account-level statement coverage: its balance statement API describes deposits, withdrawals, conversions, card transactions, and fees, and its balance API distinguishes available and reserved amounts. But this is Wise Platform documentation; access for an ordinary Wise Business customer and for this project is not established, and card acceptance is unavailable to new Wise Business customers. PayPal has a clearly documented account transaction-history API and balance-report API, but its balance data may lag by up to three hours and its documented payout API targets PayPal or Venmo recipients. The evidence reviewed does not establish that any of the candidates permits the autonomous CEO/manager agent to initiate transactions under the one-account model.

The first venture’s offer and supplier-payment needs remain necessary inputs: they determine whether customers can pay through the one selected vendor and whether vendors can be paid using that same provider. Selection also requires checking the provider’s current AI-agent terms and eligibility, not merely pricing and API availability.

## Verification evidence required before an account connection

A later implementation must demonstrate with synthetic fixtures or provider sandbox only, before any live account is considered:

- complete transaction pagination and stable de-duplication by provider transaction ID;
- correct handling of pending, settled, failed, held, refunded, disputed, and reversed events;
- separation of provider available balance, internal ledger balance, and stale/unreconciled state;
- accurate ingestion of seed deposits, customer receipts, fees, expenses, and payouts;
- no cross-venture attribution or spending beyond the manager’s authorized venture limit;
- fail-closed behavior when the feed is stale, incomplete, unavailable, or inconsistent;
- auditable CEO/manager attribution and accurate AI-origin labeling;
- documented provider permission for the intended agent use and API scopes.

## Boundaries

This is a documentation addendum only. It does not choose a vendor, decide unresolved pool or venture policy, mark a project gate accepted or blocked, change phase status, connect an account, make provider API calls, move money, contact customers or suppliers, publish, deploy, or enable any live authority. All nine live authorities remain denied. Kalaap Das remains the final reviewer and decision-maker.

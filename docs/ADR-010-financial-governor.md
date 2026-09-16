# ADR-010: Financial governor and simulated payment boundary

## Status

Accepted — P0.9.

## Decision

No agent receives banking credentials. P0.9 exposes only a local simulated payment adapter
behind broker-approved operations. Capital allocation is checked atomically against both
the portfolio deployable ceiling and the separate new-venture ceiling. If eligible
treasury balance shrinks below deployed capital, new allocations freeze without clawing
back existing allocations. Available profit is computed after refunds, chargebacks, tax
reserves, liabilities, and infrastructure/inference costs; the resulting profit is swept
to treasury.

Opex and capex categories are explicit allowlists. Unlisted categories are denied.

## Consequences

P0.9 proves financial mechanisms without real payment execution. Real stakes remain outside
this increment and are reserved for later certification.

# ADR-009: Atomic multi-level compute budgets

## Status

Accepted — P0.8.

## Decision

Every model, search, browser, subprocess, and spawn request is admitted only after the same
cost unit is available simultaneously in the agent, venture, experiment, model, hourly,
daily, and global windows. Admission and debit occur under one lock, so a request rejected
at any level consumes nothing at any other level. The global ceiling is enforced at the call
boundary, not through periodic reconciliation.

This increment uses deterministic in-memory windows for mechanism certification. Durable
compute accounting remains tied to the authoritative ledger integration.

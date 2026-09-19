# ADR-P3-003 — Voyage Scout Scoring and Lifecycle

**Status:** Proposed for P3.2 review
**Date:** 2026-09-19

## Decision

P3.2 uses a deterministic, versioned weighted score for shadow Voyage
Candidates. Weight set p3.2-w1 is frozen at:

| Factor | Weight |
|---|---:|
| Opportunity fit | 0.35 |
| Thesis fit | 0.25 |
| Market signal | 0.25 |
| Risk adjustment | 0.15 |

The score is on a 0–100 scale. The acceptance-review threshold is 70. A
score at or above 70 is eligible for human review; it is never an automatic
acceptance. The threshold is intentionally conservative for a synthetic
reasoning gate: it requires a strong opportunity/thesis baseline plus favorable
market and risk inputs before a human reviewer is asked to consider acceptance.

## Uncertainty

The base confidence interval is score plus or minus 10 points, clamped to
0–100. Tainted input adds 5 points of uncertainty. Contradictory signal IDs
add 15 points. The resulting confidence label is high through 10 points,
medium through 20, and low above 20. The interval and every factor
contribution are retained in the candidate reasoning chain.

## Lifecycle

Candidates move through INTAKE → SCORED. A human operator may move SCORED to
ACCEPTED, REJECTED, or QUARANTINED. System expiry moves an old INTAKE or
SCORED candidate to EXPIRED. Contradictory signals are quarantined, and a
second quarantine emits an escalation marker. Terminal REJECTED and EXPIRED
states cannot be reopened; ACCEPTED can only move to QUARANTINED.

## Authority

Scout can recommend and record shadow state only. It cannot accept its own
candidate, create ventures, spawn workers, request capital, execute payments
or brokers, access credentials, deploy, contact customers, or perform any
external action. Human acceptance is a review record, not venture or capital
authorization.

Changing weights or threshold requires a new weight-set version and a new
P3.2 implementation-plan version. Existing candidate records retain their
weight version and reasoning snapshot; retroactive recalculation is denied.

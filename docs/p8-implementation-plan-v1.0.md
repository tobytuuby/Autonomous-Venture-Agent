# P8 Limited Pilot — Implementation Plan

## Status

P8 planning and implementation are authorized on 2026-09-24. The authorized implementation is P8.0 synthetic preflight and charter validation. No live action is enabled.

## Increment 0 — Entry and charter contract

Record P8 entry, preserve the P7.6 synthetic certification boundary, and define the mandatory pilot charter fields and separate live-action approval gate.

## Increment 1 — Synthetic pilot preflight

Implement a standard-library-only validator that requires exactly one venture, one authority class, an ordered operating window, numeric exposure/loss ceilings, named approvers, monitoring, reconciliation, automatic stops, and pending written live-action approval.

## Increment 2 — Denial and recovery controls

Reject live authorities, live credentials, model authorization, invalid ceilings, malformed windows, incomplete controls, multiple ventures/classes, and changed charter identity. Record a synthetic automatic stop and deny all subsequent preflight validation.

## Increment 3 — Evidence

Run focused P8.0 tests and the full repository regression. Preserve source hashes, schema validation, test inventories, boundary fingerprints, zero-action counts, and a technical/governance report.

## Deferred increments

P8.1 first controlled live action, P8.2 live monitoring, P8.3 live recovery/wind-down, and P8.4 pilot certification require a completed charter and separate written live-action approval. They are not implemented or executed here.

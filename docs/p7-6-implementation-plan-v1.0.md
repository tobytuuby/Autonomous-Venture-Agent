# P7.6 Independent Certification — Implementation Plan

## Plan status

Implementation authorized by Kalaap Das on 2026-09-24. The implementation is limited to a read-only certification harness, focused tests, and audit evidence. No runtime authority is enabled.

## Increment 1 — Certification contract

Define the P7.6 policy, entry decision, test/evidence plan, and independent-decision separation. Preserve P7.5 as the audited predecessor.

## Increment 2 — Read-only repository audit harness

Implement a standard-library-only auditor that verifies Git lineage, required P7.5 artifacts, denominators, envelope hashes, manifest fields, source/test inventories, schema validity, runtime-log counts, and the synthetic-only boundary.

## Increment 3 — Static boundary inspection

Parse the P7.5 worker source and reject forbidden external-I/O, process, network, or credential imports and calls. Enumerate the four P7.5 focused test methods directly from the test AST.

## Increment 4 — Focused certification tests

Add focused tests for artifact/commit lineage, 93-case coverage, manifest boundary controls, inventory/schema integrity, runtime-log counts, static source restrictions, and non-authorizing decision status.

## Increment 5 — Evidence and review packet

Run the P7.6 focused suite and authoritative full regression. Preserve the audit JSON, logs, source/test inventories, hashes, technical implementation report, governance assessment, and independent review decision template. Keep implementation, evidence, review, and acceptance commits separately identifiable.

## Forbidden shortcuts

Do not replace direct repository inspection with bridge-generated claims, treat a passing audit as live authorization, modify P7.5 runtime code, attach a real CEO, create a runnable worker, or begin P8.

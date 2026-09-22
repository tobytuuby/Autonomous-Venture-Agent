# P7.4 Remediation Decision

**Date:** 2026-09-22  
**Branch:** phase7/p7-4-credential-provider-boundary  
**Status:** REMEDIATION IMPLEMENTED — EXECUTION AND INDEPENDENT REVIEW PENDING

## Resolved design decisions

1. Prior secret values are intentionally not recoverable. Rotation removes the old secret from the in-memory custody map.
2. Lineage retains opaque handles plus non-secret metadata: version, predecessor handle, UTC creation timestamp, and SHA-256 material fingerprint.
3. Provider registration and credential creation require `synthetic-operator`. Rotation and revocation retain the same requirement.
4. No live credential, provider, external action, or authority is enabled.

## Required closeout

The remediated focused suite and full regression must be executed from this branch. The evidence generator now derives source hashes from the checked-out files. An independent reviewer must verify the generated packet against the exact implementation commit before P7.4 can be accepted. P7.5 remains blocked.

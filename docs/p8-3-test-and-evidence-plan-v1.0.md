# P8.3 Test and Evidence Plan

## Focused denominator

The focused suite contains 12 test methods covering:

1. valid synthetic freeze record;
2. bounded revoke, quarantine, and wind-down records;
3. restore and rollback denial;
4. all nine authority drift denials;
5. action, credential, and model drift denial;
6. unknown charter denial;
7. charter scope mismatch denial;
8. schema false-authority enforcement;
9. terminal-state protection;
10. replay idempotency and collision denial;
11. injected-failure terminal containment;
12. automatic-stop and malformed-input fail-closed behavior.

## Evidence requirements

Preserve focused and full-regression logs, schema validation, source/test inventories, request hashes, all-false authority fingerprints, resulting-state decisions, zero external/unauthorized/live-credential counts, execution_performed=false, and source import inspection.

The evidence describes synthetic state records only. It must not be interpreted as live recovery, live wind-down, production readiness, or authority to begin P8.4.

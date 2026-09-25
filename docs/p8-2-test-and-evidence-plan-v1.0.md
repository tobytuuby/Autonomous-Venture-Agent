# P8.2 Test and Evidence Plan

## Focused denominator

The focused suite contains 10 test methods covering:

1. valid synthetic observation;
2. all nine authority drift fields quarantine;
3. action, credential, and model drift quarantine;
4. unknown charter denial;
5. charter scope mismatch denial;
6. schema false-authority enforcement;
7. exposure and loss ceiling quarantine;
8. replay idempotency and collision failure;
9. automatic stop fail-closed behavior;
10. non-synthetic and malformed numeric inputs quarantine or denial.

## Evidence requirements

Preserve focused and full-regression logs, schema validation, source/test inventories, observation and finding hashes, approved charter binding, quarantine reasons, all-false authority fingerprints, zero external/unauthorized/live-credential counts, and source import inspection.

A P8.2 observation or quarantine finding is not evidence of live monitoring, live action, or production authorization.

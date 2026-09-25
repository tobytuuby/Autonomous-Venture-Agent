# P8.1 Test and Evidence Plan

## Focused denominator

The remediation-focused suite contains 11 test methods covering:

1. valid request is denied without effect;
2. each of the nine live authorities is denied;
3. live credentials and live mode are denied;
4. model output and approval-like model text are denied;
5. non-synthetic execution class or effect is denied;
6. execution method always raises;
7. replay is idempotent;
8. unknown charter hash is denied;
9. request venture scope must match the approved charter;
10. automatic stop is terminal;
11. JSON schema requires all nine authorities and rejects any true value.

## Required evidence

Preserve:

- focused runtime log and exact method denominator;
- full-regression log and exact post-change denominator;
- source/test/schema inventories with Git SHA and SHA-256;
- approved charter registry binding evidence;
- schema validation result;
- request and result hashes;
- authority fingerprint showing all nine false;
- external_action=0, unauthorized_action=0, live_credential=0;
- no-I/O/process source inspection;
- technical and governance review records.

A passing P8.1 synthetic denial test is not evidence of live execution, production readiness, or live authorization.

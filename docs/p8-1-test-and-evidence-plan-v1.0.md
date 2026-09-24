# P8.1 Test and Evidence Plan

## Focused denominator

The focused suite contains 8 test methods:

1. valid request is denied without effect;
2. each of the nine live authorities is denied;
3. live credentials and live mode are denied;
4. model output and approval-like model text are denied;
5. non-synthetic execution class or effect is denied;
6. execution method always raises;
7. replay is idempotent and material collision fails closed;
8. automatic stop is terminal and result fingerprints remain denied.

## Required evidence

Preserve:

- focused runtime log and exact method denominator;
- full-regression log and exact post-change denominator;
- source/test/schema inventories with Git SHA and SHA-256;
- request and result hashes;
- authority fingerprint showing all nine false;
- external_action=0, unauthorized_action=0, live_credential=0;
- no-I/O/process source inspection;
- technical and governance review records.

A passing P8.1 synthetic denial test is not evidence of live execution or live authorization.

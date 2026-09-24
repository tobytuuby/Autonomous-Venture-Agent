# P7.6 Test and Evidence Plan

## Binding denominator

P7.6 reports:

- 6 focused certification test methods;
- 17 independently evaluated audit checks;
- inherited P7.5 denominator: 81 authority + 12 recovery = 93 envelopes;
- the authoritative full repository regression count observed after P7.6 test addition.

A missing, duplicate, or failed P7.5 case remains a P7.6 certification failure.

## Focused checks

The six methods must cover:

1. required artifacts and Git commit lineage;
2. 93-case denominator, envelope dispositions, and evidence hashes;
3. manifest denominators, zero counts, and boundary flags;
4. source/test inventory hashes, focused-method inventory, and schema validity;
5. runtime log counts and no external-I/O/process constructs;
6. non-authorizing certification status.

## Evidence requirements

The packet must preserve:

- P7.6 audit JSON with every check and finding;
- focused runtime log;
- full-regression log;
- source and test inventories with Git blob SHA and SHA-256;
- audited commit and P7.5 evidence source commit;
- exact case IDs and recomputed envelope hashes;
- technical implementation report;
- non-technical governance assessment;
- independent review decision.

All artifacts must remain synthetic-only, effect-free, and free of credentials or external actions. A PASS result must remain pending separate human independent acceptance.

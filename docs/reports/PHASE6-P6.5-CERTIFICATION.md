# P6.5 End-to-End Technical Certification

Status: ACCEPTED — SYNTHETIC-ONLY SCOPE

Source commit: `76a648a9a1c044921f492d02eda357353421807f`
Predecessor acceptance: `P6.4-ACCEPTED` at `3d32dc1010f4eba8c5e63d9be1d0e369a33cf752`
Locked configuration fingerprint: `8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11`

## Implemented composition

`kernel/p6/certification.py` adds `SyntheticPortfolioCertification`, which composes:

- P6.0 portfolio registry with two memberships: `venture-a` and `venture-b`;
- P6.1 coordination packets routed separately to each venture;
- one stateless `metadata-read` shared service;
- P6.3 aggregate anomaly analysis over the two outputs;
- P6.4 selective quarantine/recovery for venture-a;
- synthetic harvest and reinvestment proposal records for venture-b.

The report exposes only the registry's read-only aggregate view. Venture-private metadata is not included.

## Verified bridge execution

| Scope | Command result |
|---|---|
| Focused P6.5 | 12/12 passed, exit 0 |
| Combined P6.0–P6.5 | 116/116 passed, exit 0 |
| Full repository | 337/337 passed, exit 0 |

Raw records:

- `tests/certification/p6-5-raw/P6-5.json`
- `tests/certification/p6-5-raw/p6-regression.json`
- `tests/certification/p6-5-raw/full-regression.json`

The full run emitted six pre-existing unclosed-SQLite `ResourceWarning` messages. No failures or errors occurred.

## Composition observations

- Portfolio member count: 2.
- Shared-service outputs: 2.
- Finding: `CROSS_VENTURE_LEAKAGE`, status `QUARANTINED`.
- Operation statuses: `QUARANTINED`, `RECOVERED`, `HARVEST_RECORDED`, `PROPOSAL_ONLY`.
- All nine live-authority fields: false.
- External action: false.
- Capability granted: false.
- Execution requested: false.
- Report hash: `6961d5d04fde96a11106d714cafa55c2482f60f048814d995c145b0434a442ad`.

## Source hashes

- `kernel/p6/certification.py`: `dfbc5251d8a1672bedd108e4f300c9caf27f6cab6d30d356f5ae4b69aeaca4a5`
- `kernel/p6/__init__.py`: `c89cd584bfa9e73501363971b8cdecc6454ae4bfe38944525930da384ed6ffb7`
- `tests/p6/test_p6_5_certification.py`: `0d772e8eb137b2cb5d355e7011bdf320b810a854eb6de7e04e1ecf1e730eac11`
- `phase6-policy-spec-v1.6.md`: `7bc83a120236e55d131ca246cf72ec4d5c3e581681ea67e3f736f80e0024119b`
- `phase6-implementation-plan-v1.6.md`: `a80af34be55289f6ad157d4fa098c153b59fd50fafc991659c2ead6e8993995a`
- `docs/p6-5-implementation-authorization.md`: `0121f390298a80d2887ccd41647376995480a3d66b97abafa53893e4da7966ff`

## Limitations

This certifies synthetic composition only. It does not certify provider access, production readiness, external actions, live capital, real ventures, or workers. P6.5 was formally accepted on 2026-09-21 against evidence-complete commit `89b2399291a48393c6ec3b1092b3b202e3fbfe68`; tag `P6.5-ACCEPTED` records closure. P7 has not started.

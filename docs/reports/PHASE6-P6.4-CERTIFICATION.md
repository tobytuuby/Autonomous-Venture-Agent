# P6.4 Hardening Technical Certification

Hardening commit: 0f5b0f56b9d021760dc19a1d3dcebd9ade7842dc
Prior evidence commit: f7b790d5039954e5fdd038971d50d88d03564f45
Locked fingerprint: 8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11

The implementation now verifies direct grant-revocation parent existence, parent integrity, and parent scope; requires portfolio context for freeze inspection; verifies recovery candidates through replay; and explicitly validates quarantine output against the operation schema. The schema conditionally requires parent_action_id for grant revocation and validates core field types.

Verified bridge results at the hardening commit:

- Focused P6.4 hardening: 36/36 passed.
- P6.0-P6.4 regression: 104/104 passed.
- Full repository regression: 325/325 passed.
- All commands exited 0.

Six pre-existing unclosed-SQLite ResourceWarning messages occurred during the full repository regression; they did not affect exit status or test results. No provider, network, credential, payment, broker, customer, deployment, capital, venture, or worker execution exists. All nine live-authority fields remain denied.

This evidence was formally accepted on 2026-09-20 at verified source state 3d32dc1010f4eba8c5e63d9be1d0e369a33cf752. The P6.4-ACCEPTED tag records closure. P6.5 is unblocked for separate planning authorization but has not started.

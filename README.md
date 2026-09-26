# Autonomous Venture Agent

The Autonomous Venture Agent is a policy-first system for synthetic, shadow, and isolated pre-production experimentation. Its repository records policy boundaries, deterministic kernels, schemas, tests, and audit evidence for each project phase.

## Current accepted baseline

The `main` branch contains accepted work through P8.2 for synthetic observation and quarantine scope:

- P7.6: synthetic certification boundary accepted.
- P8.0: synthetic pilot preflight accepted.
- P8.1: synthetic controlled-action denial boundary accepted after schema and charter-binding remediation.
- P8.2: synthetic monitoring and reconciliation boundary accepted for observation-only scope.
- Full regression on the P8.2 baseline: 428/428 passed.

## Safety boundary

The repository does not authorize live operation. The following remain denied:

- Real CEO or worker attachment
- Live credentials
- Network, provider, broker, payment, customer, capital, deployment, venture, or external actions
- Production rollout
- Model output as execution authority
- P8.3, P8.4, P9, and P10

P8.2 only consumes supplied synthetic observations and creates in-memory observation or quarantine findings. It does not poll external systems or execute actions.

## Branch and acceptance workflow

Accepted work is merged into `main` only after independent review and explicit acceptance. New phase work is developed on a feature branch and remains out of `main` until accepted.

The current phase branch is:

```text
phase7/p7-4-credential-provider-boundary
```

This separation keeps `main` as the accepted, auditable baseline and prevents unaccepted phase work from being treated as authorized.

## Repository layout

- `docs/` — policy specifications, implementation plans, entry decisions, and reports
- `kernel/` — deterministic policy and boundary implementations
- `schemas/` — JSON Schemas for phase contracts
- `tests/` — focused and regression tests
- `tests/certification/` — runtime logs, manifests, inventories, and evidence packets
- `infrastructure/` — infrastructure boundary documentation

## Verification

From the repository root:

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

Focused P8 tests:

```bash
python3 -m unittest tests.p8.test_p8_0_pilot_gate tests.p8.test_p8_1_action_gate tests.p8.test_p8_2_monitor
```

All phase claims must be verified against committed source, schemas, tests, hashes, runtime logs, and Git history.

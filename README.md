# Autonomous Venture Agent

The Autonomous Venture Agent is a policy-first system for synthetic, shadow, and isolated pre-production experimentation. Its repository records policy boundaries, deterministic kernels, schemas, tests, and audit evidence for each project phase.

## Current accepted baseline

The accepted `main` baseline includes P8.4 synthetic pilot certification and closeout only.

- P8.0–P8.4: accepted for synthetic pilot certification and closeout.
- P8.4 merge: `0f8df0f00f15207afdf7bfe74bb466aa3d6dd386`.
- P8 combined focused tests: 59/59 passed; full regression: 453/453 passed.
- P9 synthetic boundary hardening is in progress on `phase9/p9-synthetic-boundary-hardening`; it is not accepted yet.

## Safety boundary

The repository does not authorize live operation. The following remain denied:

- Real CEO or worker attachment
- Live credentials
- Network, provider, broker, payment, customer, capital, deployment, venture, or external actions
- Production rollout
- Model output as execution authority
- Any P10 work

P9 is limited to supplied synthetic records and in-memory evaluation. It does not poll external systems or execute actions. All nine live authorities remain denied.

## Branch and acceptance workflow

Accepted work is merged into `main` only after independent review and explicit acceptance. New phase work is developed on a feature branch and remains out of `main` until accepted.

The current implementation branch is:

```text
phase9/p9-synthetic-boundary-hardening
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

Focused P9 tests:

```bash
python3 -m unittest tests.p9.test_p9_synthetic_boundary
```

All phase claims must be verified against committed source, schemas, tests, hashes, runtime logs, and Git history.

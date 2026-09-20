# Phase 6 Policy Specification v1.2 — P6.2 Addendum

Status: adopted for P6.2 implementation. No live-authority change.

This addendum extends PORT-604 bounded coordination with synthetic shared-service demand while preserving identity, isolation, kernel ownership, provenance, fail-closed authority, and evidence separation requirements.

## P6.2 policy decisions

- Demand is a typed, kernel-owned record and is not an authority grant.
- Demand must name exactly one registered portfolio, one registered venture, and one originating coordination request.
- Service classes and per-demand quota maxima are explicit configuration inputs.
- Eligibility is deterministic and fail-closed.
- The runner is stateless and effect-free; it has no provider, network, credential, queue, or ambient authority.
- Outputs must attribute portfolio, venture, demand, coordination request, service class, units, provenance, lineage, taint, policy, and fingerprint.
- Exact replay of the same demand must converge to the same output hash.
- Cross-venture mutable state and unbounded quota are prohibited.
- All nine live-authority fields remain false/denied.
- P6.2 evidence is separate from P6.1 and must include raw output and independent technical/non-technical assessments.

## Recovery rule

A failed invariant prevents execution, records a deterministic reason and evidence hash, and quarantines the demand when evidence retention is required. Recovery may only replay an accepted synthetic demand and may not widen scope, quota, or authority.

# OR-0.7.1 — uv release provenance verification (partial; STOP)
Date: 2026-10-28
Target: Autonomous Venture Agent, venture-control and venture-agents
Version: uv 0.13.5 (upstream GitHub release 0.13.5)
Platform: x86_64-unknown-linux-gnu
Status: **STOP — release archive digest verified, cryptographic attestation verification not yet completed. No binary installed or executed.**

## Approved contract and prior baseline
OR-0.6 accepted in audit. Reference: `docs/operational-readiness/OR0.6-installation-execution-contracts-v1.0.md`.
Checked `~/.local/bin/uv` on both VMs; neither contained an existing executable at that path. Control repository HEAD at start: `c6aa359e5f1ba950f66fac7855e4d55495d3b382`.

## Official artifact evidence
- Repository: https://github.com/astral-sh/uv
- Release: https://github.com/astral-sh/uv/releases/tag/0.13.5
- Asset: `uv-x86_64-unknown-linux-gnu.tar.gz`
- URL: https://github.com/astral-sh/uv/releases/download/0.13.5/uv-x86_64-unknown-linux-gnu.tar.gz
- Release API: https://api.github.com/repos/astral-sh/uv/releases/tags/0.13.5
- GitHub release asset metadata digest: `sha256:f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f`
- Downloaded on venture-control to `/tmp/or071-uv/uv-x86_64-unknown-linux-gnu.tar.gz` using HTTPS and a bounded curl timeout.
- Locally computed SHA-256: `f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f` — **MATCH**.
- Tar listing (read-only): `uv-x86_64-unknown-linux-gnu/uv`, `uv-x86_64-unknown-linux-gnu/uvx`. No extraction was performed.

## Attestation status
Queried GitHub's artifact-attestation endpoint:
`https://api.github.com/repos/astral-sh/uv/attestations/sha256:f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f`.
Response: HTTP 200, **2 attestations** returned. This demonstrates GitHub advertises attestation bundles for the exact digest. **It is not equivalent to cryptographic verification of the signatures, signing identities, or trusted roots**. The signed bundle was not verified locally; no `gh` executable was present on either inspected VM. Do not commit temporary signed bundle URLs or unredacted API responses.

## Stop decision and safe next action
OR-0.7.1 contract explicitly requires trusted artifact provenance before extraction and execution. **Stop before installing or invoking uv**. No sudo, packages, system Python changes, service restarts, paid API calls, payment activity, or agent/CEO authority changes occurred.

Next narrowly scoped action: use a trusted, versioned GitHub attestation verifier or an independently verified equivalent available without executing the uv archive, validate signatures and repository identity against upstream, then continue with verified extraction into user-local `~/.local/bin/uv` on both VMs, compare `uv --version`, and commit sanitized evidence. If verification cannot be accomplished under existing FOSS constraints, report the precise blocker and do not install.

**Stage classification:** artifact fetched and hash verified on control VM; no attestation cryptographic verification, no installation on either VM, no runtime validation. OR-0.7.1 NOT ACCEPTED.

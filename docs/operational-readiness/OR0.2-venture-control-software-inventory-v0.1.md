# OR0.2 — Venture-Control installed software and supporting service inventory
Date: 2026-10-28
Source commit before inspection: a28cba912e48e17333043474458959823404a8ac
Host: venture-control (read-only inspection over existing authorized bridge)
Status: CONTROL-SIDE INVENTORY RECORDED; overall OR-0 NOT READY

## Method and limitations
Read-only host commands inspected operating system identity, executable paths and versions, Python distribution metadata, selected systemd service state, repository manifests, and the dynamic provider-loader source. No privileged configuration file, secret value, keys, logs with sensitive content, or runtime databases were read. No installation, change of authority, service restart, paid AI call, or payment was performed. This is not a security audit, complete OS package bill of materials, or deployment acceptance.

## Verified host/platform
- Hostname: `venture-control`
- OS: Ubuntu 26.04.1 LTS, code name resolute; x86_64
- Python: 3.14.4, `/usr/bin/python3`
- Node: v20.20.2, `/usr/bin/node`
- npm: 10.8.2, `/usr/bin/npm`
- Git: `/usr/bin/git`
- PostgreSQL executables: `/usr/bin/psql`, `/usr/bin/pg_dump`, `/usr/bin/pg_restore`; all report PostgreSQL 18.6 (Ubuntu 18.6-0ubuntu0.26.04.1)
- Supporting executables detected: `/usr/bin/apt-get`, `/usr/bin/dpkg-deb`, `/usr/bin/ssh`, `/usr/bin/openssl`, `/usr/bin/systemctl`, `/usr/bin/curl`
- `chromium` and `chromium-browser` not resolved in inspected system PATH; this does NOT prove browser absence in workspace-local Playwright cache.
- Python import distribution metadata (system Python): `cryptography==46.0.5`, `jsonschema==4.19.2`, `psycopg==3.3.2`, `requests==2.32.5`; `playwright`, `pytest`, `pip` distributions not found using this metadata check (virtual environments not inventoried).
- Existing dependency declaration `requirements-owner-approval.txt` requires `cryptography>=3.4`, which is satisfied by observed system package version; no package pin chosen yet.

## Runtime/services observed
- `venture-control-broker.service`: active; enabled.
- `postgresql.service`: active; enabled.
- `venture-control-bridge.service`: active at inspected time.
- `venture-ceo-shadow.service`: disabled (service unit present; NOT evidence of active autonomous CEO inference).
- `opa.service` and `openbao.service` unit definitions exist and appeared enabled in service-unit listing. Necessity, executable versions, actual healthy service state, policies and secret-provider integration NOT verified by this inventory.
- Existing systemd units also include CEO scheduled exercise, authenticated handoff, preparation control, PostgreSQL backup and ledger checkpoint; presence of units is not evidence that those journeys have passed in production.
- Working repository at inspection: `a28cba9` with existing unrelated dirty source and untracked runtime/certification evidence; all preserved.

## Dynamic provider module and import chain
`agents/ceo/provider_dispatch.py` uses `importlib.util.spec_from_file_location` to load `ventures/venture-001/runtime/provider_manager.py` through the runtime-root path. This is the existing *repository runtime module*, not proof of a separately installed third-party provider plugin.

`provider_manager.py` imports the local `manager` module, `agents.ceo.venture_exercise.configured_provider`, `agents.ceo.gates`, `agents.ceo.provider` and Python standard-library modules. Its configured OpenAI-compatible HTTP model adapter and environment/deployment wiring still require configuration verification. Do not read or publish credentials. Indirect dependencies and environment-provided override paths must be assessed before OR0.5 version lock. This chain does not, by itself, prove working live provider execution on either VM.

## Required control-side capabilities and remaining evidence
| Capability | Finding | Follow-up |
| --- | --- | --- |
| Python core execution | Python 3.14.4 observed | verify project-specific environments/import smoke tests |
| Crypto and JSON validation | cryptography/jsonschema versions observed | OR0.4 licenses; OR0.5 compatibility |
| Database | PostgreSQL client tools 18.6 and active server unit | server schema/access, version alignment and restore smoke in OR0.10–11 |
| PostgreSQL Python access | psycopg 3.3.2 observed | safe local connection test with nonsecret configuration later |
| Model HTTP access | requests observed; OpenAI-compatible adapter source exists | approved nonbillable configuration checks; no paid inference before spending gate |
| Systemd supervisor | systemctl available, selected services active | controlled health/service-env inventory; no service modifications |
| Broker and signing | broker active; source signing code exists | auth/permissions/trust test without secret exposure |
| Backup/recovery | pg_dump/pg_restore and scripts exist | verify backup destination/restore behavior in later OR-0 gates |
| Node/browser tooling | Node/npm present; global chromium not found | control-side workspace cache audit; agent-side browser acceptance belongs to OR0.3/OR0.9 |
| OpenBao / OPA | units exist | determine whether required in active design and verify health/version |
| FOSS compliance | not assessed by OS/package inspection | OR0.4 |
| Complete versions/compatibility | incomplete | OR0.5 |

## Acceptance and provenance
Inspection was read-only; commands and observed versions were recorded in this sanitized report for GitHub review. No confidential OS environment, credentials, runtime DBs, or token-bearing logs are included. Claude can independently inspect the source paths but cannot directly validate the VM status without VM access.

**OR0.2 assessment:** Control VM preliminary installed-software inventory recorded. Version-specific requirements and limited observable service state captured. Remaining host health/permissions and package/license validation go to OR0.4, OR0.5, OR0.10–11; do not label overall OR-0 READY.

**Next predefined task:** OR0.3 Venture-Agents installed-software inventory.

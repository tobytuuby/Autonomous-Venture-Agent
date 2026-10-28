# OR0.1 — Full-lifecycle software dependency discovery (initial inventory)
Date: 2026-10-28
Baseline: 98a4396cceb5972c38f6638bb3e58314ca15a8c1
Classification: repository-derived requirements and limited read-only VM observations.
Status: OR0.1 SOURCE INVENTORY COMPLETE; NOT a software-readiness certificate.

## Scope and method
Reviewed operational viability plan v2.4, repository directory/package/service manifests, a Python AST import sweep of agents/, broker/, kernel/, ventures/, tests/, infrastructure/ and integrations/, and short read-only commands on each VM. The AST sweep read 247 Python files, with 2 parse failures; it is not a complete import/dependency lock analysis. Existing dirty worktree and untracked runtime evidence were not modified. No packages installed, no policy changed, no paid provider calls.

## Capability-to-software matrix (required, not proof of installation)

| Plan capability | Software/runtime or dependency to verify | Expected execution host | Evidence / verification pending |
| --- | --- | --- | --- |
| CEO decisions, scheduling, cost accounting (A–C,E) | Python 3, systemd, HTTP/TLS client, JSON/schema checks, model provider transport | control | `agents/ceo/`, `infrastructure/systemd/`; deployed versions pending OR0.2 |
| Signed delegation, trust, approvals (A–C) | Python cryptography, trust stores, filesystem permissions, broker transport | control and agents | `agents/ceo/service_identity.py`, `authenticated_handoff.py`, `kernel/`; remote auth smoke test pending |
| Manager and workers (A–D) | Python runtime, sandbox/OS process isolation, selected FOSS developer tools | agents | `ventures/venture-001/runtime/`; deployed agent-side services NOT verified |
| Durable state and finance (B,C,E) | PostgreSQL, psycopg driver, SQLite stdlib, backup tooling | control; apps as explicitly designed | `kernel/finance/`, `kernel/`, database and backup scripts; version and restore verification pending |
| Policy and secrets (B,E) | OpenBao/OPA only if referenced by active code and operating design | control | `infrastructure/systemd/openbao.service`, `opa.service`; necessity and installation status TBD |
| Online product engineering (D) | Python app server/framework as chosen by existing app contracts, Node/npm for JS builds, FOSS web/TLS stack, persistent storage | agents private staging; approved public host TBD | `ventures/venture-001/`; no new framework selected until contract review |
| Browser customer-journey tests (D,F) | Node.js, npm, Playwright package/browser, Chromium and OS shared libraries | agents | `artifacts/venture-001-browser/package.json` and `package-lock.json` found on control; browser install on agents unverified |
| Finance/payments (E,F) | PayPal API HTTP/TLS client, webhook validation, ledger and reconciliation libraries | control authorization; approved payment execution scope TBD | `kernel/finance/payment_path.py`; sandbox-only software prerequisites, not live proof |
| Monitoring, restoration, deployment (A–F) | systemd/journald, Git/SSH, DB backup tools, log sanitization, versioned install/deployment scripts, rollback | both | `infrastructure/`; full tooling and permission checks pending |
| Testing, audit and evidence (all) | Python unittest, jsonschema, cryptography, psycopg where used, Node browser runner, hash/diff utilities | both appropriate hosts | `tests/`, `tests/certification/`; deterministic suites exist; VM smoke results pending |

## Observed imports and manifests
- AST scan: 247 Python files read; 2 failed parse. Most frequent non-stdlib/external candidates: `jsonschema` (21 references), `cryptography` (19), `psycopg` (2). `unittest` and `sqlite3` are Python standard library. Presence of import text alone does not confirm installation or runtime necessity.
- Found `requirements-owner-approval.txt` at repository root and under a local artifact candidate. Do not claim there is no requirements file.
- Found `artifacts/venture-001-browser/package.json` and `package-lock.json` in the current workspace; their tracked status, contents, versions, and relevance to agent-side install require verification. Do not claim there is no Node manifest.
- Found systemd unit files for CEO shadow, broker, authorized handoff, preparation control, scheduled exercise, PostgreSQL backups, ledger checkpoint, OPA and OpenBao. A unit file does not prove a running service.
- No blanket `pip install`, npm install, package additions, privileged changes, or FOSS-license conclusions were performed.

## Limited read-only runtime observations
- venture-control: Git baseline 98a4396 at start; previously observed Python 3.14.4, active PostgreSQL and control broker; actual package versions, executable dependencies, service configs, and security boundaries are to be captured in OR0.2.
- venture-agents: Python 3.14.4 and Node executable were seen. `command -v` did not resolve npm/Chromium/Playwright/psql/git in one observation (PATH and command checks need independently confirmed), and no current manager/worker service deployment has been verified. Capture exact versions and installation state during OR0.3.
- This document does not state that the entire stack is installed, FOSS-license-verified, or operationally accepted.

## Evidence and follow-up contracts
1. **OR0.1 continuation (same bounded discovery scope):** inspect all existing manifest contents and lockfiles; map source-level optional/dynamic dependencies and executable subprocesses; attribute each dependency to precise feature and host; complete coverage of two AST parse failures. No installations.
2. **OR0.2:** read-only full control VM package/OS/service inventory.
3. **OR0.3:** read-only full agents VM inventory, confirm tool paths, versions, browser shared libraries, isolation and manager/worker runtime.
4. **OR0.4:** record genuine FOSS licenses and material obligations; do not exclude valid GPL/AGPL/MPL/LGPL dependencies. Four approved external-service exceptions: OpenAI, PayPal, GitHub, existing bridge.
5. **OR0.5:** build compatibility matrix; only then **OR0.6** may freeze all small installation contracts before any installs occur.
6. **OR0.7–OR0.12:** install, smoke-test and certify, with sanitized GitHub evidence and separate sudo blocks if owner execution needed.

## OR0.1 completion addendum — repository source requirements
The source-level discovery scope is complete for this baseline; **not** a claim of installed software. OR0.2–OR0.5 must verify versions, licenses and tool presence on the VMs.

### Package manifests already present
| Source path | Direct declared requirement | Caveat |
| --- | --- | --- |
| `requirements-owner-approval.txt` | `cryptography>=3.4` | lower bound only; pin chosen compatible release in OR0.5 |
| `artifacts/venture-001-browser/package.json` | `playwright:^1.64.1` | found in workspace alongside `package-lock.json`; verify tracked status and install location |
| `artifacts/venture-001-browser/node_modules/` | Playwright package files | local package presence, **not** an accepted deployable dependency manifest |
| Python imports across runtime/tests | `jsonschema`, `cryptography`, `psycopg` | distinct third-party library families; OR0.5 must resolve actual versions and supporting wheels |
| Python built-ins | `unittest`, `sqlite3`, `subprocess`, `urllib`, `ssl`, `zipfile` etc. | standard library, no third-party installs required |
| Systemd and executable scripts | `systemd`, Bash, coreutils, PostgreSQL client utilities | inspect actual scripts and units for version-specific expectations |
| JavaScript browser and worker checks | Node.js and Playwright/Chromium | browser binary and shared-library availability separately tested in OR0.9 |

### Dynamic/optional imports and subprocess execution
A targeted source scan of 242 Python/JS/shell files (excluding runtime `runs` and `node_modules`) found **21 files with subprocess execution patterns**, **5 with dynamic import patterns**, and **18 referencing executable-tool names**. These are candidate-bearing files rather than counts of mandatory packages. Examples:
- `agents/ceo/provider_dispatch.py` dynamically loads a configured provider module using `importlib.util.spec_from_file_location`. The external provider module's own runtime dependencies must be captured from its controlled deployment manifest; **do not presume the current repository pin is complete**.
- `ventures/venture-001/runtime/worker.py` calls an absolute `/usr/bin/node` executable for a local JavaScript worksheet assertion. This is a legacy fixed-worker pathway, not evidence of real online browser acceptance.
- `ventures/venture-001/validation/prepare-browser.py` calls `apt-get download` and `dpkg-deb -x` for workspace-local browser runtime libs/fonts. It lists `libatk1.0-0t64`, `libatk-bridge2.0-0t64`, `libxcomposite1`, `libxdamage1`, `libxfixes3`, `libxrandr2`, `libgbm1`, `libasound2t64`, `libatspi2.0-0t64`, `libxrender1`, `libxi6`, `libxres1`, `fonts-liberation`, `fonts-dejavu-core`. These are **candidate dependencies only**, subject to exact OS/browser compatibility and FOSS audit. Do not execute the helper until OR0.6 installation contracts are approved.
- `infrastructure/backup-postgres.sh` relies on Bash/coreutils plus `runuser`, `pg_dump` and filesystem permission tools; PostgreSQL version matching and recovery test are later gates.
- `infrastructure/systemd/` contains OpenBao and OPA units; verify whether both are required for the active operating design before adding dependencies.
- Other subprocess-bearing candidates include `ventures/venture-001/runtime/{manager.py,provider_manager.py,online_checks.py}`, `infrastructure/run-{authenticated-handoff,preparation-broker}.py`, and certification scripts. OR0.2/OR0.3 must validate executable paths, permissions, isolation and child-process behavior on designated hosts.
- `ventures/venture-001/runtime/online_browser.cjs`, `ventures/venture-001/validation/browser-journey.cjs` and `runtime/browser_acceptance.js` require direct Node/browser API compatibility verification.

### Host deployment assignments
- **Control VM:** CEO inference and controlled provider loading; cryptographic identities/verification; finance, policy, PostgreSQL driver, broker, backup and systemd tooling.
- **Agents VM:** Python manager/worker runtime, Node and Playwright browser automation, headless Chromium shared libs/fonts, local web app development and private-staging tools, process containment.
- **Shared:** authenticated transport and TLS/SSH components, audit hashing, Git, FOSS licensing and repeatable installation checks.
- **Future approved public hosting:** existing VM/web infrastructure where technically suitable; no new hosting provider or framework chosen without reuse analysis and owner-scope check.

### Mandatory outcomes of subsequent readiness tasks
OR0.2 and OR0.3 must obtain actual OS/architecture, binary paths, package versions, installation provenance and ability to run tools. OR0.4 must document FOSS license classifications (including transitive libraries) and all four approved service exceptions. OR0.5 must pick and record version-compatible supported packages. OR0.6 must create predefined bounded installation assignments, including every needed browser system library and any provider-module dependencies. OR0.7–OR0.12 install, test, certify and commit sanitized evidence.

**OR0.1 determination:** Source-level full-lifecycle dependency discovery completed with explicit unresolved environment/versions/license checks delegated to the correct OR-0 tasks. No packages installed, no privilege/policy/financial state modified, no evidence of live readiness inferred.

## Governance and audit classification
The current owner-approval policy conflict (bounded internal preparation versus owner approval for external operations) remains unresolved. This software inventory changes no authority. Preserve fail-closed behavior pending versioned policy reconciliation and boundary tests before enabling internal delegation.

**Gate decision:** OR-0 NOT READY; Releases A–F NOT AUTHORIZED. This document is a first source-based inventory, not an OR0.12 acceptance certificate.

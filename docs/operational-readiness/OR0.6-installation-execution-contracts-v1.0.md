# OR-0.6 — Fixed installation and rollback contracts
Date: 2026-10-28
Status: EXECUTION CONTRACT READY FOR AUDIT. No packages or services changed by this document.
Baseline: OR0.1–OR0.5 inventory, with OR0.5 planning accepted; operational proof deferred to OR0.7–OR0.11.

## Hard rules
- Pre-existing dirty/untracked work is protected. Do not reset or overwrite it. Do not deploy manager/worker application or enable payments, real CEO authorities or customer operations.
- System Python remains unchanged; only isolated Python environments. No automatic uv-managed Python download. No paid inference or external business actions.
- Both hosts Ubuntu 26.04.1 x86_64, Python 3.14.4, Node 20.20.2 and npm 10.8.2. Control is authoritative repo; Agents workspace is not a Git checkout.
- Exact packages/versions and execution boundaries below are frozen upfront. An installation failure stops that task; no opportunistic switching providers or redesign.
- Every owner-executed sudo command must be its **own** fenced code block, labeled with its VM and purpose. No combined sudo blocks.
- Audit records: commit/push source and configuration first; execute; verify; commit/push sanitized results after each stage.

## Fixed task sequence — do not expand prompts during execution

### OR0.6.1 — Source and digest verification (control, no install)
Commands:
```sh
git rev-parse HEAD
git status --short
node -e 'const p=require("./infrastructure/browser-acceptance/package.json");const l=require("./infrastructure/browser-acceptance/package-lock.json");if(p.dependencies.playwright!=="1.64.1"||l.packages["node_modules/playwright"].version!=="1.64.1"||l.packages["node_modules/playwright-core"].version!=="1.64.1")process.exit(1);console.log("LOCK_OK")'
```
Acceptance: lock consistent and unrelated worktree changes identified; stop on error. Rollback: none.

### OR0.6.2 — uv binary provenance acquisition, pinned release (both VMs, execution OR0.7.1)
Use official uv v0.13.5 release artifact for Linux x86_64 GNU from https://github.com/astral-sh/uv/releases/tag/0.13.5. Obtain its upstream SHA256/attestation from an authenticated trusted provenance channel and check the downloaded file **before** extraction or execution. Record digest, file name, upstream source, signature/attestation and `uv --version`. If official asset digest cannot be verified, STOP; do not run installation scripts or substitute mirrors. Install user-local `~/.local/bin/uv` via a checked archive (no sudo). Use immutable exact version and never an unpinned curl-pipe-shell script. Rollback: remove the newly installed user-local binary only if it did not preexist; restore any previous binary from recorded backup.

### OR0.6.3 — Isolated Python runtime setup (both VMs, OR0.7.2)
Before execution, add a host-specific tracked `pyproject.toml` and fully resolved `uv.lock` with hashes for the minimum declared runtime packages. Never use system `pip` or rewrite /usr Python packages. Exact execution after verified uv binary:
```sh
UV_PYTHON_DOWNLOADS=never ~/.local/bin/uv venv --python /usr/bin/python3 .venv
UV_PYTHON_DOWNLOADS=never ~/.local/bin/uv sync --locked --no-python-downloads
.venv/bin/python -c 'import cryptography,jsonschema,requests; print("PY_ENV_OK")'
```
Control also must import `psycopg` where required; agent must not install psycopg without code evidence. Run within the *approved project-specific runtime directory*, not the non-Git agent workspace root, after manifest deployment. Acceptance: correct Python 3.14, deterministic lock and imports, no system Python changes. Rollback: remove only newly created isolated environment after capturing manifests; protect any existing environment.

### OR0.6.4 — Browser native prerequisites (Agents only, OR0.8.1)
The following **14 Ubuntu 26.04 package candidates** were identified by source and apt-cache. Do not install them blindly: first run a dry-run `apt-get -s install ...` on agents and record additional transitive packages, versions and non-FOSS flags. Only then execute the exact apt install contract with the resolved version-pinned list. Candidate list:
```
libatk1.0-0t64=2.60.4-0ubuntu0.1
libatk-bridge2.0-0t64=2.60.4-0ubuntu0.1
libxcomposite1=1:0.4.6-1build1
libxdamage1=1:1.1.7-1
libxfixes3=1:6.0.0-2build2
libxrandr2=2:1.5.4-1build1
libgbm1=26.0.8-1ubuntu0.3
libasound2t64=1.2.15.3-1ubuntu1.1
libatspi2.0-0t64=2.60.4-0ubuntu0.1
libxrender1=1:0.9.12-1build1
libxi6=2:1.8.2-2
libxres1=2:1.2.1-1build2
fonts-liberation=1:2.1.5-3build1
fonts-dejavu-core=2.37-8build1
```
Read-only dry-run command:
```sh
apt-get -s install libatk1.0-0t64=2.60.4-0ubuntu0.1 libatk-bridge2.0-0t64=2.60.4-0ubuntu0.1 libxcomposite1=1:0.4.6-1build1 libxdamage1=1:1.1.7-1 libxfixes3=1:6.0.0-2build2 libxrandr2=2:1.5.4-1build1 libgbm1=26.0.8-1ubuntu0.3 libasound2t64=1.2.15.3-1ubuntu1.1 libatspi2.0-0t64=2.60.4-0ubuntu0.1 libxrender1=1:0.9.12-1build1 libxi6=2:1.8.2-2 libxres1=2:1.2.1-1build2 fonts-liberation=1:2.1.5-3build1 fonts-dejavu-core=2.37-8build1
```
Installation is allowed only after dry-run and license/BOM checks. If privileged action is necessary, present a **single sudo command in its own code block**, not chained with other commands. Rollback: record preinstalled set and restore exact prior package state using apt; do not remove shared libraries used by other services.

### OR0.6.5 — Playwright+Chromium (Agents only, OR0.8.2/OR0.9)
Install from **tracked** `infrastructure/browser-acceptance/package-lock.json` with `npm ci --ignore-scripts` in an isolated dedicated directory. Verify integrity against lockfile; use Playwright 1.64.1 and chromium revision 1248. Acquire browser archive from the Playwright project official configured registry; capture archive SHA256 and provider URL before accepting it. Do not assume Ubuntu 26.04 is formally supported just because package candidates exist. No customer network or public exposure. Acceptance: `node -e 'require("playwright")'`, headless Chromium launch, localhost HTTP customer-journey smoke (login, CRUD, CSV, logout/login) using synthetic fixtures. Stop on launch failure. Rollback: remove only the newly staged test harness and browser cache.

### OR0.6.6 — Full readiness certification (OR0.10–OR0.12)
Control: PostgreSQL 18.6 read-only connectivity and controlled backup/restore to an isolated temporary database, OPA evaluation, broker health, OpenBao health/necessity trace. Agents: browser smoke, process containment, private staging capabilities. Cross-VM: authenticated handoff with synthetic signatures and denial of all live authority. Log sanitized test exit codes and versions to `docs/operational-readiness/evidence/`; verify fail-closed policy and no financial permissions. Any failure means NOT READY. OR0.12 concludes only after independent GitHub review.

## Execution stop conditions
Wrong versions/OS; untrusted release hashes; apt dry-run adds unreviewed non-FOSS packages; incompatible Chromium libs; tests unexpectedly contact public APIs; unexpected privileged changes; nonzero health or security checks; unexpected dependency drift. Resolve failures as separately scoped correction tasks, not unbounded Codex prompts.

## Deployment and review
For each OR0.7–OR0.12 subtask: source commit -> push -> deploy prerequisites where authorized -> test VM -> sanitized evidence commit/push -> Claude review. Do not combine these tasks into a giant Codex prompt. No new VM, new broker, payment provider or launch authority.

**OR0.6 readiness:** task contracts authored; OR0.7 execution begins only after SHA256 provenance/lock and dry-run checks are proven. This document is not an installation or certification record.

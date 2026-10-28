# OR0.3 — Venture-Agents software and runtime inventory
Date: 2026-10-28
Host: venture-agents
Status: Read-only VM inventory complete for observed scope; OR-0 NOT READY.

## Method
Authorized Venture-Agents bridge executed read-only commands for OS identity, binaries, system Python distributions, systemd unit existence and state, and working-directory layout. No installation, privileged operations, service changes, provider calls, or financial actions. Evidence is a sanitized report; Claude cannot independently interrogate the VM.

## Verified machine/runtime
| Item | Observed |
| --- | --- |
| Hostname | venture-agents |
| OS | Ubuntu 26.04.1 LTS, resolute |
| Architecture | x86_64 |
| Python | 3.14.4 |
| Node.js | v20.20.2, /usr/bin/node |
| npm | 10.8.2, /usr/bin/npm |
| Git | /usr/bin/git |
| apt-get, dpkg-deb | available at /usr/bin |
| ssh, openssl, systemctl, curl | available at /usr/bin |
| psql, pg_dump, pg_restore | not found in inspected PATH |
| chromium, chromium-browser | not found in inspected PATH |

Python system package metadata: cryptography 46.0.5; jsonschema 4.19.2; requests 2.32.5; psycopg, playwright, pytest and pip distributions not found in inspected system environment. This does not rule out project virtual environments or workspace-local browser caches.

## Active services and project state
- `venture-agents-bridge.service`: active, enabled.
- `venture-agents-tunnel.service`: active, enabled.
- No installed manager/worker systemd units detected by the inspected venture-prefixed service listing.
- `/home/epsilon/venture-agents-workspace` is **not a Git checkout** (`.git` missing); local `git rev-parse` returned not-a-repository.
- `ventures/` directory absent in inspected workspace; it therefore does not contain the current committed `ventures/venture-001/runtime/` manager/worker source.
- Source of truth for current implementation is the Venture-Control Git checkout, with operational viability plan and source now committed to GitHub. Reuse and deployment must be resolved in Release A, after OR-0 stack readiness.
- Absence of a system-PATH executable or system Python distribution is evidence of a gap in that observed environment, **not** proof of absence everywhere on the VM.

## Requirements gap against Releases A–F
| Requirement | Status and next action |
| --- | --- |
| Manager/worker Python runtime | Python present; current source and service NOT deployed in observed workspace; A2/A3 remain pending |
| Authenticated agent communication | Bridge and tunnel active; application-level signed cross-VM delegation not proven |
| Cryptography / schema / HTTP | Installed system package versions observed; OR0.4 license audit and OR0.5 compatibility remain |
| Browser customer-journey testing | Node/npm present; Chromium and Playwright unverified/absent from observed system paths; OR0.5–0.9 must resolve |
| Browser OS libs/fonts | Not inventoried package-by-package; use existing `prepare-browser.py` as candidates, only after OS and version validation |
| Database drivers/clients | psycopg distribution and PostgreSQL tools not detected; determine if agent-side direct database access is actually required before installing |
| FOSS development/build tools | Git/Node/npm/Python present; exact build toolchain and project-specific isolated envs not yet tested |
| Containment | Existing source-side containment contracts; VM kernel/user namespaces/process execution controls not yet functionally verified |
| Private online staging | No manager/worker app services observed; need bounded staging host/tool prerequisites, not public launch |
| Monitoring/backup | systemd available; agent-side state backup/restore tooling not fully verified |
| Payment integration | Finance authority remains on control; do not install payment/finance components on agents without established architectural need |

## Evidence and limitations
These observations do not certify sandbox isolation, browser readiness, cross-VM application authentication, installed-package FOSS licenses, or operational manager/worker deployment. No claim of whole-stack readiness is made. No new requirements beyond existing approved architecture are authorized.

**OR0.3 decision:** Host inventory captured; follow-up OR0.4 licensing and OR0.5 compatible-version/VM placement matrix are required. The overall readiness gate remains NOT READY. Next: OR0.4 FOSS/license inventory.

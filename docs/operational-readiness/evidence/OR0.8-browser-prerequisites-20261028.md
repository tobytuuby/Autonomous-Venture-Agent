# OR-0.8 — Browser prerequisite and Playwright installation evidence
Date: 2026-10-28
Status: **OR-0.8 installation checks PASS, browser runtime launch NOT YET TESTED. Independent audit pending.**

## Control contract
OR-0.6 accepted, reference `docs/operational-readiness/OR0.6-installation-execution-contracts-v1.0.md`. Executed on Venture-Agents only. Existing unrelated control worktree and user-local Python environments preserved.

## Ubuntu 26.04 native dependencies
- Exact frozen list of 14 version-pinned browser-related package candidates from OR-0.6.4.
- `apt-get -s install <pinned candidates>` executed and exit status captured directly: **0**. Apt proposed **38 new packages**, **0 upgrades**, **0 removals**. Complete simulation log on agents: `/tmp/or08-apt-simulation.txt` (not committed; includes OS package metadata).
- `sudo -n apt-get install -y <same pinned candidates>` completed with **exit 0**. Output recorded on agents at `/tmp/or08-apt-install.txt`. Installation required Ubuntu repository dependencies including X11/XCB/Mesa libraries; no user-supplied third-party apt repositories or unrelated paid services.
- Postinstall `dpkg-query` confirmed fonts-liberation, libgbm1, libatk1.0-0t64 present. Debian copyright metadata observed for fonts-liberation. **Complete FOSS notice audit for all 38 installed packages remains unverified here.**
- No application service was deployed or restarted intentionally. Apt output included system maintenance lines referencing unattended-upgrades. No business authority changed.

## Node Playwright toolchain
- Reused the committed `infrastructure/browser-acceptance/package.json` and `package-lock.json`; the exact manifest and lock were staged in the agent VM workspace.
- `npm ci --ignore-scripts --no-audit --no-fund` installed 2 packages successfully via lockfile integrity verification.
- `require("playwright/package.json").version` => **1.64.1**.
- Reading installed `node_modules/playwright-core/browsers.json` => Chromium revision **1248**.
- First metadata check incorrectly attempted `require("playwright-core/browsers.json")` and failed due to package `exports` restrictions. Replaced with direct read of the installed file; subsequent check passed. No version change needed.
- **No Chromium executable downloaded or launched at this stage**; OR-0.9 is responsible for browser binary acquisition and headless functional verification.
- No Python, CEO/manager/worker, finance or public customer runtime changes made during OR-0.8.

## Next
OR-0.9: download the pinned Chromium 1248 build using Playwright's configured registry, capture archive provenance, inspect dynamic dependencies, launch headless browser against local synthetic web fixtures, then execute a private customer journey. Any unexpected runtime failure is a separate bounded correction.

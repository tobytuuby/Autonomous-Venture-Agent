# OR-0.9 — Chromium and local browser smoke (2026-10-28)

**Status:** Chromium installed and smoke tests PASS on Venture-Agents. Actual venture product/customer acceptance **NOT TESTED**; independent audit pending.

## Frozen versions and install
- Baseline: Playwright 1.64.1; `playwright-core/browsers.json` revision 1248, Chromium `156.0.8078.4`.
- On Venture-Agents, executed `npx --no-install playwright install chromium` in tracked browser-acceptance dependency directory. The tool reported exit 0 and the following directories exist: `~/.cache/ms-playwright/chromium-1248`, `~/.cache/ms-playwright/chromium_headless_shell-1248`.
- Playwright download log showed provider URLs `https://cdn.playwright.dev/builds/cft/156.0.8078.4/linux64/chrome-linux64.zip`, `https://cdn.playwright.dev/builds/cft/156.0.8078.4/linux64/chrome-headless-shell-linux64.zip`; also FFmpeg build 1013. These URLs are observed provider origins, **not independently proven release archive hashes**.
- Installed Chromium binary SHA-256 `377a9fc07b495c3b8d0ab8ec1fdfd153641759f9756fea34d8dfce4de82f5025`. This is a **post-install binary checksum**, not the original archive checksum nor upstream authenticated expected digest. An independent archive SHA-256 comparison remains open.
- A tool transport warning `ERR_CHILD_PROCESS_STDIO_MAXBUFFER` occurred because download progress was verbose, although its returned log displayed `INSTALL_EXIT=0`. Independently verified installed directories and successful browser execution instead of relying solely on that output.

## Actual runtime results
- Headless Chromium launch via Playwright on Ubuntu 26.04 Venture-Agents: **PASS**, `browser.version() = 156.0.8078.4`.
- In-memory HTML/data URL rendered; title `OR09`, heading `LOCAL_OK`: **PASS**.
- Dedicated temporary Node HTTP server bound only to `127.0.0.1`, Playwright requests blocked unless targeting that localhost origin. Browser-driven test exercised **login UI → create → update → export CSV text → delete → logout**, then printed `SYNTHETIC_LOCALHOST_JOURNEY_PASS`, exit **0**. Synthetic page has no real authentication or persistent datastore; it is an instrumentation smoke test, NOT a deployed venture customer acceptance test.
- No public customer website or external business/payment API contacted in the smoke test. No CEO, manager, worker or finance runtime altered.

## Bounded follow-up
- Capture and independently compare the **download archive's** SHA-256 to an authoritative expected digest before declaring binary provenance complete.
- Full private venture product acceptance (real login, inventory persistence, CSV export, logout and independent sessions) remains pending Release A/acceptance, not proven by this synthetic fixture.
- Complete licensing record for 38 installed Ubuntu libraries/fonts (deferred from OR-0.8), and independent audit.

**Verdict:** OR-0.9 browser runtime proof PASS; archive integrity gate and real product acceptance remain explicitly outstanding.

# Delivered ZIP acceptance

Run from repository root. The buyer needs only the extracted ZIP and a modern browser. The commands below are developer validation infrastructure, not buyer setup.

The existing VM installation is Playwright 1.64.1 under `artifacts/venture-001-browser/node_modules`, with Chromium under `artifacts/venture-001-browser/browsers`. No npm install or browser download is needed on this VM.

If the VM lacks Chromium shared libraries or fonts, run:

```sh
python3 ventures/venture-001/validation/prepare-browser.py
```

This optional Ubuntu-specific setup downloads Debian packages using the existing apt indexes and extracts them inside artifacts. It changes no system packages or services. It needs network access for test infrastructure only; the buyer journey runs with networking disabled. Other hosts may use their already installed libraries/fonts instead. The journey expects the workspace fonts.conf produced by this setup; it fails with BLOCKED if launch or real typing cannot work. Runtime package versions are recorded in artifacts.

```sh
node ventures/venture-001/validation/test-restock.js
node ventures/venture-001/validation/browser-journey.cjs
mkdir -p artifacts/venture-001-browser/regression-tmp
TMPDIR="$PWD/artifacts/venture-001-browser/regression-tmp" PYTHONPATH=. python3 -m unittest discover -s tests -v
git diff --check
```

The browser script sets PLAYWRIGHT_BROWSERS_PATH to the approved artifacts directory, extracts the exact named distributable to a fresh artifacts subdirectory, records its SHA-256, reads the packaged guide, and opens only the extracted file:// HTML. It uses Chromium interactions (clicks, keyboard entry, file selection and download events), not the product's calculation or CSV functions. Expected values and the downloaded CSV reader are independent of product code. It records every case, failures and browser version in report.json, saves PNG screenshots, both downloaded CSVs, and a printed PDF. Failures or setup blockers return nonzero. A small separate typing preflight catches the VM's missing-font failure before customer steps.

The 16 checks cover guide, first open, blank entry/export validation, item entry, inclusive threshold and inbound, added rows/total, both actual CSV downloads, reload/import restoration, native beforeprint event and landscape layout, invalid numeric inputs/recovery, malformed import preservation, both decimal regressions, removal/empty-table validation, and offline/network/error checks. Screenshots are desktop Chromium; physical printers, OS print dialogs, other browsers, mobile and human usability interviews are outside this evidence.

After product changes, rebuild and rerun the ZIP journey:

```sh
python3 ventures/venture-001/validation/build-kit.py
node ventures/venture-001/validation/browser-journey.cjs
```

The builder packages exactly START-HERE.md and restock.html with fixed metadata. The original distributable pathname remains the acceptance target. Source-only assertions supplement but cannot substitute for this ZIP journey. See [ACCEPTANCE-20261026.md](ACCEPTANCE-20261026.md) for observed results and committed raw evidence.

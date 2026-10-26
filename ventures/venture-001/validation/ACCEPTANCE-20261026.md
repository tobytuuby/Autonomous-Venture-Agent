# Studio Restock Kit delivered ZIP acceptance — 2026-10-26

**Decision: PASS for the tested desktop Chromium offline journey, after three verified product fixes.** This is automated customer-perspective functional acceptance, not human buyer validation, a sales result, approval to contact anyone, or production certification. No outreach was performed.

Starting repository HEAD: `1524360f5677a31a68597c2ec13bb0d435fc3bdd`, branch main. The only pre-existing untracked file was `infrastructure/venture-ceo-kernel-gate.runtime.json`; it was preserved and its before/after SHA-256 matched. All changes are under ventures/venture-001. No scheduled CEO configuration, state or services were modified or invoked. Protected scheduled state was not independently compared byte for byte. No real CEO, capital, payments, orders, venture launch or deployment was used.

## Exact artifact and environment

Target: `ventures/venture-001/Studio-Restock-Kit-v1.0.zip`.

- Original ZIP SHA-256: `a0758ebfaf79361c2109cab67109a849e21c3d77a15d602c60b88c4534053d58`.
- Accepted ZIP SHA-256: `e54d5ad724f195d423579cc2a00976299da03246a99761f3f31070e9240a9ff4`.
- ZIP contains exactly START-HERE.md and restock.html; accepted entries were compared byte for byte with product source after the ZIP journey.
- Playwright 1.64.1; Chromium version is recorded in the [raw accepted report](evidence-20261026/accepted/report.json). Headless Linux Chromium, 1440×1000 screen, 1047×740 print-media viewport; A4 landscape PDF.
- Every browser run extracted the target ZIP into a new temporary directory under artifacts and opened the extracted file:// HTML. No source HTML was used by the acceptance journey. Browser context was offline from first open; HTTP(S) attempts were intercepted and counted. Observed attempts and page/console errors: zero.
- The VM lacked Chromium libraries and all fonts. Workspace-only Debian-package extraction supplied the missing libraries and fonts; no system install, service change or elevated privileges were used. Before fonts were supplied, browser text entry silently failed, so those diagnostic runs are **not product acceptance evidence**. The successful typing preflight now distinguishes this environment blocker. Only the baseline after environment repair is used below. Setup network traffic belongs to developer infrastructure, never the buyer journey.

## Observed checks

| Browser case | Original ZIP | Accepted ZIP |
|---|---|---|
| Read packaged START-HERE, offline/save/import instructions | PASS | PASS |
| First file open, four fictional rows, total 90.00 | PASS | PASS |
| Start blank; invalid inputs cannot download | PASS | PASS |
| Enter buyer item: 3 packs / 37.5 kg / 66.00 | PASS | PASS |
| Inclusive threshold and inbound suppress unnecessary orders | PASS | PASS |
| Add Boxes: 3 packs / 30 pieces / 24.00; total 90.00 | PASS | PASS |
| Actual inputs CSV download, exact values and quoted item name | PASS | PASS |
| Actual results CSV download, quantities/costs/statuses | PASS | PASS |
| Reload, select downloaded CSV, restore buyer inputs/results | PASS | PASS |
| Print button/native beforeprint; table fits printable width | **FAIL** | PASS |
| Negative input, zero pack, invalid target, recovery | PASS | PASS |
| Malformed CSV import reports error and preserves rows | PASS | PASS |
| 0.1 + 0.2 at point 0.3: 2 packs / 0.2 / 2.00 | **FAIL** | PASS |
| 0.07 target / 0.01 pack: 7 packs / 0.07 / 7.00 | **FAIL** | PASS |
| Remove rows; empty-table export validation | PASS | PASS |
| Offline operation without network attempts or runtime errors | PASS | PASS |
| **Total** | **13 PASS, 3 FAIL** | **16 PASS, 0 FAIL** |

The original print table measured 1886.3125 px against a 1047 px print viewport. The original decimal threshold returned position 0.30000000000000004 and NO ORDER; the decimal pack ceiling ordered 8 instead of 7. The [baseline per-case report](evidence-20261026/baseline/report.json) preserves assertion failures and expected/actual values.

## Fixes and verification

The worksheet now uses exact decimal digits with scaled integers for threshold decisions, pack ceilings and money rounding. Printed content is a separate wrapped text checklist with repeated headings, landscape page sizing and all 15 data/result columns. It is built for the native beforeprint event, including browser menu printing; invalid rows retain their validation message. The guide now explicitly explains ZIP extraction and print preview. The original distributable pathname was rebuilt and tested again after the guide change.

Changed product files: product/restock.html, product/START-HERE.md and Studio-Restock-Kit-v1.0.zip. Validation changes: browser-journey.cjs, prepare-browser.py, build-kit.py, test-restock.js, TEST-PLAN.md, this assessment and evidence-20261026/.

Executed commands and raw evidence:

- `python3 ventures/venture-001/validation/prepare-browser.py`: exit 0; [setup output](evidence-20261026/setup-reproduction.log) and [package versions](evidence-20261026/runtime-packages.txt). This also tested the reproducible workspace setup.
- `node ventures/venture-001/validation/test-restock.js`: exit 0; all assertions passed, including both decimal regressions, half-cent rounding and excessive-result rejection. [Raw output](evidence-20261026/focused.log).
- `node ventures/venture-001/validation/browser-journey.cjs`: final exit 0; **16/16** checks passed on the final ZIP. [Raw log](evidence-20261026/acceptance.log), [per-case report](evidence-20261026/accepted/report.json), [inputs download](evidence-20261026/accepted/restock-inputs.csv), [results download](evidence-20261026/accepted/restock-results.csv).
- `TMPDIR="$PWD/artifacts/venture-001-browser/regression-tmp" PYTHONPATH=. python3 -m unittest discover -s tests -v`: exit 0; **686 tests, OK**. [Full raw output](evidence-20261026/regression.log). This is repository regression evidence, not a replacement or expansion of ADV-001–ADV-049 or its /49 denominator.
- Deterministic ZIP rebuild and source/ZIP byte comparisons passed. `git diff --check` passed. [Execution records](evidence-20261026/commands.json); [artifact hashes](evidence-20261026/SHA256SUMS).

Screenshots: [first open](evidence-20261026/accepted/01-first-open.png), [entered buyer results](evidence-20261026/accepted/02-entered.png), [print layout](evidence-20261026/accepted/03-print.png). The print screenshot was visually reviewed: both buyer rows, full item text, quantities, costs and total are present without horizontal clipping. [Generated checklist PDF](evidence-20261026/accepted/checklist.pdf).

## Operator assessment and limits

Evidence class: locally executed real Chromium UI interactions with synthetic inventory and independently asserted expected values. Calculations and downloaded CSV checks did not call product calculation/CSV helpers. Browser evidence is directly observed; it is not a provider/model self-report. The source-only unit test is supplemental. No human customer has independently confirmed usability or willingness to buy.

The buyer can extract/open the kit offline, enter stock, review suggestions and save/restore via CSV. Reload intentionally discards unsaved entries and returns to fictional examples; the guide explains this. The desktop worksheet scrolls horizontally. Printing was tested through the real button and native beforeprint event, print-media geometry, screenshot and generated PDF. Headless Chromium cannot validate an OS print dialog, physical printer or printer-driver overrides. Other browsers, mobile layouts, assistive technology, long multipage printouts and real supplier data were not tested. These remain review limitations, not PASS claims.

Review outcome: the three observed functional failures are resolved in the accepted ZIP. This evidence supports the tested functional scope only. It changes no authority boundary or outreach gate. Actual purchasing remains a human review step, and the kit performs no ordering or payments.

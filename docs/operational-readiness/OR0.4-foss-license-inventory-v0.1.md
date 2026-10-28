# OR0.4 — FOSS software license inventory and obligations
Date: 2026-10-28
Scope: installed core dependencies on Venture-Control and the OR0.1 software candidates for both VMs.
Status: source/package-level FOSS classification completed for named primary components; complete transitive/package-BOM verification remains a prerequisite for OR0.5 and installation.

## Rules
Only FOSS software licenses are allowed for installed tools, with four approved proprietary external service exceptions: OpenAI, PayPal, GitHub, and the existing LocalBridge infrastructure. GPL, LGPL, AGPL and MPL are eligible; log material license obligations instead of excluding them. No additional vendor, SaaS service or licensed software is authorized. License conclusions are not legal advice.

## Installed Python dependency metadata — Venture-Control
| Package | Observed version | SPDX/license metadata | Main obligation or note |
| --- | --- | --- | --- |
| cryptography | 46.0.5 | Apache-2.0 OR BSD-3-Clause | retain applicable copyright/license notices on redistribution |
| jsonschema | 4.19.2 | MIT | preserve copyright and permission notice when distributing |
| psycopg | 3.3.2 | LGPL-3.0-only | preserve license/notice and analyze LGPL obligations if distributing or modifying covered library |
| requests | 2.32.5 | Apache-2.0 | preserve license/notice; NOTICE obligations where applicable |
| attrs | 25.4.0 | MIT | notice preservation |
| jsonschema-specifications | 2023.12.1 | MIT | notice preservation |
| referencing | 0.36.2 | MIT | notice preservation |
| rpds-py | 0.27.1 | MIT | notice preservation |
| certifi | 2026.1.4 | MPL-2.0 | file-level copyleft obligations on covered changes/distribution; document actual bundle license |
| idna | 3.11 | BSD-3-Clause | notice retention |
| urllib3 | 2.6.3 | MIT | notice retention |
| charset-normalizer | not found by this inspection | UNKNOWN | determine actual HTTP client dependency variant and packaging |

The exact environment, distribution metadata, and transitive libraries of any deployed isolated Python env still require inspection. Do not treat the above as a complete dependency tree. These observations use installed package metadata, not assumptions from import names.

## System/runtime and candidate components
| Component | Expected FOSS license | Evidence basis | Open condition |
| --- | --- | --- | --- |
| Ubuntu/Linux and core utilities | multiple FOSS licenses including GPL | OS distribution | enumerate required individual binary/package records and license files for final deployment BOM |
| Python interpreter and standard library | Python Software Foundation License and bundled third-party licenses | upstream Python | installed package notices/version check |
| Node.js | MIT with separately licensed bundled libraries | upstream Node source | preserve third-party notice bundle |
| npm | Artistic-2.0 (verify package-specific version) | candidate, NOT package-audited | verify shipped package metadata and transitive entries |
| PostgreSQL | PostgreSQL License | upstream postgresql.org | preserve notice |
| Git | GPL-2.0-only (verify packaged notices) | known upstream license | retain appropriate license source/offers if redistributed |
| systemd | LGPL-2.1-or-later and bundled component licenses | candidate | inspect distro copyright files per package |
| OpenBao | MPL-2.0 | official OpenBao project | verify installed binary version, active role and distribution obligations |
| Open Policy Agent (OPA) | Apache-2.0 | official OPA repository | verify actual installed version and operational need |
| Playwright | Apache-2.0 | locally installed Node package manifest and Microsoft project | inspect exact locked transitive versions |
| Chromium | BSD-style plus third-party bundled licenses | candidate browser | inspect exact browser build and license bundle before install |
| Browser shared libraries/fonts | various FOSS and font licenses | candidates in `prepare-browser.py` | version/package/copyright file review for every selected Debian package, including font redistribution terms |
| cryptography native dependencies | OpenSSL and optional Rust/native code with separate FOSS licenses | runtime candidate | inspect installed package/provenance before final lock |
| Bash, coreutils, openssh, curl, openssl | multiple FOSS licenses | installed executables | exact distro package/license files and redistribution obligations pending |

The browser candidate packages from OR0.1 remain candidates: `libatk1.0-0t64`, `libatk-bridge2.0-0t64`, `libxcomposite1`, `libxdamage1`, `libxfixes3`, `libxrandr2`, `libgbm1`, `libasound2t64`, `libatspi2.0-0t64`, `libxrender1`, `libxi6`, `libxres1`, `fonts-liberation`, `fonts-dejavu-core`. Do not silently claim every package is installed or license-audited. `apt-get` and `dpkg-deb` are already available on both VMs, but the helper was NOT run.

## Material license controls
1. Retain notices, license texts and applicable NOTICE files for distributed software, including bundled dependencies.
2. GPL/AGPL obligations depend on redistribution, modifications, and (for AGPL) relevant network use; identify triggering behavior separately rather than banning the package.
3. LGPL-covered psycopg and system libraries may impose notice/source and modification/relinking obligations on distribution; assess actual bundling and linking.
4. MPL-2.0 (OpenBao/certifi) is file-level copyleft with source availability obligations for modifications to covered files when distributed.
5. Browser/font package bundles may carry mixed licenses: collect package-specific copyright and notice files before packaging artifacts for customers.
6. For SaaS operations and proprietary application code, using an unmodified FOSS dependency does not automatically imply the application must be open sourced; however the actual dependency, license and distribution model determine obligations.
7. The owner is the independent decision-maker for eventual software-license compliance. Neither CEO nor manager may relax the FOSS-only policy.

## External services — explicitly approved exceptions only
| Service | Classification | Restriction |
| --- | --- | --- |
| OpenAI API | proprietary external service exception | inference costs governed separately; no unapproved paid calls |
| PayPal Business | proprietary payment service exception | only approved provider; no live payment authority enabled by inventory |
| GitHub | proprietary hosted repository service exception | source/evidence workflow only |
| Existing LocalBridge | pre-existing connector infrastructure exception | no expansion to new paid bridge or provider |

## Primary verification references
- Upstream PostgreSQL license: https://www.postgresql.org/about/licence/
- Node.js license/third-party notices: https://github.com/nodejs/node/blob/main/LICENSE
- Python jsonschema metadata: https://github.com/python-jsonschema/jsonschema/blob/main/pyproject.toml
- Psycopg package license metadata: https://www.psycopg.org/download/
- OPA upstream license: https://github.com/open-policy-agent/opa
- OpenBao upstream license: https://github.com/openbao/openbao
- Playwright source/package: https://github.com/microsoft/playwright
- Mozilla MPL license and explanation: https://www.mozilla.org/en-US/MPL/

## Acceptance decision and remaining work
**OR0.4 software policy check: PASS for identified primary FOSS components; final dependency/license BOM: OPEN.** No proprietary installed requirement has been established by the inspected primary components, but the inventory does not prove every direct and transitive package or binary's license. OR0.5 must select exact versions, record package provenance and compatible license obligations, identify optional versus essential packages, and flag any non-FOSS package before OR0.6 installation contracts. OR0.12 may not certify readiness until this is resolved.

No installation, service changes, policy authority changes, paid inference or payments were conducted.

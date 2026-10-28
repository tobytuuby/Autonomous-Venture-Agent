# OR0.5 — Version compatibility and placement matrix (evidence-based)
Date: 2026-10-28. Baseline Git commit: 991aa5f.
Status: **PARTIAL / NOT ACCEPTED AS INSTALLATION LOCK.** This is a concrete version/placement decision record, not an authorization to install.

## Observed and proposed version matrix
| Component | Control observed | Agents observed | Required host | Version choice / source | Gate |
|---|---|---|---|---|---|
| Ubuntu | 26.04.1 LTS x86_64 | 26.04.1 LTS x86_64 | both | existing OS | retain |
| Python | 3.14.4 | 3.14.4 | both | existing Python | import/runtime smoke pending |
| Node.js | 20.20.2 | 20.20.2 | agents; control existing | existing Node 20; Playwright manifest requires Node >=20 | compatible on paper; smoke pending |
| npm | 10.8.2 | 10.8.2 | agents | existing | smoke pending |
| cryptography | 46.0.5 | 46.0.5 | both | existing; manifest lower bound >=3.4 | smoke |
| jsonschema | 4.19.2 | 4.19.2 | both if used | existing | smoke |
| requests | 2.32.5 | 2.32.5 | both if configured provider uses it | existing | smoke |
| psycopg | 3.3.2 | not detected | control ONLY unless code trace requires otherwise | retain existing control version | agent direct DB client not justified |
| PostgreSQL client/server | client 18.6; service active | not detected | control | existing PostgreSQL 18.6 | server detail and restore test pending |
| OpenBao | 2.6.2 installed | not established | control only | existing | retained as legacy service dependency pending architecture necessity assessment |
| OPA | 1.20.2 at /usr/local/bin/opa | not established | control only if active policy path uses it | existing | service definition alone does not establish runtime necessity |
| Playwright JS | node_modules local 1.64.1; manifest ^1.64.1 | not detected | agents browser harness | exact 1.64.1 from existing lockfile, with playwright-core exactly 1.64.1 | lock provenance and browser install pending |
| Chromium | not in PATH | not in PATH | agents | **UNSELECTED** pending Playwright browser revision/OS libs verification | installation gate |
| Browser OS libs/fonts | partially installed on control | packages not inventoried on agents | agents | **UNSELECTED** (Ubuntu 26.04 compatible packages must be enumerated) | installation gate |
| Git/SSH/openssl/systemd/apt tools | found | found | both | existing distro versions, exact package locks pending | OS license/BOM review |

## Python distribution license and dependency findings
- cryptography 46.0.5 Apache-2.0 OR BSD-3-Clause; jsonschema 4.19.2 MIT; psycopg 3.3.2 LGPL-3.0-only; requests 2.32.5 Apache-2.0.
- Runtime: certifi 2026.1.4 MPL-2.0; idna 3.11 BSD-3-Clause; urllib3 2.6.3 MIT; attrs 25.4.0 MIT; referencing 0.36.2 MIT; jsonschema-specifications 2023.12.1 MIT; rpds-py 0.27.1 MIT.
- `charset-normalizer` NOT present under inspected system Python metadata; `chardet==5.2.0` is installed and reports LGPL license metadata. This is **not** evidence of a missing non-FOSS dependency; requests may use chardet. Test HTTP client runtime with approved local fixtures.
- `cffi` and `pycparser` not in system distribution metadata; don't add them speculatively.
- Playwright lockfile reports `playwright@1.64.1` and `playwright-core@1.64.1`, each Apache-2.0 with npm registry integrity hashes and Node >=20. The observed lockfile is **not tracked** in Git (`git ls-files` returned nothing). Installation contracts must produce a tracked, controlled lockfile without committing node_modules or runtime artifacts.
- Python dependencies currently lack a single source-of-truth full transitive lock. OR0.5 cannot truthfully claim a reproducible pin for all platforms until a frozen, installable manifest and installed distribution provenance are validated.

## Architecture decisions
1. Keep PostgreSQL, psycopg, finance and payments on control. Do **not** install them on agents unless an actual agent-side source dependency justifies it.
2. Keep Node, Playwright and Chromium customer-journey harness on agents. Reuse existing `validation/prepare-browser.py` only after OS-specific package analysis; do not run its apt calls now.
3. Do not blindly reinstall OpenBao or OPA. OpenBao is declared as an ordering dependency by `venture-ceo-shadow.service`; code necessity and health remain to be verified. OPA has an installed executable and service but no runtime call established from this inspection; retain existing setup, do not duplicate it on agents. Classify OPA **operational-need unresolved** and prefer removal from future install contracts if unreferenced after definitive trace.
4. Runtime dynamic loading of `ventures/venture-001/runtime/provider_manager.py` uses the existing checked-out source; recursively check selected provider adapter dependencies with local fixture smoke, not an invented external Python plugin.
5. FOSS license classes permit LGPL and MPL, with notices, modification/distribution obligations documented by OR0.4. The four non-FOSS service exceptions remain OpenAI, PayPal, GitHub, LocalBridge; nothing else is introduced.
6. Preserve existing Python/Node stack to avoid unnecessary upgrades. The distinction between setup tools and existing application deployment remains intact.

## Follow-up evidence after independent OR0.5 review (2026-10-28)
The auditor accepted the partial matrix, NOT installation readiness. This addendum tightens the outstanding dependencies without silently changing the operating design.

### Dependency-chain verification
The installed Python distribution metadata was checked against declared `Requires-Dist` entries. `requests 2.32.5` lists `chardet>=3.0.2`, `idna>=2.5,<4`, `urllib3>=1.21.1,<3`, and `certifi>=2017.4.17`. Observed `chardet==5.2.0` satisfies that dependency, so `charset-normalizer` is not a required replacement here. `jsonschema` uses `attrs`, `jsonschema-specifications`, `referencing`, and `rpds-py`, which are present at the versions already documented. Python-version-conditional and extra-only dependencies must be excluded from the actual lock unless activated. These package-level observations **do not** constitute a complete reproducible environment lock.

### Definitive necessity decisions within existing architecture
- **OPA: REQUIRED by currently installed broker service contract.** `infrastructure/systemd/venture-control-broker.service` has `Requires=opa.service` and `After=opa.service`; `kernel/broker/broker.py` assembles an `opa_input` and invokes `policy_evaluator`. The concrete deployment's evaluator adapter still needs an authenticated, read-only trace; do not delete or omit OPA from control readiness.
- **OpenBao: RETAIN AS EXISTING CONTROL DEPENDENCY, DIRECT RUNTIME USE NOT PROVEN.** `venture-ceo-shadow.service` declares `After=openbao.service` but **not** `Requires=`; this ordering alone does not prove a functional secret-store call or that startup requires OpenBao. An existing `kernel/execution/openbao.py` integration also requires verification against the active entrypoint and configuration. Do not add OpenBao to agents or remove control deployment before that trace.
- **Agents-side PostgreSQL: NOT REQUIRED by the selected deployment design.** There is no established agent-side database-client call; avoid installing PostgreSQL/psycopg on the agent VM pending a concrete source-to-runtime dependency. Persistent state and finance remain control-side.
- **Node browser manifest:** The local lock records `playwright@1.64.1` and `playwright-core@1.64.1` with registry integrity hashes; both are Apache-2.0, Node >=20. This is a vetted *candidate*, not a tracked deployment artifact. The eventual tracked manifest must have verified provenance and matching browser binaries.

### Explicit unresolved proofs
A complete, reproducible Python lock for both host roles; browser executable revision and Ubuntu 26.04 shared-library compatibility; exact apt package versions and package-specific licenses/notices; controlled project-specific Python environments; dependency vulnerability/advisory verification; actual OpenBao active entrypoint use. **No packages were installed and OR0.6 installation authorization remains denied.**

## Additional direct checks — 2026-10-28
- System Python `python3 -m pip --version` returned `No module named pip` on Venture-Control. No `pip` or `uv` executable resolved in the inspected PATH. Therefore a lock that is *installable and verified here* cannot be claimed from metadata alone.
- Captured the twelve observed Python direct/transitive distribution versions in `docs/operational-readiness/evidence/OR0.5-control-python-observed-versions.txt`. **This is evidence, not an install-ready lock:** missing hashes, environment/metadata reproducibility and isolated-environment verification remain open.
- Reconfirmed local JS lockfile v3 has Playwright and playwright-core at exactly 1.64.1. Its root manifest still requests `^1.64.1`, and it remains untracked. This is not an approved reproducible browser installation.
- Expected control user Playwright browser cache path `/home/epsilon/.cache/ms-playwright` produced no browser directory during inspection. Browser build, assets, system libraries and execution on Venture-Agents remain unverified.
- Sample installed Ubuntu 26.04 browser library candidate versions observed on control: `libatk1.0-0t64 2.60.4-0ubuntu0.1`, `libatk-bridge2.0-0t64 2.60.4-0ubuntu0.1`, `libatspi2.0-0t64 2.60.4-0ubuntu0.1`, `libgbm1 26.0.8-1ubuntu0.3`, `libasound2t64 1.2.15.3-1ubuntu1.1`, `fonts-dejavu-core 2.37-8build1`. Package copyright files exist for several checked packages. This is **not** the full agent-side dependency/license BOM.
- `openbao.service` and `opa.service` both reported **active**. Active services and source-unit relationships justify retaining existing services while tracing functionality, but do not demonstrate a real CEO-to-OpenBao request. No service was changed.
- **Blockers remain:** hash-locked Python and JS artifacts with verified provenance; supported browser build and all Ubuntu 26.04 library versions/notices; actual isolated environments; software advisory review; active OpenBao call path. OR0.5 remains NOT COMPLETE and OR0.6 stays BLOCKED.

## OR0.5 verification continuation — 2026-10-28 (no installation)
The following are verified **choices and facts**, not a passed complete compatibility gate.

### uv selection
- **Selected candidate:** `uv==0.13.5`, a documented October 21, 2026 release; upstream changelog reports certificate-trust security fixes through 0.13.4/0.13.5 and continued explicit Python 3.14 support. Release history: https://github.com/astral-sh/uv/releases and https://github.com/astral-sh/uv/blob/main/CHANGELOG.md.
- Project source license: MIT OR Apache-2.0, subject to the selected release artifact's included notices and verification. `uv` is FOSS-eligible and works without system `pip`; **not yet installed**.
- Installation contract MUST request `/usr/bin/python3` or explicit Python 3.14, disable automatic interpreter downloads, verify the uv artifact digest/attestation and create an isolated project environment. Upstream uv 0.13 changed default managed Python to 3.15; do **not** invoke commands that silently upgrade the system interpreter.
- Platform candidate: Linux x86_64 GNU; exact signed asset SHA-256/attestation and install provenance remain to be extracted and locked at OR0.6. No vendor-hosted install shell script is to be executed unreviewed.

### Playwright Chromium selection
- Existing local `playwright-core` v1.64.1 `browsers.json` reports **Chromium revision 1248**, browserVersion `156.0.8078.4`, plus **chromium-headless-shell revision 1248**, same version. This identifies a precise candidate build, **NOT proof** it runs on Ubuntu 26.04.
- Browser download artifact integrity, supported Linux shared-library resolution, and the full selected apt/font license BOM are still NOT verified on Venture-Agents. Do not classify the browser as installation-ready.
- The existing `package-lock.json` is untracked; move/copy a sanitized exact-manifest + lock under a designated tracked build/test directory in the next controlled provenance step. Never commit `node_modules`.

### OpenBao active use
- `kernel/execution/openbao.py` contains an `OpenBaoLeaseClient` that uses `urllib.request` for `/v1/auth/token/create` and revoke-accessor operations, explicitly described as an internal execution-service integration.
- A source reference search found **no instantiation/reference to `OpenBaoLeaseClient` outside its definition** within `agents/` and `kernel/`. This does not disprove use via dynamic configuration, but **active CEO runtime use remains unproven**. Preserve the existing active service; treat OpenBao as existing, not a new mandatory dependency on Venture-Agents.
- OPA remains a required control service due to existing broker systemd `Requires=opa.service`.

### Security and license gate
- The upstream uv security certificate fixes give a reason to prefer uv 0.13.5 over 0.13.3. This is **not a full advisory scan** of cryptography, PostgreSQL, Playwright, browser, libraries or Python runtime.
- A complete exact-version transitive dependency/advisory report and selected browser Debian copyright/notice files are still required. No blanket "no vulnerabilities" claim can be made.
- **Status remains NOT COMPLETE** because Ubuntu browser compatibility, full binary provenance/license records, and repeatable hash-locked installation have not been demonstrated. OR0.6 remains blocked.

## Execution evidence — package prerequisites and controlled browser manifest (2026-10-28)

- Cross-checked all **14 browser candidate Ubuntu packages** via `apt-cache show` directly on Venture-Agents. Versions: libatk1.0-0t64 2.60.4-0ubuntu0.1; libatk-bridge2.0-0t64 2.60.4-0ubuntu0.1; libxcomposite1 1:0.4.6-1build1; libxdamage1 1:1.1.7-1; libxfixes3 1:6.0.0-2build2; libxrandr2 2:1.5.4-1build1; libgbm1 26.0.8-1ubuntu0.3; libasound2t64 1.2.15.3-1ubuntu1.1; libatspi2.0-0t64 2.60.4-0ubuntu0.1; libxrender1 1:0.9.12-1build1; libxi6 2:1.8.2-2; libxres1 2:1.2.1-1build2; fonts-liberation 1:2.1.5-3build1; fonts-dejavu-core 2.37-8build1. Repository candidates are **not yet verified installed** on Venture-Agents, and Playwright may require additional libraries.
- Reused the existing local npm registry-integrity lock and established a **tracked candidate manifest** at `infrastructure/browser-acceptance/package.json` and `package-lock.json`, pinned to exact `playwright==1.64.1` (npm version syntax `1.64.1`), with `playwright-core==1.64.1`. Read-only Node structural validation passed. `npm ci` and browser launch remain future acceptance checks.
- The external release changelog confirms uv 0.13.5, 2026-10-21 and Python 3.14 support, but it is **not installed** and artifact checksums/platform attestation have not yet been independently validated.
- Exact license notice files for the agent VM's **not-yet-installed** libraries, browser binary compatibility, and vulnerability advisory results remain open; package availability alone cannot pass the gate.
- Underlying project runtime, owner approvals, and finances remain untouched. **OR-0.5 NOT COMPLETE; installation not authorized by this evidence alone.**

## October 28 verification: upstream provenance and lock procedure
- uv 0.13.5 PyPI **manylinux x86_64 wheel** SHA-256: `fa8d26e08e34c29c0c4e820cf3181757086d547240b4f4d31ff1d8bd810ca946`. PyPI release artifact: `uv-0.13.5-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` (published 2026-10-22). This is an upstream-published digest, **not locally verified wheel bytes or a security attestation**. Reference: https://pypi.org/project/uv/0.13.5/
- Python lock design: create a project-local `pyproject.toml` with exact direct versions, `requires-python = "==3.14.*"`; set `UV_PYTHON_DOWNLOADS=never` and explicitly select `/usr/bin/python3`; run selected uv `lock` to produce `uv.lock` with resolved packages and registry artifact hashes; verify with uv `sync --locked --no-python-downloads` in a clean isolated environment only **after OR0.6 contract approval**. Python hash-locked artifact references must be inspected against upstream digests; do not simply re-label observed system packages as locked dependencies. Commands are procedural design, not executed.
- Node artifact: the repository's tracked `infrastructure/browser-acceptance/package-lock.json` provides npm package integrity hashes, verified structurally against the tracked exact-version manifest; actual npm tarball bytes and browser archive digest remain to be checked.
- Chromium revision 1248 is declared in the existing Playwright package metadata; **no authoritative archive SHA-256 has been established**. Verify the real downloaded archive checksum against an authenticated trusted source before installing or treating the browser as accepted.
- Ubuntu library candidates, including fonts, have exact release package versions on Venture-Agents; **complete per-package copyright file extraction and transitive browser dependencies remain unresolved**.
- Advisory posture: upstream uv changelog notes 0.13.4/0.13.5 certificate-trust fixes, but there is **no comprehensive package-level OSV/GHSA/Ubuntu-USN report** yet. Do not infer lack of vulnerabilities.
- OR0.5 decision **STILL OPEN**. This is a concrete provenance advance; OR0.6 cannot be approved from this evidence alone.

## Outstanding blockers before OR0.6
- Produce a **complete trackable reproducible direct+transitive Python requirements/lock manifest**, identifying host-specific environment resolution and actual native dependencies.
- Track and validate JS package-lock with integrity; verify selected browser revision is downloadable and runnable with the listed Ubuntu libraries, without executing installation before OR0.6.
- Complete exact Debian/Ubuntu package/version/license and font notice BOM for the selected browser dependencies (not just candidates); verify project and virtual environments.
- Verify whether OpenBao and OPA are active design requirements using source and nonsecret service configuration. Don't confuse installed services with necessary ones.
- Verify selected versions against OS, Python 3.14 wheels and import APIs, and check existing software for vulnerable/unsupported builds where applicable.
- Document safe installation plan steps and tests **upfront** in OR0.6; missing blockers above must be settled before declaring OR0.5 complete.

**Decision: OR0.5 NOT COMPLETE / NO OR0.6 INSTALLATION CONTRACT APPROVAL.** This document records known versions and host placement, flags concrete missing proof, and prevents false readiness. No software installed, services altered or paid inference executed.

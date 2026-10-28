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

## Outstanding blockers before OR0.6
- Produce a **complete trackable reproducible direct+transitive Python requirements/lock manifest**, identifying host-specific environment resolution and actual native dependencies.
- Track and validate JS package-lock with integrity; verify selected browser revision is downloadable and runnable with the listed Ubuntu libraries, without executing installation before OR0.6.
- Complete exact Debian/Ubuntu package/version/license and font notice BOM for the selected browser dependencies (not just candidates); verify project and virtual environments.
- Verify whether OpenBao and OPA are active design requirements using source and nonsecret service configuration. Don't confuse installed services with necessary ones.
- Verify selected versions against OS, Python 3.14 wheels and import APIs, and check existing software for vulnerable/unsupported builds where applicable.
- Document safe installation plan steps and tests **upfront** in OR0.6; missing blockers above must be settled before declaring OR0.5 complete.

**Decision: OR0.5 NOT COMPLETE / NO OR0.6 INSTALLATION CONTRACT APPROVAL.** This document records known versions and host placement, flags concrete missing proof, and prevents false readiness. No software installed, services altered or paid inference executed.

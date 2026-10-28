# OR-0.7.2 — uv installation and runtime verification

Date: 2026-10-28
Status: **PASS for user-local uv installation/version on both VMs; awaiting independent audit**.

## Approved upstream artifact

- Release: https://github.com/astral-sh/uv/releases/tag/0.13.5
- File: `uv-x86_64-unknown-linux-gnu.tar.gz`
- Trusted GitHub published SHA-256: `f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f`
- Both VM archives verified with SHA-256 before extraction. GitHub attestation signature verification explicitly deferred by independent OR-0.7.1 audit; SHA-256 release integrity accepted.

## Host observations

| Host | Archive verification | Install path | Version output | Verdict |
|---|---|---|---|---|
| venture-control | SHA-256 match (observed) | `~/.local/bin/uv` | `uv 0.13.5 (x86_64-unknown-linux-gnu)` | PASS |
| venture-agents | `sha256sum -c` returned OK | `~/.local/bin/uv` | `uv 0.13.5 (x86_64-unknown-linux-gnu)` | PASS |

No pre-existing user-local uv binary was found before installation. Extraction used `tar -xOzf` of the checked archive to a newly created user-local binary, then `chmod 755`. No root privileges, Python package installation, system Python modifications or service changes occurred. Pre-existing unrelated git worktree changes were not staged or modified.

**Scope:** This evidence proves only uv 0.13.5 archive digest matching and executable installation on both hosts. It does not claim isolated Python environments, locked Python packages, Playwright, Chromium, browser testing or CEO/manager/worker acceptance.

**Next:** Independent audit of this evidence before OR-0.7.3 isolated environment execution.

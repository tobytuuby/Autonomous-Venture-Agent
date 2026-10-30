# CTKFamily Owner Dashboard — independent audit copy

This directory is a **read-only audit snapshot**, not an AVA runtime component. Do not serve or deploy this PHP file from the AVA repository.

- Source repository: `tobytuuby/ctkfamily` (private)
- Source branch: `release/resume-p1-p2-20261019`
- Source commit: `70b0073c93e989bf32c4d17008341e90e2e0a225`
- Original source path: `pages/venture_ideas.php`
- Audit copy: `pages/venture_ideas.php`
- SHA-256 of original and copy (verify before audit): `25051c17e12fa813218aaaf1b1ee892b868f828e02080b61142b5a30505dbbf9`
- AVA Owner API baseline: `f983c57a3e28af20ab24e091e42fdc3b6f9cbf78`

## Scope and limitations

This is the exact CTKFamily file added by the source commit, not a substitute for full review of its runtime dependencies. Shared login/session implementation resides in `config.php`, which is **not copied** because it is outside the CTKFamily change and may contain unrelated configuration. Audit the visible page code and mark assertions dependent on shared login/session configuration as unverified until separately supplied.

This page reads configuration from environment variables and uses PHP cURL, the shared `config.php` session routines, and CTKFamily CSS. No credentials, certificates, or secret values are included in this audit copy. No API service, tunnel, website integration, payment system, or commercial action is activated by copying the file.

The auditor should inspect authentication, CSRF, session handling, service-to-service request construction, URL restriction / SSRF controls, and delegated authorization boundaries. Audit Gate 1 remains conditional pending operational provisioning and independent verification.

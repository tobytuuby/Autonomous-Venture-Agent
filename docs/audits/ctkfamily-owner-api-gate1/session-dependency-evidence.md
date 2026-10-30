# CTKFamily shared session dependency — targeted Gate 1 evidence

Source inspected on CTKFamily VM: `/var/www/ctkfamily/config.php`, current working tree at `70b0073c93e989bf32c4d17008341e90e2e0a225` (outside this audit copy). No full config.php or secret values copied.

Relevant code-level behaviors independently inspected:
- `startSecureSession()` sets `session.use_strict_mode=1`, `session.cookie_httponly=1`, `session.cookie_samesite=Lax`, and calls `session_set_cookie_params(publishingTrackerSessionCookieParams())` before `session_start()`.
- `publishingTrackerSessionCookieParams()` sets lifetime 0, path /, domain empty, httponly true, samesite Lax, and secure according to `publishingTrackerIsHttpsRequest()`.
- HTTPS detection checks `HTTPS`, `HTTP_X_FORWARDED_PROTO`, `HTTP_X_FORWARDED_SSL`, and `SERVER_PORT`.

Security caveat: verification of the HTTP reverse proxy's trusted forwarding-header configuration, actual HTTPS-only access, and browser cookie attributes remains outstanding. Untrusted client-origin forwarding headers must not be accepted as proof of HTTPS. A synchronizer CSRF token is implemented separately in `pages/venture_ideas.php`.

The Owner password verification in `pages/venture_ideas.php` has **no rate limiter visible in that page**. The main CTKFamily `login.php` rate limiter applies to the family passcode, not automatically to Owner re-verification. Treat this as a separate unresolved access-control issue until fixed and tested.

No operational activation is authorized by this evidence.

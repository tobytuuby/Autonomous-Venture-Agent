# Studio Restock Kit — online product requirements v1.1 (preparation draft)

Supersedes the offline objective in OFFER.md for new provider-manager preparation runs. OFFER.md, ZIP, prior decisions and evidence remain historical. Venture #1 remains UNAPPROVED PILOT. No owner receipt, admission, funding, launch or live authority is created. A changed proposal/version/scope requires renewed owner discussion and durable approval before operational execution.

Build an ONLINE application for private staging. Authenticated, tenant-isolated server-side inventory is the source of truth. A static HTML or localStorage-only product fails acceptance. Browser storage may cache presentation only. Product pricing, subscriptions and demand are undecided. Supplier pack prices are user input.

Manager delegates backend AND application to development, independent checks and online acceptance to testing, auth/tenant/CSRF/privacy/recovery review to security. Research stays blocked without an approved facility. Commercial returns unpublished drafts with pricing undecided.

Required: server-verified login, hashed passwords, opaque revocable sessions, tenant derived from session; deny anonymous/cross-tenant reads, writes, exports and deletes. Durable CRUD, bounded numbers, pack-aware reorder, atomic CSV import/export with formula neutralization. Never order supplies. After logout/login in a second independent browser context the same account sees server inventory; another tenant cannot. Persist across backend restart; clearing browser storage must not delete data.

Recovery instructions, authenticated tenant-scoped backup and verified restore, deletion and session revocation are mandatory. Document retention, backup deletion lag, data purpose, privacy and recovery limitations; do not promise erasure from retained backups without evidence. No real customer data, email, analytics, remote assets or supplier integration. UI at /: Studio Restock Kit title, login, inventory editing, reorder review guidance, CSV controls and private preparation label.

## Bounded source and HTTP contract

Development returns app.py, index.html and README.md; optional backend/*.py, backend/*.sql and local .js/.css. Standard library only. No shell, dependencies, credentials or test scripts. app.py exports WSGI callable application(environ,start_response). Use environ["STUDIO_DATA_DIR"] for persistent SQLite/backups. Each request may run in a fresh process. Generated code cannot open sockets or spawn children; the trusted adapter owns HTTP.

Synthetic API: POST /api/register JSON {username,password} creates a separate tenant and session (201). POST /api/login returns session (200). POST /api/logout revokes session (200/204). HttpOnly, SameSite=Strict cookie; Secure required for future HTTPS staging. All mutations require exact same-origin Origin or return 403. Do not trust forwarded headers. No real email/enrollment service.

GET /api/items => JSON list of {id,name,on_hand,inbound,reorder_point,target,pack_size,pack_price}. POST creates (201), PUT /api/items/{id} updates (200), DELETE deletes (200/204). Anonymous protected requests => 401/403; foreign IDs => 403/404. GET /api/reorder => list of {id,packs,quantity,estimate}. Stock=10,inbound=0,point=10,target=20,pack=5,pack_price=3 => packs=2,quantity=10,estimate=6 (inclusive threshold).

GET /api/export => CSV. POST /api/import text/csv => fully validate then atomically import. GET /api/backup => tenant-scoped JSON, POST /api/restore restores fully validated JSON. DELETE /api/account deletes tenant data and revokes sessions. POST /api/recover JSON {username} returns generic non-enumerating 200 response, never a session; document separately verified operator recovery, no email/contact. Backups must not expose other tenants or plaintext passwords.

README names trusted online_checks.py preview harness and 127.0.0.1, recovery steps, retention/privacy/deletion limits. Root HTML must be the integrated UI, not a link-only placeholder. UI uses literal same-origin /api fetch paths; no dynamic target URLs.

Stable UI contract for independent browser testing: #username and #password inputs; #register, #login, #logout buttons. #logout visible only after authentication; #login visible after logout. Inventory editor inputs #item-name, #on-hand, #inbound, #reorder-point, #target, #pack-size, #pack-price; #save-item button persists to server; #inventory shows saved names as exact text. #export-csv triggers a CSV download. Also provide CSV import and editing/deletion UI. Browser tests use synthetic separate tenants and a fresh independent context after logout.

## Execution and acceptance

Trusted harness alone may bind ephemeral 127.0.0.1 and issue bounded same-origin HTTP for synthetic data. Backend requests run inside filesystem/resource/no-network/no-child containment with sanitized environment. Browser intercepts non-origin requests. Arbitrary targets, LAN/metadata/DNS, WebSockets and unrestricted worker HTTP stay denied. Source validation is defense in depth, not runtime safety proof.

Record source hashes, exact commands, per-gate outputs, exits and limitations. Mandatory acceptance: authentication/revocation, tenant CRUD isolation, reorder, atomic CSV, process and independent-browser logout/login continuity, backup/restore, deletion, privacy/security review and real browser UI journey. Missing/failed evidence blocks acceptance. Test adapters prove plumbing only, never actual provider capability/browser passes. Static previews and reload-only checks do not meet online acceptance.

Remote private staging requires a verified existing authorized path with exact target/access/data/rollback boundaries. Otherwise do not deploy. Public launch, payments, customer contact, real CEO and real external effects remain denied; all nine live authorities stay false. ADV-001–ADV-049 and /49 unchanged.

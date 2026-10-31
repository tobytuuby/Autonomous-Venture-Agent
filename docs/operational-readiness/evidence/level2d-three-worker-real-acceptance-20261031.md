# Level2D three-Worker real VM acceptance — 2026-10-31

**PASS for signed preparation-only Level2D hierarchy.** Release baseline `056f2da0f606aecfbecb56ac8185ff36b410d55f`. Control broker and CEO services ran on Venture-Control and Manager/three Workers on Venture-Agents. The owner executed the bounded privileged Agents configuration script; reported source replacement was only hierarchy_gateway.py; inference journals, keys and policies unchanged.

## Verified final signed state
Independent read-only broker replay via `scripts/level2d_acceptance_observe.py`, stored under ignored `artifacts/level2d-acceptance-final.json`, confirms the existing `level2d-multiworker-acceptance-1` sequence:

1. rev1 CEO create
2. rev2 Manager propose_decomposition
3. rev3 CEO approve_decomposition
4. rev4 Worker A submit
5. rev5 Worker B submit
6. rev6 Worker C submit (depends on A and B)
7. rev7 Manager manager_approve
8. rev8 CEO ceo_approve -> **OWNER_REVIEW**

Final snapshot: `used_units=5` of `budget_units=5`; `mode=PREPARATION_ONLY`; `money_released=false`; `operational_authority=false`. The old `level2d-multiworker-remediation-1` state remains `BUDGET_EXHAUSTED`, revision 11 and unmodified.

Central Control SQLite ledger for the new workflow has **four** Worker reservations: Worker B twice and A and C once. All four corresponding Worker execution rows report COMPLETE. This satisfies the unchanged shared ceiling of four, but reveals an unnecessary duplicate B inference due to contemporaneous signed state advancement; refine after acceptance if needed. Never represent this as just three paid calls.

## Existing Owner Dashboard
CTKFamily production `pages/venture_ideas.php` has Owner password verification, CSRF, Approve for Research, Reject and Request Changes and signed CEO research assessments. The existing PHP/cURL tunnel returned HTTP 200 with TLS peer and host verification and three current research statuses. This is research triage only: no signed venture admission/capital approval or full browser acceptance was demonstrated. Status publishing now maps DECOMPOSITION_REVIEW to CEO_DECOMPOSITION_REVIEW without a new endpoint. Owner Dashboard full commercial approval remains a separate acceptance gate.

## Safety and validation
Control suite 1,107 passed; Agents targeted suite 58 passed after staging missing test dependencies. No capital, customer action or release authority was granted. Real CEO/Manager/Worker provider calls occurred. Technical fixture succeeded without raising the existing Worker ceiling. This evidence is a real-VM observation, not independent Claude audit or DR certification.

# Freelance Scope Log live recovery — 2026-11-02

Production workflow: `research-4e6018e70bf43a549e289b3f`.

The read-only forensic inspection found Manager `MANAGER_PENDING` with one pending inference intent in the canonical research directory and one copy under an incorrectly nested research directory. Control broker had no matching Manager reservation or execution for the original pending intent when checked; later CEO session reservation succeeded after the broker's private permissions were restored. Retained all original records, with no workflow rewrite or quota reset.

Source fix `26923e3` prevents duplicate scoped Manager queue ticks and nested research directories, with 102 isolated tests. Code was installed on the existing Agents Manager and A/B/C services and all restarted active. A one-time Manager reconciliation was performed for exactly `manager-cb10dfba80bfc195418cf8c978288bc1c5605b4829e773d2b5` using the existing guarded explicit mechanism after central reservation/execution inspection. The temporary systemd reconciliation override was subsequently removed, daemon reloaded, and Manager restarted active. The original same-scope pending provider request was not deleted.

A previous read-only CEO permission ACL had made broker authority directory `0710` and `resources.sqlite` `0640`, violating owner-private `0700`/`0600` checks and rejecting CEO reservations. The CEO-specific ACL entries were removed, restoring `0700`/`0600`; never broaden broker-private permissions for quota visibility. Commit `dea0205` introduced a read-only count over the existing broker mTLS API, role-limited to quota-ceo, with 176 regression tests passed. It was deployed to existing broker and CEO service code, both active. Live CEO query returned exactly round 1 count 4, venture count 4 for the same signed snapshot.

After recovery, genuine production signed workflow reached A/B/C. Central broker showed 4 completed Worker executions across A, B and C (including two B requests). The signed workflow advanced to revision 9 `WORKER_PENDING`, then CEO signed a `hold` at revision 10 based on authenticated exhausted quota count. No paid calls past 4/round, no new research grant, no external venture operation or launch.

IMPORTANT: Final end-to-end research acceptance is NOT PASS. The CEO research review service subsequently reported `ambiguous CEO provider outcome; manual reconciliation required` at signed `HOLD`. A pending review may represent an already dispatched provider request. DO NOT delete/recreate review intent, blindly retry, or reset quotas. Forensic reconciliation must verify the durable CEO intent/transport/provenance before any further action. Old Client Document Checklist remains immutable; Grant Deadline Calendar has a separate pending Manager intent.

All code commits pushed to `main`. This document records production observations and an unresolved gate, not authorization to bypass the gate.

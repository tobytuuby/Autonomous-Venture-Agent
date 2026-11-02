# Research poll isolation deployment procedure — 2026-11-02

These are operator steps, not executed by this remediation. Use the final pushed
commit reported with this change, after required GitHub/Claude review. This
procedure does not waive existing production gates. No new service is needed.
Restart can allow already-authorized paid work, so do not execute these steps
during read-only diagnosis.

1. Capture sanitized read-only production evidence inside the approved project
   root as specified in the linked review. Verify current signed approval,
   snapshot, original session, identity/request/attempt and reservation/execution
   bindings for both named ventures. Inspect all pending Owner-authorized
   research, not only those two. Do not execute any inference or reservation probe.
2. Verify prerequisites from commits 7788b26, 79f99e3 and dd1dff6 are present in
   the installed broker, CEO and Manager trees. Compare installed module hashes
   to the pinned source, including venture_workflow.py, hierarchy_gateway.py,
   provider_gateway.py and hierarchy_providers.py. The repository working tree
   is dirty; deploy only archived committed source. If prerequisites differ,
   stop this incremental deployment and review the complete source delta.
   Retain existing policies, trust, configs, credentials and all durable ledgers.
3. Export this change from the exact final commit on main into a clean source
   directory under the approved project root. Substitute the final commit hash
   for COMMIT below. Do not use working-tree copies.

   ```sh
   mkdir -p artifacts/research-poll-deploy-source
   git archive COMMIT agents/ceo/hierarchy_service.py agents/ceo/hierarchy_research_daemon.py | tar -x -C artifacts/research-poll-deploy-source
   sha256sum artifacts/research-poll-deploy-source/agents/ceo/hierarchy_service.py artifacts/research-poll-deploy-source/agents/ceo/hierarchy_research_daemon.py
   ```

4. On Control, preserve a rollback copy of each installed file, then install
   exactly the two exported files in the existing CEO tree:

   ```sh
   sudo cp -p /usr/local/lib/venture-ceo-level2c/agents/ceo/hierarchy_service.py /usr/local/lib/venture-ceo-level2c/agents/ceo/hierarchy_service.py.pre-poll-isolation
   sudo cp -p /usr/local/lib/venture-ceo-level2c/agents/ceo/hierarchy_research_daemon.py /usr/local/lib/venture-ceo-level2c/agents/ceo/hierarchy_research_daemon.py.pre-poll-isolation
   sudo install -o root -g root -m 0644 artifacts/research-poll-deploy-source/agents/ceo/hierarchy_service.py /usr/local/lib/venture-ceo-level2c/agents/ceo/hierarchy_service.py
   sudo install -o root -g root -m 0644 artifacts/research-poll-deploy-source/agents/ceo/hierarchy_research_daemon.py /usr/local/lib/venture-ceo-level2c/agents/ceo/hierarchy_research_daemon.py
   ```

5. Transfer the same two exported files to the existing Agents host through the
   approved operational channel and verify identical SHA-256. In that host's
   existing /usr/local/lib/venture-manager-level2c tree, back up and install them
   using the same cp/install commands with that tree as destination. Verify the
   actual installed service WorkingDirectory first; stop if it differs.
   Do not replace any runtime config, signing key or inference database.
6. After matching hashes and existing review gates, restart existing services:

   Control:
   ```sh
   sudo systemctl restart venture-owner-research-ceo.service
   systemctl is-active venture-owner-research-ceo.service
   ```

   Agents:
   ```sh
   sudo systemctl restart venture-owner-research-manager.service
   sudo systemctl restart venture-level2d-worker@worker-a.service venture-level2d-worker@worker-b.service venture-level2d-worker@worker-c.service
   systemctl is-active venture-owner-research-manager.service venture-level2d-worker@worker-a.service venture-level2d-worker@worker-b.service venture-level2d-worker@worker-c.service
   ```

   This incremental change needs no broker restart if the prerequisite hashes
   already match. Do not enable the retired service-worker.
7. Observe existing polls; do not manually issue role ticks or inference calls.
   Verify the legal signed routing event or explicit block reason for each
   legacy task, unchanged approval/session/effort/reservation history, exact
   Manager request identity and no duplicate provider execution. Verify fresh
   signed A/B/C research and restart/replay separately. A running service is
   not evidence of successful research recovery.
8. If blocked, inspect the recorded workflow/hash/reason and original proof.
   Do not repeatedly restart, alter signed records, reset allowance or change
   identity. Rollback code, if needed, restores only the saved source files
   followed by the same service restarts; retain all newly committed signed
   records and durable inference ledgers.

Evidence and limitations:
[review](../tests/acceptance-evidence/research-poll-isolation-20261102/REVIEW.md).

# Production A/B/C research routing deployment — 2026-11-02

## Deployed and observed

- Validated signed bootstrap broker admission and fail-closed denial tests in commit `3e02539`: 13 focused and 166 expanded tests passed in isolated and dirty contexts (see `docs/research-abc-broker-admission-status-20261102.md`). Research routing commit `6a6a018` had 135 isolated tests passed.
- Control installed root-owned `hierarchy_gateway.py` in the existing broker tree, `hierarchy_research_daemon.py` and `owner_research_kickoff.py` in the existing CEO tree; Control comparisons reported exact byte equality for all three. Backups were created with suffix `.pre-abc-20261102`. Broker and CEO research services restarted and were active.
- CEO research public-trust file was updated from the existing broker's A/B/C trust, after checking all three existing actor records were unchanged; it remains private to `venture-ceo`. No signing key material or authority was changed.
- Agents installed `hierarchy_research_daemon.py` from pinned repository `main`, confirmed byte-equal after updating to commit `7325447`. Existing Manager public-trust file was updated to A/B/C trust after verifying identical existing actor records.
- Existing Worker A, B, C systemd template instances received the checked-in `research-abc.conf` ExecStart override to run `hierarchy_research_daemon` with their current role configs, certificates and identities, instead of the old fixed acceptance fixture. All three and the existing research Manager were active. The legacy `venture-owner-research-worker` service was stopped and disabled.
- Code fix `7325447` makes A/B/C skip undecomposed, historically signed single-Worker research rather than repeatedly reporting errors. Nine focused tests passed. Post-restart observation found Manager and A/B/C all active without new logged errors in the bounded sample.
- Unrelated dirty repository files were not staged or committed. Existing ledgers, quotas, policy, signing history, finance and external action restrictions were unchanged.

## Important remaining acceptance boundary

The existing Owner-approved Client Document Checklist workflow `research-5900c3db9bb5bd74601e3f9d` was verified live as `WORKER_PENDING`, `scope.worker_id=service-worker`, without CEO-approved decomposition and without a terminal CEO disposition. Its immutable signed scope cannot be silently rewritten as worker-a or replayed with a second bootstrap identity. The new deployed A/B/C route applies to future properly signed research workflows. **No new Owner-approved A/B/C research workflow was available to exercise a fresh end-to-end production sequence.** Therefore this deployment is NOT a genuine live signed CEO→Manager→A/B→C→Manager→CEO acceptance and Task03's remaining live-decision validation is still open.

Next safe action: Owner reviews and approves an eligible new venture proposal through the CTKFamily Owner page (for example, a proposal still awaiting review). Existing scheduled Owner-feedback publication and kickoff then create a *new* signed worker-a research workflow. Capture real A/B/C assignments, central reservations, signatures, CEO disposition, persistence/restart and CTKFamily rendering. Do not alter the historical Client Document Checklist record or reuse its exhausted/stalled authorization as a new venture grant.

Deployment note: the tracked template drop-in `infrastructure/systemd/venture-level2d-worker@.service.d/research-abc.conf` matches the installed file on Venture-Agents and should be included in recovery/deployment procedures. No new services were created.

# P1-04 two-VM synthetic verification - 2026-11-06

Decision: **Synthetic execution PASS on both VMs; production acceptance remains DENY.**

Source baseline: `8301ace6cfc1cfd7700e3bc1ef39679ac263d926` on `main`.

- Venture-Control: 222 combined C4/C3A/C1, signed recovery, broker restart,
  quotas, ABC routing, and Stage6 regressions passed in 39.279 seconds.
  Evidence: `tests/acceptance-evidence/p1-04-c4-20261106/regression-final.log`
  (local log, not included here).
- Venture-Agents: the tracked C4 source and dependencies were copied from the
  pinned commit into an isolated user-owned source-only directory under
  `/home/epsilon/venture-agents-workspace/candidate-p1-04-8301ace`.
  The same 15 C4 synthetic cases passed in 1.775 seconds. The scratch copy
  required its project-root constant to point to that user-owned directory
  for child-process fixture tests; `agents/ceo/__init__.py` was emptied in
  the isolated subset to remove unrelated package-import dependencies.
  The test and production source files in the Control Git commit were not
  changed by that scratch adaptation.
  Agents log SHA256:
  `f90dc3bcfae222d9c36ca756ce7186748324673a3cd6ac3e591701e18d7ff4f5`.

The C4 fixtures represent two host-labelled namespaces with distinct local
admission controls and test-only credentials. **They do not prove real
cross-host atomic quiescence or installed process adoption.** No production
broker or Manager/Worker process was restarted, deployed, or stopped during this
verification; no live inference, quota reset, ledger update or ambiguous retry
was performed. Workers A/B/C remained inactive. Existing real PENDING execution
records remain held.

The live broker still lacks C1 installed/loaded adoption, active Managers lack
C3A admission adoption, and the source Stage6 gate still returns DENY. The
existing independent review, exhaustive live writer exclusion, loaded-byte
attestation and safe legacy-to-gated bootstrap are not proven. This record must
not be used as deployment approval or a basis for releasing admission.

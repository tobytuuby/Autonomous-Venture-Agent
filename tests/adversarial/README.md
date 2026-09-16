# Genuine P0.15 pre-model adversarial gate

The CEO must not start until this suite has driven the kernel through ADV-001
through ADV-049 with role-bound red-team/test identities and no reasoning model
attached anywhere.

The existing P0.13/P0.14 tests are mechanism and lifecycle fixture coverage;
they are not the certifying 49-test suite and must not be reported as 49/49.
The harness must emit a gate record with status PASS, pass_count 49,
universe 49, pending_count 0, role_bound_red_team_identities true, and
reasoning_model_attached false. Until then, the CEO service remains blocked.

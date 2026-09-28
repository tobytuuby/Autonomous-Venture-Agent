# P9 Focused Test and Evidence Plan

**Version:** 1.0
**Focused denominator:** 48 dynamically registered, individually named unittest cases
**P8 baseline:** 59 cumulative P8 focused tests; 453 full regression as recorded in P8.4 evidence

## Focused case registry

| Family | Cases | Required coverage |
|---|---:|---|
| Valid synthetic contracts | 8 | Four permitted dimensions, deterministic valid values, bounded values, valid observation/recovery records |
| Live authority denial | 9 | One attempted true value for each live authority; each must fail closed |
| Model non-authorization | 5 | Approval-like text, override text, malformed recommendation, prompt-injection-like output, asserted model-authorization flag |
| Charter and isolation | 8 | Unknown/stale charter, charter/venture mismatch, charter/portfolio mismatch, cross-venture identity, cross-portfolio identity, missing binding, mixed identity, context separation |
| Replay and evidence integrity | 6 | Identical replay, changed-material collision, duplicate ordering, out-of-order sequence, tampered evidence hash, missing/malformed hash |
| Recovery and fail-closed | 6 | Freeze, revoke, quarantine, wind-down simulation, injected failure, terminal reopening |
| Mode/schema/no-side-effect | 6 | Invalid mode, malformed record, forbidden field, external action flag, credential/provider/network indicator, terminal stop |
| **Total** | **48** | Each case has an ID, method name, input mutation, expected disposition, and output assertions |

The P9 focused suite target is 48/48. Combined P8+P9 focused target is 107/107. With the unchanged P8.4 full-suite baseline, the expected regression target is 501/501. These totals must be confirmed by actual test discovery and execution; they are not inferred from successful test output alone.

## Evidence contract

Preserve:
- exact repository URL, branch, full HEAD, P8.4 ancestry, clean tracked state, and untracked-file inventory;
- reproducibility commands, Python and dependency versions, environment identity, UTC timestamp, exit code, stdout/stderr;
- a registry mapping each of 48 case IDs to a distinct unittest method and raw result;
- focused and full-regression raw logs and exact discovered/passed/failed counts;
- schema validation, source/test/schema SHA-256 inventories, charter hash and binding, configuration fingerprint;
- canonical input/result hashes, replay key/outcome, sequence, scope, quarantine reason, and recovery state where applicable;
- all nine live fields false; model output non-authoritative; synthetic mode; execution_performed=false; external_action=0; unauthorized_action=0; live_credential=0; provider_calls=0; network_calls=0;
- import/call-path review proving no runtime network, subprocess, credential, filesystem, deployment, provider, worker/venture, or external-action path;
- independent reviewer identity, commands, independently recomputed hashes, findings, limitations, and signed ACCEPTED/BLOCKED disposition.

Canonical evidence uses UTF-8 JSON with sorted keys, compact separators, no NaN/infinity, and SHA-256. The manifest binds path, byte length, and hash for every artifact. Missing, duplicate, changed, mismatched, or unverifiable evidence blocks acceptance. Logs and summaries must not be used as substitutes for source and per-case results.

The evidence proves synthetic test behavior only. It does not demonstrate operational monitoring, live recovery, production readiness, or authority to expand or begin P10.

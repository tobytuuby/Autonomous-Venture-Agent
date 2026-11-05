#!/bin/sh
# Offline synthetic execution; existing runner rejects non-loopback connections.
cd /home/epsilon/venture-control-workspace || exit 1
OUT=tests/acceptance-evidence/p1-04-task-a-20261105
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:integrations/payment_adapter python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_resume_boundary tests.test_ceo_stage6_gate tests.test_ceo_broker tests.test_ceo_pending_recovery tests.test_ceo_candidate_acceptance tests.test_broker_mtls_entrypoint > "$OUT/tests.log" 2>&1
result=$?
printf '%s\n' "$result" > "$OUT/tests.exit"
git diff --check > "$OUT/diff-check.log" 2>&1
diff_result=$?
printf '%s\n' "$diff_result" > "$OUT/diff-check.exit"
test "$result" -eq 0 && test "$diff_result" -eq 0

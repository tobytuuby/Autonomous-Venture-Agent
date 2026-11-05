#!/bin/sh
cd /home/epsilon/venture-control-workspace || exit 1
OUT=tests/acceptance-evidence/p1-04-stage-b-20261105
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:integrations/payment_adapter timeout 150s python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_deployment_resume tests.test_deployment_broker_restart tests.test_resume_boundary tests.test_research_poll_isolation tests.test_ceo_stage6_gate tests.test_ceo_broker tests.test_ceo_pending_recovery tests.test_ceo_candidate_acceptance tests.test_broker_mtls_entrypoint tests.test_hierarchy_service_research > "$OUT/finish-retry.log" 2>&1
result=$?
printf '%s\n' "$result" > "$OUT/finish-retry.exit"
git diff --check > "$OUT/finish-diff-check.log" 2>&1
diff_result=$?
printf '%s\n' "$diff_result" > "$OUT/finish-diff-check.exit"
test "$result" -eq 0 && test "$diff_result" -eq 0

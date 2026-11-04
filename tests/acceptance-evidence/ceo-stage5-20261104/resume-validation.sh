#!/bin/sh
mkdir -p artifacts/ceo-stage5-tmp
export TMPDIR="$PWD/artifacts/ceo-stage5-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:$PWD/tests"
cp tests/acceptance-evidence/ceo-stage5-20261104/candidate-imports.json tests/acceptance-evidence/ceo-stage5-20261104/candidate-imports-before-resume.json
timeout 120s python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_ceo_pending_recovery tests.test_ceo_candidate_acceptance > tests/acceptance-evidence/ceo-stage5-20261104/resume-focused.log 2>&1
rc=$?
echo "$rc" > tests/acceptance-evidence/ceo-stage5-20261104/resume-focused.exit
test "$rc" = 0 || exit "$rc"
timeout 180s python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py --profile tests/acceptance-evidence/ceo-stage5-20261104/candidate_profile.py > tests/acceptance-evidence/ceo-stage5-20261104/resume-candidate.log 2>&1
rc=$?
echo "$rc" > tests/acceptance-evidence/ceo-stage5-20261104/resume-candidate.exit
test "$rc" = 0 || exit "$rc"
timeout 240s python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_broker_isolated_mtls tests.test_broker_mtls_entrypoint tests.test_hierarchy_artifact_store tests.test_hierarchy_runner tests.test_owner_research_admission tests.test_research_continuation tests.test_mvp_handoff tests.test_ceo_pending_recovery tests.test_ceo_research_review tests.test_research_poll_isolation tests.test_research_abc_routing tests.test_research_broker_admission tests.test_hierarchy_service_research tests.test_ceo_durable tests.test_hierarchy_bootstrap tests.test_hierarchy_gateway tests.test_hierarchy_model_callbacks tests.test_hierarchy_multi_worker tests.test_hierarchy_providers tests.test_hierarchy_redirection tests.test_legacy_worker_recovery tests.test_level2c_central_roles tests.test_owner_research_feedback tests.test_owner_research_progress tests.test_owner_research_quota_hold tests.test_preparation_broker tests.test_preparation_exchange tests.test_preparation_service tests.test_provider_dispatch tests.test_provider_dispatch_transport tests.test_research_recovery tests.test_research_reservation_counts tests.test_worker_inference tests.test_ceo_legacy_dependent_replay tests.test_ceo_research_mtls_acceptance tests.test_ceo_three_round_mtls tests.test_ceo_candidate_acceptance > tests/acceptance-evidence/ceo-stage5-20261104/resume-regression.log 2>&1
rc=$?
echo "$rc" > tests/acceptance-evidence/ceo-stage5-20261104/resume-regression.exit
exit "$rc"

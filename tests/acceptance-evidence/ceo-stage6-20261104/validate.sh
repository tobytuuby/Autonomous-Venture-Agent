#!/bin/sh
mkdir -p artifacts/ceo-stage6-tmp
export TMPDIR="$PWD/artifacts/ceo-stage6-tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:$PWD/tests"
out=tests/acceptance-evidence/ceo-stage6-20261104
timeout 60s python3 -B scripts/ceo_stage6_deployment_gate.py --reconstruct > "$out/gate.log" 2>&1
rc=$?
echo "$rc" > "$out/gate.exit"
test "$rc" = 2 || exit 1
timeout 90s python3 -B "$out/strict_installed_dry_run.py" broker tests.test_broker_isolated_mtls > "$out/broker.log" 2>&1
echo "$?" > "$out/broker.exit"
timeout 90s python3 -B "$out/strict_installed_dry_run.py" ceo tests.test_ceo_pending_recovery tests.test_ceo_candidate_acceptance > "$out/ceo.log" 2>&1
echo "$?" > "$out/ceo.exit"
timeout 120s python3 -B tests/acceptance-evidence/ceo-stage5-20261104/verify_synthetic.py tests.test_ceo_stage6_gate tests.test_ceo_pending_recovery tests.test_ceo_candidate_acceptance > "$out/regression.log" 2>&1
rc=$?
echo "$rc" > "$out/regression.exit"
test "$rc" = 0 || exit "$rc"
git diff --check

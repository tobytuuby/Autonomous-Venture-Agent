#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"
export PYTHONPATH="$repo_root"
python3 -m unittest discover -s tests
role="$(sudo -u postgres psql -X -Atqc "SELECT rolname FROM pg_roles WHERE rolname='venture-broker' AND rolsuper=false AND rolcreatedb=false AND rolcreaterole=false AND rolcanlogin=true")"
test "$role" = "venture-broker"
job_id="$(cat /proc/sys/kernel/random/uuid)"
key="p07-cert-${job_id}"
sudo -u venture-broker env PYTHONPATH=/usr/local/lib/venture-control-broker JOB_ID="$job_id" IDEMPOTENCY_KEY="$key" python3 - <<'PY'
import os
from postgres_queue import PostgresJobQueue
q = PostgresJobQueue()
job = q.enqueue(os.environ["JOB_ID"], os.environ["IDEMPOTENCY_KEY"], {"certification": "p07"})
assert job["status"] == "queued"
claimed = q.claim("p07-cert-worker")
assert claimed and claimed["status"] == "claimed" and claimed["attempts"] == 1
assert q.complete(claimed["job_id"]) is True
assert q.complete(claimed["job_id"]) is False
print("postgres_queue=PASS")
PY
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -c "DELETE FROM agent_jobs WHERE idempotency_key='${key}';" >/dev/null
systemctl is-active --quiet venture-control-broker.service
echo "P07_CERTIFICATION=PASS"

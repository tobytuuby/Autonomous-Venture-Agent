#!/usr/bin/env bash
set -euo pipefail

: "${CHECKPOINT_DESTINATION:?Set CHECKPOINT_DESTINATION to an off-box checkpoint directory}"
CHECKPOINT_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CHECKPOINT_FILE="${CHECKPOINT_DESTINATION%/}/ledger-head-${CHECKPOINT_STAMP}.json"
TMP_DIR="$(mktemp -d /var/tmp/venture-control-checkpoint.XXXXXX)"
TMP_FILE="${TMP_DIR}/checkpoint.json"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

chown postgres:postgres "${TMP_DIR}"
chmod 0700 "${TMP_DIR}"
mkdir -p "${CHECKPOINT_DESTINATION}"

runuser -u postgres -- psql -X -Atqc "
SELECT json_build_object(
  'generated_at', now(),
  'database', current_database(),
  'operational_event_count', (SELECT count(*) FROM operational_events),
  'operational_event_head', (SELECT event_hash FROM operational_events ORDER BY event_seq DESC LIMIT 1),
  'accounting_entry_count', (SELECT count(*) FROM accounting_ledger),
  'accounting_entry_head', (SELECT entry_hash FROM accounting_ledger ORDER BY entry_seq DESC LIMIT 1)
)::text;
" > "${TMP_FILE}"

cp "${TMP_FILE}" "${CHECKPOINT_FILE}"
chmod 0600 "${CHECKPOINT_FILE}"
printf '%s\n' "${CHECKPOINT_FILE}"

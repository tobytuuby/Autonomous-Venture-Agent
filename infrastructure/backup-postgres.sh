#!/usr/bin/env bash
set -euo pipefail

: "${BACKUP_DESTINATION:?Set BACKUP_DESTINATION to an off-box backup directory or mounted destination}"
BACKUP_DATABASE="${BACKUP_DATABASE:-postgres}"
BACKUP_HOST="${BACKUP_HOST:-}"
BACKUP_USER="${BACKUP_USER:-postgres}"
BACKUP_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DESTINATION%/}/venture-control-${BACKUP_DATABASE}-${BACKUP_STAMP}.dump"
TMP_DIR="$(mktemp -d /var/tmp/venture-control-pgbackup.XXXXXX)"
TMP_FILE="${TMP_DIR}/backup.dump"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

chown postgres:postgres "${TMP_DIR}"
chmod 0700 "${TMP_DIR}"
mkdir -p "${BACKUP_DESTINATION}"
runuser -u postgres -- pg_dump --format=custom --file="${TMP_FILE}" \
  ${BACKUP_HOST:+--host="${BACKUP_HOST}"} \
  --username="${BACKUP_USER}" "${BACKUP_DATABASE}"

cp "${TMP_FILE}" "${BACKUP_FILE}"
chmod 0600 "${BACKUP_FILE}"
printf '%s\n' "${BACKUP_FILE}"

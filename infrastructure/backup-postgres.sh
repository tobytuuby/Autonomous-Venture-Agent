#!/usr/bin/env bash
set -euo pipefail

: "${BACKUP_DESTINATION:?Set BACKUP_DESTINATION to an off-box backup directory or mounted destination}"
BACKUP_DATABASE="${BACKUP_DATABASE:-postgres}"
BACKUP_HOST="${BACKUP_HOST:-}"
BACKUP_USER="${BACKUP_USER:-postgres}"
BACKUP_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DESTINATION%/}/venture-control-${BACKUP_DATABASE}-${BACKUP_STAMP}.dump"

mkdir -p "${BACKUP_DESTINATION}"
pg_dump --format=custom --file="${BACKUP_FILE}" \
  ${BACKUP_HOST:+--host="${BACKUP_HOST}"} \
  --username="${BACKUP_USER}" "${BACKUP_DATABASE}"

chmod 0600 "${BACKUP_FILE}"
printf '%s\n' "${BACKUP_FILE}"

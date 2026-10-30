#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 /usr/local/lib/venture-backup/backup_sqlite_state.py \
 --destination /var/backups/venture-agents/venture-agents/sqlite-workflow \
 --identity venture-agents \
 --source /var/lib/venture-manager/level2d \
 --source /var/lib/venture-worker/level2d

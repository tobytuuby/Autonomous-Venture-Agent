#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 /usr/local/lib/venture-backup/backup_sqlite_state.py \
 --destination /var/backups/venture-control/sqlite-workflow \
 --identity venture-control \
 --source /var/lib/venture-review/inbox \
 --source /usr/local/lib/venture-ceo-level2c/artifacts \
 --source /usr/local/lib/venture-control-broker-level2c/artifacts \
 --source /var/lib/venture-control-broker

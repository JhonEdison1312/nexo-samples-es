#!/bin/bash
# drop_old_partitions.sh - I-2: invocador de fn_drop_old_partitions (retención).
# Sin este cron la función existía pero nadie la llamaba — biometric_events y
# las auditorías crecían para siempre. Corre mensualmente vía crontab.
# Retención: NEXO_PARTITION_RETENTION_MONTHS (predeterminado 24).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/../logs/partition_retention.log"
mkdir -p "$(dirname "$LOG_FILE")"
log() { echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"; }

if [ -z "${DATABASE_URL:-}" ] && [ -f "${SCRIPT_DIR}/../.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/../.env" | xargs)
fi
ADMIN_DSN="${ADMIN_DATABASE_URL:-${DATABASE_URL:-}}"
if [ -z "$ADMIN_DSN" ]; then
    log "ERROR: ADMIN_DATABASE_URL/DATABASE_URL no está configurada"; exit 1
fi

RETENTION="${NEXO_PARTITION_RETENTION_MONTHS:-24}"
DROPPED=$(psql "$ADMIN_DSN" -t -c "SELECT fn_drop_old_partitions(${RETENTION});" 2>&1 | xargs)
log "Retención ${RETENTION} meses — particiones eliminadas: ${DROPPED}"


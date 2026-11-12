#!/bin/bash
# create_monthly_partition.sh - Crea particiones mensuales para las 8 tablas
# particionadas de NEXO. Uso: ./create_monthly_partition.sh [YYYY-MM] [tabla]
# Sin argumentos crea la partición del mes siguiente en TODAS las tablas.
# I-2: antes solo cubría biometric_events — las otras 7 acumulaban todo en su
# partición DEFAULT (sin posibilidad de pruning y fuera del alcance de retención).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/../logs/partition_creation.log"
mkdir -p "$(dirname "$LOG_FILE")"
log() { echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"; }

if [ -z "${DATABASE_URL:-}" ] && [ -f "${SCRIPT_DIR}/../.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/../.env" | xargs)
fi
# SEC-2: DDL administrativo — requiere ADMIN_DATABASE_URL (rol con DDL);
# DATABASE_URL solo en despliegues legacy de rol único.
ADMIN_DSN="${ADMIN_DATABASE_URL:-${DATABASE_URL:-}}"
if [ -z "$ADMIN_DSN" ]; then
    log "ERROR: ADMIN_DATABASE_URL/DATABASE_URL no está configurada"; exit 1
fi

# tabla:columna_de_rango — los 8 padres particionados del esquema
declare -A PARTS=(
    [biometric_events]=event_timestamp
    [attendance_incidents]=detected_at
    [internal_messages]=sent_at
    [twilio_messages]=sent_at
    [user_commands]=executed_at
    [sos_alerts]=emitted_at
    [student_record_audit]=performed_at
    [global_audit_logs]=created_at
)

TARGET_MONTH="${1:-$(date -d "+1 month" +%Y-%m)}"
ONLY_TABLE="${2:-}"
YEAR="${TARGET_MONTH:0:4}"; MONTH="${TARGET_MONTH:5:2}"
P_START="${YEAR}-${MONTH}-01"
P_END=$(date -d "${P_START} +1 month" +%Y-%m-%d)

fail=0
for TBL in "${!PARTS[@]}"; do
    [ -n "$ONLY_TABLE" ] && [ "$ONLY_TABLE" != "$TBL" ] && continue
    PNAME="${TBL}_${YEAR}_${MONTH}"
    EXISTS=$(psql "$ADMIN_DSN" -t -c "SELECT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname='${PNAME}' AND n.nspname='public');" 2>&1 | xargs)
    if [ "$EXISTS" = "t" ]; then
        log "La partición ${PNAME} ya existe."
        continue
    fi
    if psql "$ADMIN_DSN" -c "CREATE TABLE IF NOT EXISTS ${PNAME} PARTITION OF ${TBL} FOR VALUES FROM ('${P_START}') TO ('${P_END}');" >>"$LOG_FILE" 2>&1; then
        log "Partición ${PNAME} creada [${P_START}, ${P_END})."
    else
        log "ERROR: no se pudo crear ${PNAME}"; fail=1
    fi
done
exit $fail

#!/usr/bin/env bash
# AÑADIDO PARA ESTA MUESTRA
# Prueba la verificación de integridad de la cadena de auditoría y la
# detección de manipulaciones:
# 1. Cadena válida -> status: ok
# 2. Manipulación de un registro intermedio -> status: compromised
# 3. Eliminación de un registro -> status: compromised
# 4. Reordenación de registros -> status: compromised
# Cada comprobación es una aserción real; el banner solo se imprime si todas pasan.
set -uo pipefail

PG_HOST="${NEXO_PG_HOST:-127.0.0.1}"
PG_PORT="${NEXO_PG_PORT:-15432}"
DB_NAME="${NEXO_DB_NAME:-nexo}"
DB_USER="${NEXO_DB_USER:-nexo_app}"
export PGPASSWORD="${NEXO_DB_PASSWORD:-nexo_secret}"
SOCKET_DIR="${NEXO_SOCKET_DIR:-/tmp/nexo_env/sockets}"
FAIL=0

if [[ -d "${SOCKET_DIR}" ]]; then
    PSQL_CMD=(psql -h "${SOCKET_DIR}" -p "${PG_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -A -t -q)
else
    PSQL_CMD=(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -A -t -q)
fi

json_status() {
    printf '%s' "$1" | grep -o '"status"[^,}]*' | head -n1 | sed 's/.*"status"[[:space:]]*:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}.*/\1/'
}

check() {
    local name="$1" actual="$2" expected="$3"
    if [[ "${actual}" == "${expected}" ]]; then
        echo "  [PASS] ${name}: status=${actual}"
    else
        echo "  [FAIL] ${name}: esperado status=${expected}, obtenido '${actual}'"
        FAIL=1
    fi
}

echo "=== DEMO DE VERIFICACIÓN: 02-AUDIT-CHAIN ==="
echo "Objetivo: ${DB_NAME} como ${DB_USER}"

"${PSQL_CMD[@]}" -c "SELECT set_config('app.nexo_hmac_secret', 'nexo-audit-hmac-sha256-secret-key-32b', false);" >/dev/null

SEED_SQL='SELECT set_config('"'"'app.nexo_hmac_secret'"'"', '"'"'nexo-audit-hmac-sha256-secret-key-32b'"'"', false);
TRUNCATE TABLE global_audit_logs;
INSERT INTO global_audit_logs (school_id, performed_by_user_id, action_type, action_details, ip_address, created_at)
VALUES
  ('"'"'11111111-1111-1111-1111-111111111111'"'"', '"'"'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"'"', '"'"'AUTH_LOGIN'"'"', '"'"'{"method": "password"}'"'"', '"'"'10.0.0.1'"'"', NOW() + INTERVAL '"'"'1 second'"'"'),
  ('"'"'11111111-1111-1111-1111-111111111111'"'"', '"'"'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"'"', '"'"'STUDENT_VIEW'"'"', '"'"'{"student_id": 101}'"'"', '"'"'10.0.0.1'"'"', NOW() + INTERVAL '"'"'2 seconds'"'"'),
  ('"'"'11111111-1111-1111-1111-111111111111'"'"', '"'"'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"'"', '"'"'ATTENDANCE_OVERRIDE'"'"', '"'"'{"record_id": 55}'"'"', '"'"'10.0.0.1'"'"', NOW() + INTERVAL '"'"'3 seconds'"'"'),
  ('"'"'11111111-1111-1111-1111-111111111111'"'"', '"'"'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"'"', '"'"'REPORT_GENERATE'"'"', '"'"'{"report": "monthly"}'"'"', '"'"'10.0.0.1'"'"', NOW() + INTERVAL '"'"'4 seconds'"'"'),
  ('"'"'11111111-1111-1111-1111-111111111111'"'"', '"'"'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'"'"', '"'"'AUTH_LOGOUT'"'"', '"'"'{"duration": 1800}'"'"', '"'"'10.0.0.1'"'"', NOW() + INTERVAL '"'"'5 seconds'"'"');'

validate() {
    "${PSQL_CMD[@]}" <<'SQL' | tail -n1
SELECT set_config('app.nexo_hmac_secret', 'nexo-audit-hmac-sha256-secret-key-32b', false);
SELECT fn_validate_audit_chain();
SQL
}

echo ""
echo "--- TEST 1: Generación de cadena secuencial válida ---"
echo "${SEED_SQL}" | "${PSQL_CMD[@]}" >/dev/null
echo "Se insertaron 5 eventos de auditoría secuenciales."
RES_1_JSON=$(validate)
echo "Resultado de la validación: ${RES_1_JSON}"
check "TEST 1 cadena válida" "$(json_status "${RES_1_JSON}")" "ok"

echo ""
echo "--- TEST 2: Detección de manipulación de un registro intermedio ---"
"${PSQL_CMD[@]}" <<'SQL' >/dev/null
SELECT set_config('app.nexo_hmac_secret', 'nexo-audit-hmac-sha256-secret-key-32b', false);
ALTER TABLE global_audit_logs DISABLE TRIGGER trg_audit_chain;
UPDATE global_audit_logs SET action_details = '{"record_id": 55, "tampered": true}' WHERE action_type = 'ATTENDANCE_OVERRIDE';
ALTER TABLE global_audit_logs ENABLE TRIGGER trg_audit_chain;
SQL
echo "Se modificó directamente en la base de datos el payload del evento intermedio ('ATTENDANCE_OVERRIDE')."
RES_2_JSON=$(validate)
echo "Resultado de la validación: ${RES_2_JSON}"
check "TEST 2 manipulación intermedia" "$(json_status "${RES_2_JSON}")" "compromised"

echo ""
echo "--- TEST 3: Detección de eliminación de un registro ---"
echo "${SEED_SQL}" | "${PSQL_CMD[@]}" >/dev/null
"${PSQL_CMD[@]}" <<'SQL' >/dev/null
SELECT set_config('app.nexo_hmac_secret', 'nexo-audit-hmac-sha256-secret-key-32b', false);
ALTER TABLE global_audit_logs DISABLE TRIGGER trg_audit_chain;
DELETE FROM global_audit_logs WHERE action_type = 'ATTENDANCE_OVERRIDE';
ALTER TABLE global_audit_logs ENABLE TRIGGER trg_audit_chain;
SQL
echo "Se eliminó el evento n.º 3 ('ATTENDANCE_OVERRIDE') de la secuencia."
RES_3_JSON=$(validate)
echo "Resultado de la validación: ${RES_3_JSON}"
check "TEST 3 eliminación" "$(json_status "${RES_3_JSON}")" "compromised"

echo ""
echo "--- TEST 4: Detección de reordenación de registros ---"
"${PSQL_CMD[@]}" <<'SQL' >/dev/null
SELECT set_config('app.nexo_hmac_secret', 'nexo-audit-hmac-sha256-secret-key-32b', false);
TRUNCATE TABLE global_audit_logs;
INSERT INTO global_audit_logs (school_id, performed_by_user_id, action_type, action_details, ip_address, created_at)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'AUTH_LOGIN', '{"method": "password"}', '10.0.0.1', NOW() + INTERVAL '1 second'),
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'STUDENT_VIEW', '{"student_id": 101}', '10.0.0.1', NOW() + INTERVAL '2 seconds'),
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ATTENDANCE_OVERRIDE', '{"record_id": 55}', '10.0.0.1', NOW() + INTERVAL '3 seconds'),
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'REPORT_GENERATE', '{"report": "monthly"}', '10.0.0.1', NOW() + INTERVAL '4 seconds'),
  ('11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'AUTH_LOGOUT', '{"duration": 1800}', '10.0.0.1', NOW() + INTERVAL '5 seconds');
ALTER TABLE global_audit_logs DISABLE TRIGGER trg_audit_chain;
UPDATE global_audit_logs SET created_at = NOW() + INTERVAL '10 seconds' WHERE action_type = 'AUTH_LOGIN';
ALTER TABLE global_audit_logs ENABLE TRIGGER trg_audit_chain;
SQL
echo "Se movió la marca de tiempo del evento n.º 1 ('AUTH_LOGIN') más allá del evento n.º 5, rompiendo la secuencia de la cadena."
RES_4_JSON=$(validate)
echo "Resultado de la validación: ${RES_4_JSON}"
check "TEST 4 reordenación" "$(json_status "${RES_4_JSON}")" "compromised"

echo ""
if [[ "${FAIL}" -eq 0 ]]; then
    echo "=== DEMO 02-AUDIT-CHAIN COMPLETADA: TODAS LAS COMPROBACIONES PASARON ==="
    exit 0
fi
echo "=== DEMO 02-AUDIT-CHAIN COMPLETADA: SE PRODUJERON FALLOS ==="
exit 1

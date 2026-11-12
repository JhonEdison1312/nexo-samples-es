#!/usr/bin/env bash
# AÑADIDO PARA ESTA MUESTRA
# Prueba el aislamiento de tenants con RLS y el comportamiento de
# reutilización de conexiones de PgBouncer.
# Cada comprobación es una aserción real; el banner solo se imprime si todas pasan.
set -uo pipefail

PGBOUNCER_HOST="${NEXO_PGBOUNCER_HOST:-127.0.0.1}"
PGBOUNCER_PORT="${NEXO_PGBOUNCER_PORT:-16432}"
DB_NAME="${NEXO_DB_NAME:-nexo}"
DB_USER="${NEXO_DB_USER:-nexo_app}"
export PGPASSWORD="${NEXO_DB_PASSWORD:-nexo_secret}"
FAIL=0

run_query() {
    psql -h "${PGBOUNCER_HOST}" -p "${PGBOUNCER_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 -A -t "$@"
}

# last_row: modo silencioso + tail -n1 para que las etiquetas BEGIN/COMMIT/SET
# nunca contaminen una aserción de conteo.
last_row() {
    run_query -q "$@" | tail -n1
}

check() { # check <test-name> <actual> <expected>
    local name="$1" actual="$2" expected="$3"
    if [[ "${actual}" == "${expected}" ]]; then
        echo "  [PASS] ${name}"
    else
        echo "  [FAIL] ${name}: esperado '${expected}', obtenido '${actual}'"
        FAIL=1
    fi
}

echo "=== DEMO DE VERIFICACIÓN: 01-RLS-PGBOUNCER ==="
echo "Conectado a través de PgBouncer: ${PGBOUNCER_HOST}:${PGBOUNCER_PORT} como rol '${DB_USER}'"

echo ""
echo "--- TEST 0: Verificar que current_user es un rol de aplicación NOSUPERUSER ---"
CURRENT_USER=$(run_query -c "SELECT current_user;")
IS_SUPERUSER=$(run_query -c "SELECT usesuper FROM pg_user WHERE usename = current_user;")
echo "current_user: ${CURRENT_USER}"
echo "is_superuser: ${IS_SUPERUSER}"
check "current_user es nexo_app" "${CURRENT_USER}" "nexo_app"
check "el usuario NO es superusuario" "${IS_SUPERUSER}" "f"

echo ""
echo "--- TEST 1: La configuración a nivel de sesión se filtra entre conexiones (la vulnerabilidad) ---"
echo "El cliente A establece app.current_school_id a nivel de sesión (sin ámbito de transacción):"
run_query -c "SET app.current_school_id = '11111111-1111-1111-1111-111111111111';" >/dev/null
echo "Configuración de sesión del cliente A completada."

echo "El cliente B abre una nueva conexión a PgBouncer e inspecciona app.current_school_id:"
LEAKED_GUC=$(run_query -c "SELECT COALESCE(current_setting('app.current_school_id', true), '<empty>');")
echo "El cliente B observó el GUC: ${LEAKED_GUC}"
check "el GUC a nivel de sesión se filtra entre conexiones del pool" "${LEAKED_GUC}" "11111111-1111-1111-1111-111111111111"

# Restablece el estado de la conexión backend para las pruebas siguientes
run_query -c "RESET app.current_school_id;" >/dev/null 2>&1

echo ""
echo "--- TEST 2: set_config(..., true) / SET LOCAL con ámbito de transacción (el patrón seguro) ---"
echo "El cliente A establece app.current_school_id dentro de un bloque BEGIN/COMMIT con is_local=true:"
run_query -q <<'SQL' >/dev/null
BEGIN;
SELECT set_config('app.current_school_id', '22222222-2222-2222-2222-222222222222', true);
COMMIT;
SQL
echo "Transacción del cliente A confirmada."

echo "El cliente B abre una nueva conexión a PgBouncer e inspecciona app.current_school_id:"
ISOLATED_GUC=$(run_query -c "SELECT COALESCE(NULLIF(current_setting('app.current_school_id', true), ''), '<empty>');")
echo "El cliente B observó el GUC: ${ISOLATED_GUC}"
check "el GUC con ámbito de transacción NO se filtra" "${ISOLATED_GUC}" "<empty>"

echo ""
echo "--- TEST 3: Aislamiento de tenants con Row-Level Security ---"
echo "Consulta 3a: lectura sin contexto configurado:"
NO_CTX_COUNT=$(last_row -c "SELECT count(*) FROM students;")
echo "Filas visibles: ${NO_CTX_COUNT}"
check "la lectura sin contexto devuelve 0 filas (RLS deniega por defecto)" "${NO_CTX_COUNT}" "0"

echo "Consulta 3b: lectura con contexto de la Escuela A ('11111111-1111-1111-1111-111111111111'):"
run_query -q <<'SQL' | tail -n +2
BEGIN;
SELECT set_config('app.current_school_id', '11111111-1111-1111-1111-111111111111', true);
SELECT school_id || ' | ' || first_name || ' ' || last_name FROM students ORDER BY first_name;
COMMIT;
SQL

echo "Consulta 3c: intento de lectura entre tenants (consultando la Escuela B con ámbito de la Escuela A):"
CROSS_COUNT=$(last_row <<'SQL'
BEGIN;
SELECT set_config('app.current_school_id', '11111111-1111-1111-1111-111111111111', true);
SELECT count(*) FROM students WHERE school_id = '22222222-2222-2222-2222-222222222222';
COMMIT;
SQL
)
echo "Filas entre tenants devueltas: ${CROSS_COUNT}"
check "la lectura entre tenants devuelve 0 filas" "${CROSS_COUNT}" "0"

echo "Consulta 3d: lectura con contexto de la Escuela B ('22222222-2222-2222-2222-222222222222'):"
run_query -q <<'SQL' | tail -n +2
BEGIN;
SELECT set_config('app.current_school_id', '22222222-2222-2222-2222-222222222222', true);
SELECT school_id || ' | ' || first_name || ' ' || last_name FROM students ORDER BY first_name;
COMMIT;
SQL

echo ""
echo "--- TEST 4: GUC vacío tras COMMIT (misma conexión) ---"
run_query -q <<'SQL'
BEGIN;
SELECT set_config('app.current_school_id', '11111111-1111-1111-1111-111111111111', true);
COMMIT;
SELECT 'Valor del GUC tras COMMIT: ' || COALESCE(NULLIF(current_setting('app.current_school_id', true), ''), '<empty>');
SQL

echo ""
if [[ "${FAIL}" -eq 0 ]]; then
    echo "=== DEMO 01-RLS-PGBOUNCER COMPLETADA: TODAS LAS COMPROBACIONES PASARON ==="
    exit 0
fi
echo "=== DEMO 01-RLS-PGBOUNCER COMPLETADA: SE PRODUJERON FALLOS ==="
exit 1

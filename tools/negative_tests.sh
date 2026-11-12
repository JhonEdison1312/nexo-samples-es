#!/usr/bin/env bash
# ADDED FOR THIS SAMPLE
# Controles negativos: demuestran que cada prueba falla de verdad cuando lo
# que verifica está roto. Cada sabotaje DEBE producir una salida de test
# distinta de cero; el entorno se restaura tras cada caso. Termina con
# código distinto de cero si algún sabotaje pasa inadvertido.
#
# Uso: primero tools/env/up.sh (o este script lo arranca), luego:
#   bash tools/negative_tests.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit

PSQL_ADMIN=(psql -h /tmp -p 15432 -U nexo_admin -d nexo -v ON_ERROR_STOP=1 -q)
PASS=0; FAIL=0

restore_env() {
    tools/env/up.sh >/dev/null 2>&1
}

expect_fail() { # expect_fail <nombre> <comando...>
    local name="$1"; shift
    echo ""
    echo "=== NEGATIVO: $name ==="
    "$@" > /tmp/neg_last.log 2>&1
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "[PASA] el test salió con código distinto de cero ($rc) como se requiere"
        tail -n 8 /tmp/neg_last.log | sed 's/^/    /'
        PASS=$((PASS+1))
    else
        echo "[FALLA] el test PASÓ a pesar del sabotaje — la aserción no es real"
        FAIL=$((FAIL+1))
    fi
}

# Asegurar que el entorno está activo
if ! pg_isready -h /tmp -p 15432 >/dev/null 2>&1; then
    tools/env/up.sh >/dev/null
fi

echo "=== PRUEBAS NEGATIVAS: cada sabotaje debe ser detectado ==="

# --- 1. RLS desactivado -> test-01 debe fallar (las filas sin contexto se vuelven visibles)
echo ""
echo "--- sabotaje: DISABLE ROW LEVEL SECURITY en students ---"
"${PSQL_ADMIN[@]}" -c "ALTER TABLE students DISABLE ROW LEVEL SECURITY;"
expect_fail "RLS desactivado (test-01)" make test-01
"${PSQL_ADMIN[@]}" -c "ALTER TABLE students ENABLE ROW LEVEL SECURITY;"

# --- 2. Función de cadena de auditoría eliminada -> test-02 debe fallar
echo ""
echo "--- sabotaje: DROP FUNCTION fn_validate_audit_chain ---"
"${PSQL_ADMIN[@]}" -c "DROP FUNCTION IF EXISTS fn_validate_audit_chain(uuid);"
expect_fail "fn de cadena de auditoría eliminada (test-02)" make test-02
restore_env  # recarga src/audit_chain_trigger.sql

# --- 3. Redis caído -> test-03 debe fallar con 'Redis is down', test-05 debe fallar
echo ""
echo "--- sabotaje: Redis parado ---"
redis-cli -p 16379 shutdown nosave >/dev/null 2>&1 || true
sleep 1
expect_fail "Redis caído (test-03)" make test-03
if grep -qi "redis is down" /tmp/neg_last.log; then
    echo "[PASA] el mensaje de fallo menciona que Redis está caído"
    PASS=$((PASS+1))
else
    echo "[FALLA] el fallo no reportó claramente que Redis estaba caído"
    FAIL=$((FAIL+1))
fi
expect_fail "Redis caído (test-05)" python3 samples/05-redis-reliable-queue/harness/test_queue.py
restore_env

# --- 4. Función de retención de particiones eliminada -> test-06 debe fallar
echo ""
echo "--- sabotaje: DROP FUNCTION fn_drop_old_partitions ---"
"${PSQL_ADMIN[@]}" -c "DROP FUNCTION IF EXISTS fn_drop_old_partitions(integer);"
expect_fail "fn de particiones eliminada (test-06)" make test-06
restore_env

# --- cordura: entorno restaurado, todos los tests vuelven a pasar
echo ""
echo "=== COMPROBACIÓN DE RESTAURACIÓN: los tests deben volver a pasar ==="
for t in test-01 test-02 test-03 test-05 test-06; do
    if make "$t" >/dev/null 2>&1; then
        echo "[PASA] $t pasa tras la restauración"
        PASS=$((PASS+1))
    else
        echo "[FALLA] $t sigue fallando tras la restauración"
        FAIL=$((FAIL+1))
    fi
done

echo ""
echo "=== RESUMEN DE PRUEBAS NEGATIVAS ==="
echo "comprobaciones pasadas: $PASS"
echo "comprobaciones fallidas: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "PRUEBAS NEGATIVAS: FALLA"
    exit 1
fi
echo "PRUEBAS NEGATIVAS: TODOS LOS SABOTAJES DETECTADOS"
exit 0

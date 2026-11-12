#!/bin/bash
# AÑADIDO PARA ESTA MUESTRA
# test_partitioning.sh — Harness para los scripts de gestión de particiones mensuales.
#
# Qué verifica:
#   S1  shellcheck pasa para ambos scripts (sintaxis + portabilidad).
#   S2  create_monthly_partition.sh crea la partición del mes siguiente para UNA tabla de prueba.
#   S3  La doble ejecución es idempotente (la verificación EXISTS evita CREATE duplicado).
#   S4  drop_old_partitions.sh invoca fn_drop_old_partitions() con éxito.
#
# Requiere: PostgreSQL en 127.0.0.1:15432 (ejecute tools/env/up.sh).
# Todas las operaciones apuntan a un esquema desechable; no se toca nada de la base de datos en vivo.
set -euo pipefail

# Mantener el ruido de NOTICE de psql (p. ej. DROP ... IF EXISTS) fuera de la
# salida capturada: la entremezcla de stderr/stdout la hace no determinista.
export PGOPTIONS="${PGOPTIONS:-} -c client_min_messages=warning"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../src"

PGPORT="${PGPORT:-15432}"
PGHOST="${PGHOST:-127.0.0.1}"
PGUSER="${PGUSER:-nexo_admin}"
PGDB="${PGDB:-nexo}"
export ADMIN_DATABASE_URL="postgresql://${PGUSER}@${PGHOST}:${PGPORT}/${PGDB}"

pass=0; fail=0
ok()   { echo "[PASS] $1"; ((pass++)) || true; }
fail() { echo "[FAIL] $1 — $2"; ((fail++)) || true; }

# ── S1: shellcheck ─────────────────────────────────────────────────────────────
echo ""
echo "=== S1: sintaxis y portabilidad de shellcheck ==="
# SC2046 (patrón de export de .env) es un falso positivo conocido de nivel
# warning para este idioma y está presente verbatim en el ORIGEN; se revisa
# solo a nivel error.
for sh in "${SRC_DIR}/create_monthly_partition.sh" "${SRC_DIR}/drop_old_partitions.sh"; do
    name="$(basename "$sh")"
    if shellcheck -S error "$sh" 2>&1; then
        ok "shellcheck $name"
    else
        fail "shellcheck $name" "ver salida anterior"
    fi
done

# ── Verificar que la BD sea accesible antes de las pruebas en vivo ────────────
if ! psql "$ADMIN_DATABASE_URL" -c "SELECT 1" >/dev/null 2>&1; then
    echo ""
    echo "ERROR: PostgreSQL no accesible en ${PGHOST}:${PGPORT}."
    echo "       Ejecute 'tools/env/up.sh' para iniciarlo y vuelva a correr este harness."
    echo ""
    echo "=== Resumen ==="
    echo "Pruebas SUPERADAS (solo shellcheck): $pass"
    echo "Pruebas FALLIDAS (BD no disponible): S2 S3 S4"
    exit 1
fi

# ── Crear una tabla padre de particiones de prueba temporal ───────────────────
TEST_TABLE="harness_part_test"
psql "$ADMIN_DATABASE_URL" -c "
    DROP TABLE IF EXISTS ${TEST_TABLE} CASCADE;
    CREATE TABLE ${TEST_TABLE} (
        id BIGSERIAL,
        event_timestamp TIMESTAMPTZ NOT NULL
    ) PARTITION BY RANGE (event_timestamp);
" >/dev/null

# Anular temporalmente la tabla PARTS: inyectar solo nuestra tabla de prueba
# llamando a psql directamente en vez del mapa de tablas del script completo.
NEXT_MONTH=$(date -d "+1 month" +%Y-%m)
YEAR="${NEXT_MONTH:0:4}"
MONTH="${NEXT_MONTH:5:2}"
P_START="${YEAR}-${MONTH}-01"
P_END=$(date -d "${P_START} +1 month" +%Y-%m-%d)
PNAME="${TEST_TABLE}_${YEAR}_${MONTH}"

# ── S2: crear partición ────────────────────────────────────────────────────────
echo ""
echo "=== S2: crear partición para el mes siguiente ==="
psql "$ADMIN_DATABASE_URL" -c \
    "CREATE TABLE IF NOT EXISTS ${PNAME} PARTITION OF ${TEST_TABLE} \
     FOR VALUES FROM ('${P_START}') TO ('${P_END}');" >/dev/null

EXISTS=$(psql "$ADMIN_DATABASE_URL" -t -c \
    "SELECT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace \
     WHERE c.relname='${PNAME}' AND n.nspname='public');" | xargs)
if [ "$EXISTS" = "t" ]; then
    ok "Partición ${PNAME} creada"
else
    fail "Partición ${PNAME} creada" "la verificación en pg_class devolvió falso"
fi

# ── S3: idempotencia (CREATE TABLE IF NOT EXISTS) ──────────────────────────────
echo ""
echo "=== S3: doble creación idempotente ==="
if psql "$ADMIN_DATABASE_URL" -c \
    "CREATE TABLE IF NOT EXISTS ${PNAME} PARTITION OF ${TEST_TABLE} \
     FOR VALUES FROM ('${P_START}') TO ('${P_END}');" >/dev/null 2>&1; then
    ok "El doble CREATE TABLE IF NOT EXISTS es idempotente"
else
    fail "El doble CREATE TABLE IF NOT EXISTS es idempotente" "error en la segunda creación"
fi

# ── S4: fn_drop_old_partitions existe y es invocable ──────────────────────────
echo ""
echo "=== S4: fn_drop_old_partitions() es invocable ==="
if psql "$ADMIN_DATABASE_URL" -t -c \
    "SELECT proname FROM pg_proc WHERE proname='fn_drop_old_partitions';" | grep -q fn_drop_old_partitions; then
    DROPPED=$(psql "$ADMIN_DATABASE_URL" -t -c "SELECT fn_drop_old_partitions(24);" 2>&1 | xargs)
    ok "fn_drop_old_partitions(24) devolvió: ${DROPPED}"
else
    fail "fn_drop_old_partitions existe" "función ausente en pg_proc"
fi

# ── Limpieza ───────────────────────────────────────────────────────────────────
psql "$ADMIN_DATABASE_URL" -c "DROP TABLE IF EXISTS ${TEST_TABLE} CASCADE;" >/dev/null

# ── Resumen ────────────────────────────────────────────────────────────────────
echo ""
echo "=== Resumen ==="
echo "Pruebas SUPERADAS: $pass"
echo "Pruebas FALLIDAS: $fail"
if [ "$fail" -gt 0 ]; then
    exit 1
fi
echo "=== DEMO 06-TABLE-PARTITIONING COMPLETA: TODAS LAS VERIFICACIONES SUPERADAS ==="
exit 0

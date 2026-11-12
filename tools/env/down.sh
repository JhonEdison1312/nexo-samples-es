#!/bin/bash
# ADDED FOR THIS SAMPLE
# Para el entorno en espacio de usuario: PostgreSQL, PgBouncer, Redis
# (+ ruta Docker si existe)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Parando el entorno de NEXO Samples ==="

# Redis nativo
if [ -f /tmp/nexo-redis.pid ] && kill -0 "$(cat /tmp/nexo-redis.pid)" 2>/dev/null; then
    echo "Parando Redis (pid $(cat /tmp/nexo-redis.pid))"
    redis-cli -p 16379 shutdown nosave 2>/dev/null || kill "$(cat /tmp/nexo-redis.pid)" 2>/dev/null || true
fi

# PgBouncer nativo
if [ -f /tmp/nexo-pgbouncer/pgbouncer.pid ] && kill -0 "$(cat /tmp/nexo-pgbouncer/pgbouncer.pid)" 2>/dev/null; then
    echo "Parando PgBouncer (pid $(cat /tmp/nexo-pgbouncer/pgbouncer.pid))"
    kill "$(cat /tmp/nexo-pgbouncer/pgbouncer.pid)" 2>/dev/null || true
fi

# PostgreSQL nativo
if [ -f /tmp/nexo-pgdata/postmaster.pid ]; then
    echo "Parando PostgreSQL (/tmp/nexo-pgdata)"
    pg_ctl -D /tmp/nexo-pgdata -m fast -w stop || true
fi

# Ruta Docker (idempotente: compose down no hace nada cuando no hay nada en ejecución)
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    for harness in samples/*/harness; do
        if [ -f "$harness/docker-compose.yml" ]; then
            echo "Parando el proyecto docker compose en $harness"
            (cd "$harness" && docker compose down -v)
        fi
    done
fi

echo "=== Entorno parado ==="

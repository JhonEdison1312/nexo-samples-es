#!/bin/bash
# AÑADIDO PARA ESTA MUESTRA
# test_reliable_queue.sh — Wrapper de shell que ejecuta el harness de cola en Python.
# Inicia Redis (si no está corriendo) e invoca test_queue.py.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../../.."

REDIS_PORT="${REDIS_PORT:-16379}"

if ! redis-cli -p "$REDIS_PORT" ping >/dev/null 2>&1; then
    echo "Iniciando Redis vía tools/env/up.sh..."
    bash "${REPO_ROOT}/tools/env/up.sh"
fi

echo "Ejecutando las pruebas de invariantes de la cola confiable biométrica..."
python3 "${SCRIPT_DIR}/test_queue.py"

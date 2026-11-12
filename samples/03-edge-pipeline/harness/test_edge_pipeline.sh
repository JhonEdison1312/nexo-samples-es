#!/usr/bin/env bash
# AÑADIDO PARA ESTA MUESTRA
# Prueba del pipeline edge sin conexión:
# 1. Aprovisionamiento de clave vinculada al dispositivo post-corrección (fail-closed sin opt-in, permitido con NEXO_ALLOW_DEV_KEY_FALLBACK=1)
# 2. Inicialización del outbox local SQLite en modo WAL
# 3. Captura de asistencia biométrica sin conexión
# 4. Manejo de fallos de red e incremento del contador de reintentos
# 5. Subida cifrada AES-256-GCM con deduplicación del servidor vía Redis NX
# 6. Rechazo de ataque de replay
# El binario verifica cada paso y sale con código distinto de cero ante cualquier discrepancia.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAMPLE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN="${SCRIPT_DIR}/edge_demo"

SOURCES=(
  "${SAMPLE_DIR}/src/encryption.cpp"
  "${SAMPLE_DIR}/src/sqlite_manager.cpp"
  "${SAMPLE_DIR}/src/DevStubBiometricSensor.cpp"
  "${SAMPLE_DIR}/src/cloud_manager.cpp"
  "${SAMPLE_DIR}/src/utils/ConfigManager.cpp"
  "${SCRIPT_DIR}/main_demo.cpp"
)

needs_build=0
if [[ ! -x "${BIN}" ]]; then
    needs_build=1
else
    for src in "${SOURCES[@]}"; do
        if [[ "${src}" -nt "${BIN}" ]]; then
            needs_build=1
            break
        fi
    done
fi

if [[ "${needs_build}" -eq 1 ]]; then
    echo "Compilando edge_demo..."
    if ! g++ -std=c++20 -Wall -Wextra -Wpedantic \
      -I "${SAMPLE_DIR}/src/include" \
      -I "${SAMPLE_DIR}/src" \
      -I "${SAMPLE_DIR}/harness/include" \
      "${SAMPLE_DIR}/src/encryption.cpp" \
      "${SAMPLE_DIR}/src/sqlite_manager.cpp" \
      "${SAMPLE_DIR}/src/DevStubBiometricSensor.cpp" \
      "${SAMPLE_DIR}/src/cloud_manager.cpp" \
      "${SAMPLE_DIR}/src/utils/ConfigManager.cpp" \
      "${SCRIPT_DIR}/main_demo.cpp" \
      -lsqlite3 -lcrypto -lssl -lcurl -lspdlog -lfmt \
      -o "${BIN}" 2> "${SCRIPT_DIR}/.build.log"; then
        cat "${SCRIPT_DIR}/.build.log" >&2
        exit 1
    fi
fi

# Ejecuta el binario compilado (sale con código distinto de cero ante cualquier aserción fallida)
"${BIN}"

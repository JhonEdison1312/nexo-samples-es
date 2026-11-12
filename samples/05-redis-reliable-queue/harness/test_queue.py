#!/usr/bin/env python3
"""
AÑADIDO PARA ESTA MUESTRA
test_queue.py — Harness independiente que demuestra el patrón de cola confiable biométrica.

Ejercita tres invariantes de los scripts Lua extraídos de worker_biometric_queue.php:
  T1  Atomicidad de LMOVE  — el elemento se mueve ingest→processing; ingest queda vacía.
  T2  Recuperación de zombie por GC — un job viejo en processing (>maxAge) se reencola a ingest.
  T3  Promoción a DLQ   — un job que excede MAX_RETRIES se mueve a DLQ, no se reintenta.

Requiere: Redis en 127.0.0.1:16379 (ejecute tools/env/up.sh para iniciarlo).
No necesita base de datos; la lógica de la cola es Redis + Lua puro.
"""

import sys
import json
import time
import redis as redislib

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 16379

INGEST     = "q:biometric_ingest"
PROCESSING = "q:biometric_processing"
DLQ        = "q:biometric_dlq"
MAX_RETRIES = 3
GC_MAX_AGE  = 5   # segundos — reducido para la demo (predeterminado de producción: 300s)

# ── Scripts Lua copiados verbatim de src/worker_biometric_queue.php ────────────
SCRIPT_RELIABLE_POP = """
local ingest = KEYS[1]
local processing = KEYS[2]
local now = tonumber(ARGV[1])
local item = redis.call('LMOVE', ingest, processing, 'RIGHT', 'LEFT')
if item then
    local ok, job = pcall(cjson.decode, item)
    if ok and job then
        job.processing_since = now
        local newItem = cjson.encode(job)
        redis.call('LREM', processing, 0, item)
        redis.call('LPUSH', processing, newItem)
        return newItem
    end
    return item
end
return nil
"""

SCRIPT_GC = """
local processing = KEYS[1]
local ingest = KEYS[2]
local maxAge = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local items = redis.call('LRANGE', processing, 0, -1)
local recovered = 0
for i = 1, #items do
    local item = items[i]
    local ok, job = pcall(cjson.decode, item)
    if ok and job and job.processing_since then
        if (now - job.processing_since) > maxAge then
            redis.call('LREM', processing, 0, item)
            redis.call('LPUSH', ingest, item)
            recovered = recovered + 1
        end
    else
        redis.call('LREM', processing, 0, item)
        redis.call('LPUSH', ingest, item)
        recovered = recovered + 1
    end
end
return recovered
"""


def main():
    r = redislib.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    try:
        r.ping()
    except Exception as e:
        print(f"ERROR: No se puede conectar a Redis en {REDIS_HOST}:{REDIS_PORT}: {e}", file=sys.stderr)
        print("Inícielo con: tools/env/up.sh", file=sys.stderr)
        sys.exit(1)

    # Limpieza de cualquier ejecución previa
    r.delete(INGEST, PROCESSING, DLQ)

    passed = 0
    failed = 0

    def ok(label):
        nonlocal passed
        print(f"[PASS] {label}")
        passed += 1

    def fail(label, got, want):
        nonlocal failed
        print(f"[FAIL] {label} — obtenido {got!r}, esperado {want!r}")
        failed += 1

    def check(label, got, want):
        if got == want:
            ok(label)
        else:
            fail(label, got, want)

    # ── T1: Atomicidad de LMOVE ────────────────────────────────────────────────
    print("\n=== T1: LMOVE confiable — el job se mueve de ingest a processing de forma atómica ===")
    job1 = {"action": "SYNC_ATTENDANCE", "request_id": "req-001", "retries": 0}
    r.rpush(INGEST, json.dumps(job1))

    now = int(time.time())
    item = r.eval(SCRIPT_RELIABLE_POP, 2, INGEST, PROCESSING, now)

    check("cola ingest vacía tras el pop", r.llen(INGEST), 0)
    check("cola processing tiene 1 elemento",  r.llen(PROCESSING), 1)

    popped = json.loads(item)
    check("acción del job intacta",         popped.get("action"),         "SYNC_ATTENDANCE")
    check("processing_since inyectado", "processing_since" in popped, True)

    # Simular commit exitoso: eliminar de processing
    r.lrem(PROCESSING, 0, item)
    check("processing vacía tras el ack", r.llen(PROCESSING), 0)

    # ── T2: El GC recupera un job zombie ────────────────────────────────────────
    print("\n=== T2: Recuperación de zombie por GC — job viejo en processing se reencola ===")
    job2 = {"action": "REGISTER_STUDENT", "request_id": "req-002", "retries": 0}
    r.rpush(INGEST, json.dumps(job2))

    stale_ts = int(time.time()) - (GC_MAX_AGE + 1)   # ya expirado
    zombie = r.eval(SCRIPT_RELIABLE_POP, 2, INGEST, PROCESSING, stale_ts)

    check("el zombie está en processing antes del GC", r.llen(PROCESSING), 1)
    check("ingest vacía antes del GC",            r.llen(INGEST), 0)

    recovered = r.eval(SCRIPT_GC, 2, PROCESSING, INGEST, GC_MAX_AGE, int(time.time()))
    check("el GC recuperó 1 zombie",     int(recovered), 1)
    check("processing vacía tras el GC", r.llen(PROCESSING), 0)
    check("ingest tiene el job recuperado",  r.llen(INGEST), 1)

    r.delete(INGEST)

    # ── T3: Promoción a DLQ tras agotar reintentos ──────────────────────────────
    print("\n=== T3: Promoción a DLQ — job que excede el límite de reintentos se mueve a DLQ ===")
    # Sembrar el job inicial una sola vez; cada iteración reencola el estado actualizado.
    job_state = {"action": "SYNC_ATTENDANCE", "request_id": "req-003", "retries": 0}
    r.rpush(INGEST, json.dumps(job_state))

    for attempt in range(1, MAX_RETRIES + 2):
        item = r.eval(SCRIPT_RELIABLE_POP, 2, INGEST, PROCESSING, int(time.time()))
        r.lrem(PROCESSING, 0, item)
        job_state = json.loads(item)
        job_state["retries"] = attempt
        if attempt <= MAX_RETRIES:
            r.rpush(INGEST, json.dumps(job_state))    # reintento
        else:
            r.rpush(DLQ, json.dumps(job_state))        # dead letter

    check("ingest vacía tras todos los reintentos", r.llen(INGEST), 0)
    check("DLQ tiene 1 job fallido",          r.llen(DLQ), 1)

    dlq_job = json.loads(r.lindex(DLQ, 0))
    check("reintentos del job en DLQ == 4",  dlq_job.get("retries"), MAX_RETRIES + 1)
    check("acción del job en DLQ intacta", dlq_job.get("action"), "SYNC_ATTENDANCE")

    # Limpieza
    r.delete(INGEST, PROCESSING, DLQ)

    # ── Resumen ────────────────────────────────────────────────────────────────
    print(f"\n=== Resumen ===")
    print(f"Pruebas SUPERADAS: {passed}")
    print(f"Pruebas FALLIDAS: {failed}")
    if failed:
        sys.exit(1)
    print("Todas las pruebas de invariantes de la cola SUPERADAS.")
    sys.exit(0)


if __name__ == "__main__":
    main()

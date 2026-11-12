# Cola confiable en Redis con GC y DLQ

## Propósito

Demuestra un patrón de cola Redis sin pérdida de mensajes: LMOVE atómico hacia
una lista sombra de procesamiento, garbage collection de zombies mediante un
script Lua de GC, y promoción automática a una dead-letter queue tras agotar el
presupuesto de reintentos.

## Dónde encaja

En la ruta de ingesta de eventos biométricos de NEXO. Los dispositivos edge
encolan eventos de asistencia y registro de estudiantes en
`queue:biometric_ingest`; este worker los consume con semántica de entrega
at-least-once incluso ante caídas del worker.

## Origen

- Ruta: `backend/api/workers/worker_biometric.php` (líneas 720-939)
- Transformaciones: 0 sustituciones aplicadas (extracto de código limpio que coincide con el commit del repositorio madre)

## Qué observar

- `worker_biometric_queue.php` (líneas 1-25): `$scriptReliablePop` — LMOVE atómico
  en Lua + inyección del timestamp `processing_since`. Sin condición de carrera
  a nivel de aplicación.

- `worker_biometric_queue.php` (líneas 27-47): `$scriptGc` — GC en Lua que
  recorre la lista de procesamiento y reencola cualquier elemento más viejo que
  `GC_MAX_AGE_SEC`.

- `worker_biometric_queue.php` (líneas 69-115): Bucle principal — pop con LMOVE,
  despacho de jobs, patrón ack-tras-commit (`lRem` solo en éxito).

- `worker_biometric_queue.php` (líneas 159-174): Promoción a DLQ tras 3
  reintentos; circuit-breaker en `/tmp/redis_circuit_open`.

- `worker_biometric_queue.php` (líneas 77-91): Drenaje del outbox cada 15 s —
  filas PROCESSING huérfanas (worker muerto a mitad de vuelo) vuelven a PENDING.

## Cómo ejecutarlo

```bash
# Iniciar Redis (si no está corriendo)

tools/env/up.sh

# Ejecutar las pruebas de invariantes de la cola (T1: atomicidad, T2: recuperación por GC, T3: promoción a DLQ)

python3 samples/05-redis-reliable-queue/harness/test_queue.py

```

La salida esperada está en `EXPECTED_OUTPUT.txt`.

## Decisiones de diseño y compensaciones

- **Cola confiable de dos listas**: LMOVE es atómico; el elemento nunca es
  invisible. Si el worker se cae antes del ack, el GC lo recupera tras
  `GC_MAX_AGE_SEC` (300 s por defecto), eliminando la ventana de mensajes
  perdidos que tendría un simple LPOP.

- **Scripts Lua para la atomicidad**: Tanto LMOVE+inyección de timestamp como
  el escaneo y recuperación del GC corren dentro de una sola llamada Lua. No se
  necesita MULTI/EXEC multi-clave.

- **Outbox durable de respaldo**: Redis es la ruta rápida. Si Redis no está
  disponible, la API edge escribe en `ingest_outbox` (PostgreSQL). El worker
  drena ambos cada 15 s: ningún mensaje se pierde aunque Redis caiga minutos.

- **La DLQ es una lista separada**: `queue:biometric_dlq` es inspeccionable y
  reproducible sin tocar la cola en vivo.

## Limitaciones y qué cambiaría

- El GC MAX_AGE (300 s) es una configuración estática. Un campo TTL por job
  permitiría que los eventos de alta prioridad se recuperaran más rápido.

- `lRem` es O(N) sobre la lista de procesamiento. Para un throughput muy alto,
  un enfoque basado en hash (ID de job → expiración del claim) sería O(1).

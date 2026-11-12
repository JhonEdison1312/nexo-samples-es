# Edge Pipeline

## Propósito

Demuestra un nodo edge C++20 con enfoque offline-first que incluye una capa de abstracción de hardware (HAL), un outbox local en SQLite, cifrado AES-256-GCM, sincronización con la nube con contabilidad de reintentos y defensa contra ataques de replay.

## Dónde encaja

En los dispositivos edge de NEXO instalados en centros educativos, que registran eventos de asistencia biométrica sin conexión y los sincronizan de forma segura con la API central cuando se restablece la conectividad de red.

## Origen

- Path: `backend/edge/include/hal/IBiometricSensor.h` (lines 1-56)
- Path: `backend/edge/src/hardware/dev_stub/DevStubBiometricSensor.cpp` (lines 1-54)
- Path: `backend/edge/src/base_de_datos/sqlite_manager.cpp` (lines 1-723)
- Path: `backend/edge/src/base_de_datos/encryption.cpp` (lines 1-498)
- Path: `backend/edge/src/base_de_datos/cloud_manager.cpp` (lines 1-168)
- Transformaciones: 0 sustituciones aplicadas (extracción de código limpia que coincide con el commit del repositorio matriz).

## Qué revisar

- `encryption.cpp` (lines 106-136): Enforzamiento fail-closed de la clave vinculada al hardware; el fallback de desarrollo requiere `NEXO_ALLOW_DEV_KEY_FALLBACK=1` (modo 0600).
- `encryption.cpp` (lines 188-267): Cifrado AES-256-GCM con IV aleatorio de 12 bytes y etiqueta de autenticación de 16 bytes.
- `sqlite_manager.cpp` (lines 37-95): Configuración de la tabla outbox con `PRAGMA journal_mode=WAL` y `synchronous=EXTRA`.
- `cloud_manager.cpp` (lines 52-168): Ensamblado del payload cifrado y seguimiento de reintentos de sincronización.
- `IBiometricSensor.h` (lines 28-55): Contrato de abstracción de hardware que separa la lógica de negocio de los sensores biométricos.

## Cómo ejecutarlo

Espacio de usuario nativo:

```bash
./samples/03-edge-pipeline/harness/test_edge_pipeline.sh

```

Docker Compose:

```bash
cd samples/03-edge-pipeline/harness && docker compose up --build

```

## Decisiones de diseño y compensaciones

- **Vinculación de hardware fail-closed**: si la obtención de la clave vinculada al hardware falla, el nodo se niega a persistir claves en texto plano salvo que `NEXO_ALLOW_DEV_KEY_FALLBACK=1` esté configurado explícitamente para los simuladores de desarrollo. SIMULATED: la demo del harness (`main_demo.cpp`) simula un servidor en la nube simulado; no realiza llamadas de red reales ni usa claves de hardware reales.
- **Patrón outbox en SQLite**: los eventos biométricos se persisten de inmediato en el SQLite local antes de cualquier llamada de red, evitando la pérdida de datos ante cortes de energía o caídas de red.
- **Deduplicación en servidor y protección anti-replay**: los payloads incluyen nonces únicos verificados mediante `SET key 1 NX EX 604800` en Redis para prevenir ataques de replay.

## Limitaciones y qué cambiaría

- **Verificación de nonce fail-open**: el handler privado de ingesta `backend/api/api.php` (archivo privado, no forma parte de este repositorio), líneas 363-380, permite las peticiones cuando Redis está caído, priorizando la captura de asistencia sobre la protección estricta contra replay. En entornos de alta seguridad, debería fallar cerrado o recurrir a una tabla indexada en PostgreSQL.
- **Recuperación de claves**: las claves vinculadas al hardware no pueden extraerse; el reemplazo del dispositivo requiere un re-registro en la nube. Añadir atestación respaldada por TPM agilizaría el aprovisionamiento de la flota.
- **Fallback heredado de clave en texto plano**: `encryption.cpp:139-158` contiene un fallback para cargar claves en texto plano desde un archivo de 32 bytes para entornos heredados/no-RPi. Se usa cuando las claves cifradas vinculadas al hardware no pueden descifrarse (p. ej., tarjeta SD movida a hardware distinto). En un despliegue fail-closed estricto, este fallback debería eliminarse. SIMULATED: el servidor de la demo del harness es SIMULATED; no usa hardware real ni claves cifradas.
- **Modo degradado de cifrado por campo**: `encField`/`decField` en `sqlite_manager.cpp` (líneas ~171-195) almacenan y devuelven TEXTO PLANO cuando no hay clave aprovisionada o el cifrado falla, y `decField` acepta valores heredados en texto plano sin el prefijo `enc:v1:`. La PII en reposo solo está protegida mientras haya una clave aprovisionada; un despliegue estricto también debería fallar cerrado aquí.

## Muestras relacionadas

- `01-rls-pgbouncer`: aislamiento de sesiones multi-inquilino en la API de ingesta.
- `02-audit-chain`: registro de auditoría HMAC a prueba de manipulaciones para los eventos registrados.

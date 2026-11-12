# Cadena de auditoría HMAC

## Propósito

Demuestra el registro de auditoría a prueba de manipulaciones mediante encadenamiento de hashes criptográficos HMAC-SHA256 para detectar modificaciones, eliminaciones o rupturas de secuencia.

## Dónde encaja

Pipeline de auditoría donde las mutaciones de estado emiten registros de solo anexado a `global_audit_logs`. Un trigger de base de datos calcula una cadena criptográfica hacia adelante por tenant utilizando un secreto HMAC del lado del servidor.

## Origen

- Path: `backend/api/workers/worker_audit.php` (lines 70-189)
- Path: `sql/schema.sql` (lines 1362-1456)
- Transformaciones: 0 sustituciones aplicadas (extracción de código limpia que coincide con el commit del repositorio original)

## Qué mirar

- `src/audit_chain_trigger.sql`: `fn_calculate_audit_hash` deriva una firma HMAC-SHA256 que vincula el hash del registro anterior, el ID del actor, el payload de la acción y la marca de tiempo.
- `src/audit_chain_trigger.sql`: `fn_audit_chain_trigger` consulta automáticamente `prev_audit_id` y vincula `chain_hash` antes de la inserción.
- `src/audit_chain_trigger.sql`: `fn_validate_audit_chain` recorre los registros iterativamente en orden cronológico e informa del ID exacto del registro roto al detectar una discrepancia.

## Cómo ejecutarlo

Ejecución nativa en espacio de usuario:

```bash
tools/env/up.sh
./samples/02-audit-chain/harness/test_tampering.sh

```

Ruta Docker (la ruta nativa anterior es la principal):

```bash
cd samples/02-audit-chain/harness && docker compose up -d --wait && NEXO_PG_PORT=15433 NEXO_SOCKET_DIR= ./test_tampering.sh

```

## Decisiones de diseño y compensaciones

- **HMAC frente a hash simple**: requiere `app.nexo_hmac_secret`. Un atacante con acceso a la base de datos pero sin acceso a la configuración del servidor de aplicaciones no puede recalcular firmas válidas tras una manipulación.
- **Encadenamiento por tenant**: delimitar las cadenas por `school_id` evita bloqueos de filas en la serialización global, permitiendo la ingesta en paralelo entre instituciones.

## Limitaciones y qué cambiaría

- El trigger ejecuta `SELECT ... FOR UPDATE` sobre el registro más reciente del tenant, creando un cuello de botella serializado bajo alta concurrencia de escritura dentro de un mismo tenant.
- En entornos desplegados con alta carga, trasladaría el cálculo de la cadena a un worker asíncrono basado en cola con batching.

## Muestras relacionadas

- `01-rls-pgbouncer`: aislamiento multitenant mediante SET LOCAL
- `03-edge-pipeline`: registro de eventos biométricos sin conexión y sincronización

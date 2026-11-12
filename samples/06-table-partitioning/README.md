# Particionamiento mensual de tablas

## Propósito

Demuestra la gestión de particionamiento RANGE declarativo en PostgreSQL:
creación automatizada de particiones mensuales en 8 tablas padre, guardas
idempotentes CREATE TABLE IF NOT EXISTS, y un invocador de eliminación por
retención que llama a un procedimiento almacenado para podar particiones
expiradas.

## Dónde encaja

NEXO acumula filas append-only de series temporales en 8 tablas (eventos de
asistencia, logs de auditoría, mensajes, alertas, comandos). El particionado
por mes permite pruning sin bloquear filas en vivo y mantiene acotados los
tamaños de los índices.

## Origen

- `create_monthly_partition.sh`: `backend/api/infra/scripts/create_monthly_partition.sh` (líneas 1-57)
- `drop_old_partitions.sh`: `backend/api/infra/scripts/drop_old_partitions.sh` (líneas 1-24)
- Transformaciones: 0 sustituciones aplicadas (extractos de código limpios).

## Qué observar

- `create_monthly_partition.sh` (líneas 24-34): Arreglo asociativo que mapea
  las 8 tablas padre particionadas a su columna de rango — fuente única de
  verdad de toda la topología de particiones.

- `create_monthly_partition.sh` (líneas 43-56): Bucle con guarda EXISTS —
  omite particiones ya creadas; cualquier fallo produce un exit no cero para
  que cron alerte.

- `create_monthly_partition.sh` (línea 36): Argumentos opcionales `[YYYY-MM]`
  y `[tabla]` para backfill puntual de un mes específico o de una sola tabla.

- `drop_old_partitions.sh` (línea 22): Delega en `fn_drop_old_partitions(N)`
  (un procedimiento almacenado PL/pgSQL) — el script de shell es solo un shim
  de cron con logging; la lógica de eliminación vive en la base de datos
  donde puede ser transaccional.

## Cómo ejecutarlo

```bash
# Requiere PostgreSQL en localhost:15432 (tools/env/up.sh)

bash samples/06-table-partitioning/harness/test_partitioning.sh

```

La salida esperada está en `EXPECTED_OUTPUT.txt`.  
Si PostgreSQL está fuera de línea, shellcheck (S1) igual corre de forma aislada.

## Decisiones de diseño y compensaciones

- **El DDL requiere `ADMIN_DATABASE_URL`**: CREATE de particiones requiere un
  rol con privilegio DDL. Separarlo de `DATABASE_URL` (rol de lectura/escritura
  de la aplicación) evita que el proceso de la API emita DDL en operación
  normal.

- **Shell en lugar de framework de migraciones**: Ningún ORM ni migration
  runner puede pre-crear de forma confiable la partición del mes siguiente vía
  cron. Un script de shell que llama a `psql` es la herramienta correcta:
  transparente, auditable y ejecutable desde crontab sin runtime de lenguaje.

- **Procedimiento almacenado para las eliminaciones**:
  `fn_drop_old_partitions` corre en una transacción y puede inspeccionar
  pg_class con seguridad. Hacerlo en shell obligaría a armar una lista DROP
  dinámica con manipulación de strings — propenso a errores y no transaccional.

## Limitaciones y qué cambiaría

- La granularidad de partición es fija en mensual. Para tablas de muy alto
  throughput, una granularidad semanal o diaria reduciría el tamaño de cada
  partición individual.

- La creación de particiones es actualmente un disparador manual o por cron;
  un enfoque dirigido por eventos (crear 7 días antes del fin de mes) sería
  más robusto.

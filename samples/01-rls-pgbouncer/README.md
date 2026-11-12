# RLS + PgBouncer + SET LOCAL

## Propósito

Demuestra el uso de Row-Level Security (RLS) de PostgreSQL con pooling por transacción de PgBouncer y SET LOCAL para evitar fugas de contexto entre tenants en conexiones reutilizadas.

## Dónde encaja

Núcleo multitenant donde las políticas RLS de PostgreSQL aplican el aislamiento por `school_id`. Los parámetros de configuración con ámbito de transacción impiden la filtración de estado cuando PgBouncer reutiliza conexiones físicas.

## Origen

- Path: `backend/api/routes/_auth_middleware.php` (lines 665-725)
- Path: `sql/schema.sql` (lines 2282-2294)
- Transformaciones: 0 sustituciones aplicadas (extracción de código limpia que coincide con el commit del repositorio original)

## Qué mirar

- `src/auth_middleware.php`: `beginTransaction()` seguido de `set_config('app.current_school_id', ..., true)` garantiza el ámbito a nivel de transacción.
- `src/auth_middleware.php`: re-enlace autoritativo del contexto desde la fila de la base de datos tras el parseo inicial del token.
- `src/rls_policies.sql`: políticas RLS sobre la tabla `students` que utilizan `get_current_school_id()`.

## Cómo ejecutarlo

Ejecución nativa en espacio de usuario:

```bash
tools/env/up.sh
./samples/01-rls-pgbouncer/harness/test_pgbouncer_leak.sh

```

Ruta Docker (la ruta nativa anterior es la principal):

```bash
cd samples/01-rls-pgbouncer/harness && docker compose up -d --wait && NEXO_PGBOUNCER_PORT=16431 ./test_pgbouncer_leak.sh

```

## Decisiones de diseño y compensaciones

- **Ámbito de transacción frente a sesión**: en el pooling por transacción de PgBouncer, un `SET` de sesión se filtra al siguiente cliente que comparta la conexión backend. Pasar `is_local=true` reinicia el estado en el `COMMIT`.
- **Relectura autoritativa de la BD**: los tokens son instantáneas puntuales en el tiempo. Los cambios de rol o de tenant durante sesiones activas se detectan en la consulta posterior a la base de datos.

## Limitaciones y qué cambiaría

- Requiere que toda consulta de lectura se ejecute dentro de un bloque de transacción explícito, lo que aumenta los roundtrips.
- En arquitecturas de alto rendimiento, evaluaría esquemas con prefijo de tenant o pools de conexiones dedicados por nivel.

## Muestras relacionadas

- `02-audit-chain`: registro de auditoría a prueba de manipulaciones con encadenamiento HMAC
- `03-edge-pipeline`: captura de asistencia sin conexión e ingesta sincronizada

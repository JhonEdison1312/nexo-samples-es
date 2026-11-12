# NEXO Samples - README

![CI](https://github.com/JhonEdison1312/nexo-samples-en/actions/workflows/ci.yml/badge.svg)

> Landing: <https://nexo-u2nb.vercel.app>
> Demo en vivo (aplicación funcional): <https://nexo-eight-xi.vercel.app>

¡Bienvenido! Este repositorio contiene extractos depurados del proyecto NEXO, un prototipo que construí como ingeniero backend en solitario. Se publica como portfolio técnico para entrevistas y aprendizaje. NEXO sigue siendo propietario, pero puedes leer, ejecutar, discutir y criticar los patrones que se muestran aquí. Consulta LICENSE para conocer las condiciones exactas.

## Qué es / Qué no es

**Esto es:**

- Extractos depurados de mi prototipo NEXO (código real del sistema)
- Harnesses de pruebas añadidos para que los extractos sean ejecutables como demos independientes
- Demostraciones de patrones arquitectónicos que implementé
- Muestras pequeñas y enfocadas que demuestran patrones individuales

**Esto NO es:**

- El código completo de NEXO
- Una aplicación completa (cada muestra demuestra un patrón específico, no un sistema completo)
- Código de producción (NEXO está en fase de prototipo, solo con simuladores, sin usuarios reales)
- Código escrito solo para las muestras (todo lo que hay bajo `samples/*/src` se extrajo del sistema real; el código del harness es código de pegamento añadido)

## Muestras destacadas

**1. RLS + PgBouncer + SET LOCAL** (~5 min)

- Row-Level Security de PostgreSQL con transaction pooling para evitar fugas de contexto entre tenants
- Ejecuta: `make up && make test-01`

**2. HMAC Audit Chain** (~5 min)

- Logs de auditoría a prueba de manipulación con HMAC-SHA256 encadenado por hash
- Ejecuta: `make up && make test-02`

**3. Edge Pipeline** (15+ min)

- Nodo offline-first en C++20 con abstracción de hardware, SQLite, cifrado AES-256-GCM y sincronización en la nube
- Ejecuta: `make up && make test-03`

**4. Nodus LLM Parser** (15+ min)

- Integración de LLM con guardrails - el parser clasifica intenciones, el composer reescribe las respuestas con validación estricta, y el sistema degrada de forma segura sin modelo
- Ejecuta: `make test-04`

## Índice de todas las muestras

| Muestra | Habilidad demostrada | Área | Ejecutar |
|--------|---------------------|------|----------|
| 01-rls-pgbouncer | SQL multi-tenant con RLS + PgBouncer + SET LOCAL | Autenticación | `make up && make test-01` |
| 02-audit-chain | Cadena de auditoría HMAC para evidencia de manipulación | Seguridad | `make up && make test-02` |
| 03-edge-pipeline | Arquitectura offline-first en C++20 con cifrado | Edge | `make up && make test-03` |
| 04-nodus-parser | Integración de LLM con guardrails y fallback determinista | Integración con IA | `make test-04` |
| 05-redis-reliable-queue | Cola atómica con LMOVE en Lua, con GC y DLQ | Workers asíncronos | `make up && make test-05` |
| 06-table-partitioning | Ciclo de vida de particiones RANGE mensuales con retención | Base de datos | `make up && make test-06` |

## Mapa del sistema

Consulta [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para ver el diagrama de arquitectura completo y el flujo de datos.

## Cómo se verifica la autenticidad

Cada extracto se registra en PROVENANCE.json con la ruta de origen, el rango de líneas y las transformaciones aplicadas. Ejecuta `make verify-provenance ORIGIN=/path/to/mother/repo` para verificar que el código de las muestras coincide con el repositorio original tras las sustituciones declaradas. Consulta PROVENANCE.md para más detalles.

## Ejecutar todo

**Prerrequisitos:**
Ejecuta `make deps-check` para verificar que todas las herramientas necesarias están instaladas.

**Iniciar el entorno:**

```bash
make up

```

**Ejecutar muestras individuales:**

```bash
make test-01  # RLS + PgBouncer
make test-02  # HMAC Audit Chain
make test-03  # Edge Pipeline
make test-04  # Nodus Parser
make test-05  # Redis Queue
make test-06  # Table Partitioning

```

**Detener el entorno:**

```bash
make down

```

**Verificar procedencia (requiere el repositorio ORIGIN):**

```bash
make verify ORIGIN=/path/to/mother/repo

```

## Licencia

Este repositorio se distribuye bajo la licencia PolyForm Noncommercial 1.0.0 — consulta el archivo LICENSE para el texto completo.

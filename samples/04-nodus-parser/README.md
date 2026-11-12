# Nodus LLM Parser y Guardrails

## Propósito

Demuestra un pipeline de integración con LLM con guardrails estrictos: clasificación de lenguaje natural compatible con OpenAI, sanitización de entidades con allowlists de dominio, detección de alucinaciones post-generación y degradación determinista segura cuando el modelo no está disponible.

## Dónde encaja

En el asistente conversacional de NEXO ("Nodus" en la interfaz del producto, implementado en el código interno bajo `backend/api/nexus/`). Nodus traduce preguntas libres del usuario a estructuras de intent validadas sin ejecutar nunca SQL arbitrario ni mutar estado.

## Origen

- Ruta: `backend/api/nexus/nexus_llm.php` (líneas 1-572)
- Transformaciones: 0 sustituciones aplicadas (extracto de código limpio que coincide con el commit del repositorio madre).

## Qué observar

- `nexus_llm.php` (líneas 25-44): Configuración y verificaciones de capacidad con degradación elegante (`nxLlmEnabled`).
- `nexus_llm.php` (líneas 91-155): Transporte de red vía libcurl con manejo de 429 Retry-After y contabilidad de presupuesto de tiempo.
- `nexus_llm.php` (líneas 190-320): Response Composer y guardia anti-alucinación post-generación (`nxLlmComposeGuard`).
- `nexus_llm.php` (líneas 360-486): Clasificador de intents (`nxLlmClassify`) con allowlists de entidades, enums cerrados e inyección bloqueada de scope comodín.
- `nexus_llm.php` (líneas 559-570): Enmascaramiento de PII de estudiantes (`nxComposeCellSafe`) que garantiza que los campos sensibles nunca salen del perímetro.

## Cómo ejecutarlo

```bash
php samples/04-nodus-parser/harness/test_parser.php

```

## Decisiones de diseño y compensaciones

- **Solo parser, nunca ejecutor directo de BD**: El LLM traduce texto a un intent estructurado y un payload de entidades. Las capas deterministas posteriores (planner, verificaciones de política RBAC y consultas de solo lectura) ejecutan la obtención de datos, lo que previene inyección SQL o destrucción de datos inducida por el prompt. El planner y la matriz RBAC (nexus_semantic.php, chat.php) NO ESTÁN EN EL REPO — no fueron extraídos para esta muestra.
- **Guardia anti-alucinación post-generación**: `nxLlmComposeGuard` valida que las respuestas generadas conserven todas las cifras verificadas, rechaza causas inventadas (p. ej. fallos técnicos falsos) y bloquea la negación de datos si la consulta subyacente devolvió filas.
- **Sanitización estricta de entidades**: Las claves de entidad están restringidas a una allowlist, los enums se validan estrictamente, las fechas no pueden ser futuras ni tener más de 3 años, y las escaladas de scope (p. ej. `group: ALL`) se eliminan.

## Limitaciones y qué cambiaría

- **Planner semántico descendente**: El planner semántico (`nexus_semantic.php`) y la matriz de permisos institucionales (`chat.php`) residen en el repositorio madre. En este extracto, el parser y el composer se verifican de extremo a extremo con un harness de pruebas automatizado. SIMULADO: el harness de pruebas simula los pasos de planner/RBAC ya que NO ESTÁN EN EL REPO.
- **Modelo de respaldo local**: En despliegues edge de alta latencia o sin conexión, las consultas al LLM en la nube añaden latencia. Ejecutar un modelo cuantizado de 3B parámetros on-premise eliminaría la dependencia de proveedores cloud.
- **Español en los prompts**: Nodus es un asistente en español. Los system prompts, patrones regex y plantillas de respuesta en `nexus_llm.php` están en español como lógica funcional del producto. Esto está documentado en `tools/lang_allowlist.txt`.

## Muestras relacionadas

- `01-rls-pgbouncer`: Aislamiento de sesión multi-tenant en los manejadores de consultas descendentes.
- `02-audit-chain`: Registro a prueba de manipulaciones de consultas de seguridad y acciones del asistente.

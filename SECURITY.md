# Política de seguridad

## Credenciales solo para demo

Este repositorio contiene código de ejemplo con fines demostrativos. Las credenciales en las configuraciones de los harnesses son solo para pruebas locales y NO son credenciales de despliegue.

### Credenciales de demo de los harnesses

- **PostgreSQL (muestras 01, 02)**: usuario `nexo_app` con contraseña `demo_password` (solo localhost)
- **Redis (muestra 05)**: sin autenticación configurada (solo localhost)
- **Cloud API (muestra 03)**: servidor simulado en localhost:8080, sin llamadas de red reales

## Seguridad por diseño en los extractos

Los patrones de seguridad demostrados incluyen:

1. **Row-Level Security (RLS) de PostgreSQL**: aislamiento multi-tenant con `SET LOCAL` para evitar fugas de contexto entre tenants
2. **Cifrado AES-256-GCM**: claves de 256 bits con IV aleatorio de 12 bytes y etiqueta de autenticación de 16 bytes
3. **Cadena de auditoría HMAC**: logging a prueba de manipulación con HMAC-SHA256 encadenado por hash
4. **Nonces anti-replay**: nonces de payload únicos verificados mediante `SET key 1 NX EX 604800` en Redis
5. **Fail-closed de binding de hardware**: claves ligadas al hardware con opt-in explícito para el fallback de desarrollo
6. **Guardrails de LLM**: el parser solo clasifica, las capas deterministas ejecutan, y el sistema degrada sin modelo

## Cómo reportar problemas de seguridad

Para el prototipo NEXO (repositorio privado), reporta los problemas de seguridad por los canales correspondientes. Este repositorio público de muestras contiene solo extractos depurados y ningún secreto de despliegue.

## Descargo de responsabilidad

Este es un repositorio de portfolio que demuestra patrones arquitectónicos de un prototipo. El código NO está listo para despliegue y no debe desplegarse tal cual en ningún entorno.

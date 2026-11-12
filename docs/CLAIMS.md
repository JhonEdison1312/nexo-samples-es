# Mapeo de Claims del CV

| Claim del CV | Muestra | Archivo | Comando |
|---------------|---------|---------|---------|
| C++20 | 03-edge-pipeline | samples/03-edge-pipeline/src/include/hal/IBiometricSensor.h | `bash samples/03-edge-pipeline/harness/test_edge_pipeline.sh` |
| PHP 8 | 01-rls-pgbouncer | samples/01-rls-pgbouncer/src/auth_middleware.php | `php -l samples/01-rls-pgbouncer/src/auth_middleware.php` |
| PostgreSQL RLS | 01-rls-pgbouncer | samples/01-rls-pgbouncer/src/auth_middleware.php | `bash samples/01-rls-pgbouncer/harness/test_pgbouncer_leak.sh` |
| PgBouncer SET LOCAL | 01-rls-pgbouncer | samples/01-rls-pgbouncer/src/auth_middleware.php | `bash samples/01-rls-pgbouncer/harness/test_pgbouncer_leak.sh` |
| AES-256-GCM | 03-edge-pipeline | samples/03-edge-pipeline/src/encryption.cpp | `bash samples/03-edge-pipeline/harness/test_edge_pipeline.sh` |
| HMAC audit chain | 02-audit-chain | samples/02-audit-chain/src/worker_audit.php | `bash samples/02-audit-chain/harness/test_tampering.sh` |
| LLM integration | 04-nodus-parser | samples/04-nodus-parser/src/nexus_llm.php | `php samples/04-nodus-parser/harness/test_parser.php` |
| Redis reliable queue / DLQ | 05-redis-reliable-queue | samples/05-redis-reliable-queue/src/worker_biometric_queue.php | `python3 samples/05-redis-reliable-queue/harness/test_queue.py` |
| PostgreSQL table partitioning | 06-table-partitioning | samples/06-table-partitioning/src/create_monthly_partition.sh | `bash samples/06-table-partitioning/harness/test_partitioning.sh` |

## Auditoría Tier 3 — Claims presentes en ORIGIN pero no extraídos

| Claim | Estado | Evidencia |
|-------|--------|-----------|
| Risk engine (multi-layer scoring) | EVIDENCIADO EN EL REPO — NO EXTRAÍDO | `backend/api/routes/risk.php`, `RiskEngineV3.php`; demasiado grande para un extract aislado |
| JWT / RBAC middleware | EVIDENCIADO EN EL REPO — NO EXTRAÍDO | `_auth_middleware.php` (más allá del extract de RLS); capacidades RBAC en `nexus_semantic.php` |
| Docker / containerization | EVIDENCIADO EN EL REPO — NO EXTRAÍDO | `Dockerfile`, `docker-compose.yml` en la raíz de ORIGIN; nivel prototipo, sin target de registry |
| Kubernetes / multi-region | NO ESTÁ EN EL REPO | No se encontraron manifiestos k8s, Helm charts ni configuración multi-región en ORIGIN |
| Database migrations framework | NO ESTÁ EN EL REPO | El esquema se gestiona vía `sql/schema.sql` y scripts de particiones; sin migration runner |

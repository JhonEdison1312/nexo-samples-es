#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Genera docs/CLAIMS.md mapeando claims del CV a archivos de muestra y comandos
de verificación.
"""
from pathlib import Path

CLAIMS = {
    "C++20": {
        "sample": "03-edge-pipeline",
        "file": "samples/03-edge-pipeline/src/include/hal/IBiometricSensor.h",
        "command": "bash samples/03-edge-pipeline/harness/test_edge_pipeline.sh"
    },
    "PHP 8": {
        "sample": "01-rls-pgbouncer",
        "file": "samples/01-rls-pgbouncer/src/auth_middleware.php",
        "command": "php -l samples/01-rls-pgbouncer/src/auth_middleware.php"
    },
    "PostgreSQL RLS": {
        "sample": "01-rls-pgbouncer",
        "file": "samples/01-rls-pgbouncer/src/auth_middleware.php",
        "command": "bash samples/01-rls-pgbouncer/harness/test_pgbouncer_leak.sh"
    },
    "PgBouncer SET LOCAL": {
        "sample": "01-rls-pgbouncer",
        "file": "samples/01-rls-pgbouncer/src/auth_middleware.php",
        "command": "bash samples/01-rls-pgbouncer/harness/test_pgbouncer_leak.sh"
    },
    "AES-256-GCM": {
        "sample": "03-edge-pipeline",
        "file": "samples/03-edge-pipeline/src/encryption.cpp",
        "command": "bash samples/03-edge-pipeline/harness/test_edge_pipeline.sh"
    },
    "HMAC audit chain": {
        "sample": "02-audit-chain",
        "file": "samples/02-audit-chain/src/worker_audit.php",
        "command": "bash samples/02-audit-chain/harness/test_tampering.sh"
    },
    "LLM integration": {
        "sample": "04-nodus-parser",
        "file": "samples/04-nodus-parser/src/nexus_llm.php",
        "command": "php samples/04-nodus-parser/harness/test_parser.php"
    },
    "Redis reliable queue / DLQ": {
        "sample": "05-redis-reliable-queue",
        "file": "samples/05-redis-reliable-queue/src/worker_biometric_queue.php",
        "command": "python3 samples/05-redis-reliable-queue/harness/test_queue.py"
    },
    "PostgreSQL table partitioning": {
        "sample": "06-table-partitioning",
        "file": "samples/06-table-partitioning/src/create_monthly_partition.sh",
        "command": "bash samples/06-table-partitioning/harness/test_partitioning.sh"
    },
}

TIER3_AUDIT = [
    ("Risk engine (multi-layer scoring)",
     "EVIDENCIADO EN EL REPO — NO EXTRAÍDO",
     "`backend/api/routes/risk.php`, `RiskEngineV3.php`; demasiado grande para un extract aislado"),
    ("JWT / RBAC middleware",
     "EVIDENCIADO EN EL REPO — NO EXTRAÍDO",
     "`_auth_middleware.php` (más allá del extract de RLS); capacidades RBAC en `nexus_semantic.php`"),
    ("Docker / containerization",
     "EVIDENCIADO EN EL REPO — NO EXTRAÍDO",
     "`Dockerfile`, `docker-compose.yml` en la raíz de ORIGIN; nivel prototipo, sin target de registry"),
    ("Kubernetes / multi-region",
     "NO ESTÁ EN EL REPO",
     "No se encontraron manifiestos k8s, Helm charts ni configuración multi-región en ORIGIN"),
    ("Database migrations framework",
     "NO ESTÁ EN EL REPO",
     "El esquema se gestiona vía `sql/schema.sql` y scripts de particiones; sin migration runner"),
]


def generate_claims(check_only=False):
    out = "# Mapeo de Claims del CV\n\n"
    out += "| Claim del CV | Muestra | Archivo | Comando |\n"
    out += "|---------------|---------|---------|---------|\n"
    for claim, data in CLAIMS.items():
        out += f"| {claim} | {data['sample']} | {data['file']} | `{data['command']}` |\n"

    out += "\n## Auditoría Tier 3 — Claims presentes en ORIGIN pero no extraídos\n\n"
    out += "| Claim | Estado | Evidencia |\n"
    out += "|-------|--------|-----------|\n"
    for claim, status, evidence in TIER3_AUDIT:
        out += f"| {claim} | {status} | {evidence} |\n"

    if check_only:
        existing = Path("docs/CLAIMS.md")
        if not existing.exists() or existing.read_text(encoding="utf-8") != out:
            print("docs/CLAIMS.md está DESACTUALIZADO — ejecuta tools/generate_claims.py")
            return 1
        print("docs/CLAIMS.md está al día")
        return 0
    Path("docs/CLAIMS.md").write_text(out, encoding="utf-8")
    print("Generado docs/CLAIMS.md")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(generate_claims(check_only="--check" in sys.argv))

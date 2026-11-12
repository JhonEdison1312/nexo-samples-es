#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Comprueba el mapeo de claims del CV de cada muestra e identifica lagunas de
contenido.
"""
import json
import sys
from pathlib import Path

# Claims del CV del usuario
cv_claims = {
    "Multi-tenant SQL: PostgreSQL Row-Level Security under PgBouncer transaction pooling": "01-rls-pgbouncer",
    "Security by design: HMAC audit chain": "02-audit-chain",
    "Edge node (C++20): offline-first, SQLite, HAL, simulators, E2E validation": "03-edge-pipeline",
    "Nodus (AI assistant): LLM parser and composer": "04-nodus-parser"
}

print("=== MAPEO MUESTRA -> CLAIM DEL CV ===\n")

for sample_dir in sorted(Path('samples').iterdir()):
    if not sample_dir.is_dir():
        continue
    sample_id = sample_dir.name
    print(f"Muestra: {sample_id}")
    print(f"  Archivos en src: {list((sample_dir / 'src').glob('*')) if (sample_dir / 'src').exists() else 'Ninguno'}")
    print(f"  Archivos en harness: {list((sample_dir / 'harness').glob('*')) if (sample_dir / 'harness').exists() else 'Ninguno'}")

    # Comprobar README
    readme = sample_dir / 'README.md'
    if readme.exists():
        content = readme.read_text()
        print(f"  Secciones del README: {[line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')][:5]}")
    print()

print("\n=== COMPROBANDO SQL FALTANTE EN ORIGIN ===\n")

# Buscar archivos SQL de políticas RLS
origin_arg = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd().parent)
rls_files = list(Path(origin_arg).rglob('*.sql'))
print(f"Total de archivos SQL en ORIGIN: {len(rls_files)}")

# Buscar palabras clave de políticas RLS
rls_found = []
for sql_file in rls_files:
    content = sql_file.read_text()
    if 'ROW LEVEL SECURITY' in content or 'row level security' in content.lower():
        rls_found.append(sql_file)

print(f"Archivos SQL que mencionan RLS: {len(rls_found)}")
for f in rls_found[:5]:
    print(f"  {f}")

# Buscar trigger de auditoría
audit_found = []
for sql_file in rls_files:
    content = sql_file.read_text()
    if 'chain_hash' in content or 'global_audit_logs' in content:
        audit_found.append(sql_file)

print(f"\nArchivos SQL que mencionan la cadena de auditoría: {len(audit_found)}")
for f in audit_found[:5]:
    print(f"  {f}")

#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Comprobación de huérfanos: verifica que todos los archivos de samples/*/src
están en PROVENANCE.json y viceversa.
"""
import json
from pathlib import Path

def orphan_check():
    with open('PROVENANCE.json') as f:
        provenance = json.load(f)

    # Obtener todos los archivos de samples/*/src
    src_files = set()
    for sample_dir in Path('samples').iterdir():
        if sample_dir.is_dir():
            src_path = sample_dir / 'src'
            if src_path.exists():
                for f in src_path.rglob('*'):
                    if f.is_file():
                        src_files.add(f"{sample_dir.name}/src/{f.relative_to(src_path)}")

    # Obtener todos los archivos de PROVENANCE.json
    provenance_files = set()
    for sample_id, sample_data in provenance.get('samples', {}).items():
        for extract in sample_data.get('extracts', []):
            provenance_files.add(f"{sample_id}/src/{extract['output_file']}")

    # Buscar huérfanos
    src_only = src_files - provenance_files
    provenance_only = provenance_files - src_files

    print("=== COMPROBACIÓN DE HUÉRFANOS ===")
    print(f"Archivos en samples/*/src: {len(src_files)}")
    print(f"Archivos en PROVENANCE.json: {len(provenance_files)}")

    if src_only:
        print(f"\nArchivos en src pero NO en PROVENANCE.json ({len(src_only)}):")
        for f in sorted(src_only):
            print(f"  {f}")
    else:
        print("\nSin archivos huérfanos en src")

    if provenance_only:
        print(f"\nArchivos en PROVENANCE.json pero NO en src ({len(provenance_only)}):")
        for f in sorted(provenance_only):
            print(f"  {f}")
    else:
        print("Sin archivos huérfanos en PROVENANCE.json")

    if not src_only and not provenance_only:
        print("\nORPHAN CHECK: PASA")
        return 0
    else:
        print("\nORPHAN CHECK: FALLA")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(orphan_check())

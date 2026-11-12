#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Punto de entrada maestro del verificador.

Delega en tools/release_check.sh, que ejecuta las puertas G1-G8, escribe los
logs raw en _internal/release/raw/ y solo imprime TODAS LAS PUERTAS
SUPERADAS cuando cada puerta pasó de verdad. Este archivo existe por
compatibilidad con `make verify`.

Uso: python3 tools/run_verify.py [/path/to/mother/repo]
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    origin = sys.argv[1] if len(sys.argv) > 1 else ''
    if not origin:
        import os
        origin = os.environ.get('ORIGIN', '')
    if not origin:
        print('ERROR: se requiere la ruta del repo ORIGIN (argumento o variable'
              ' de entorno $ORIGIN); sin fallback implícito al directorio padre')
        return 2
    if not (Path(origin) / '.git').exists():
        print('ERROR: se requiere la ruta del repo ORIGIN (argumento o variable'
              ' de entorno $ORIGIN)')
        return 2
    script = REPO / 'tools' / 'release_check.sh'
    return subprocess.run(['bash', str(script), origin], cwd=REPO).returncode


if __name__ == '__main__':
    sys.exit(main())

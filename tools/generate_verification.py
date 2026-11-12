#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Genera VERIFICATION.md — solo comandos.

VERIFICATION.md es un archivo PÚBLICO: nunca debe contener afirmaciones de
PASS/FAIL ni referencias a logs locales en bruto. Este generador, por tanto,
emite únicamente los comandos que un revisor puede ejecutar para reproducir
la verificación, más el commit de procedencia fijado. Los resultados de las
compuertas quedan en los logs locales en bruto y nunca se escriben aquí.

Si existen logs de compuertas en bruto y alguna compuerta FALLÓ, el script
igual termina con código distinto de cero (lo reporta solo en stdout) para que
CI pueda detectar un mal estado sin que el archivo público afirme jamás un
resultado.

Uso: python3 tools/generate_verification.py
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / '_internal' / 'release' / 'raw'


def any_gate_failed():
    """True si algún log de compuerta en bruto registra una FALLA. Sin logs -> False."""
    if not RAW.is_dir():
        return False
    for log in RAW.glob('*.log'):
        text = log.read_text(errors='replace')
        if re.search(r'GATE \S+: FALLA|RELEASE CHECK: FALLA', text):
            return True
    return False


def main():
    prov = json.loads((REPO / 'PROVENANCE.json').read_text())
    commit = prov['origin']['commit']
    n_extracts = sum(len(sd['extracts']) for sd in prov['samples'].values())

    lines = [
        '# Verificación de NEXO Samples',
        '',
        'Este archivo lista los comandos usados para verificar este repositorio. Lo',
        'GENERA `tools/generate_verification.py`; no lo edites a mano.',
        'Intencionadamente no contiene afirmaciones de aprobado/fallido: ejecuta los',
        'comandos de abajo e inspecciona la salida por ti mismo.',
        '',
        '## Comandos',
        '',
        '```bash',
        'make deps-check          # herramientas requeridas presentes (distinto de cero si falta alguna)',
        'make up && make down     # ciclo de vida de PG+PgBouncer+Redis en espacio de usuario',
        'make test-01 .. test-06  # demos por muestra (el entorno debe estar activo)',
        'bash tools/negative_tests.sh      # controles de sabotaje (el entorno debe estar activo)',
        'make verify-fast         # php -l + lint de docs + shellcheck',
        'make verify ORIGIN=...   # suite completa de compuertas de release',
        '```',
        '',
        'Cada comando termina con código distinto de cero si falla; una prueba omitida no cuenta como aprobada.',
        '',
        f'Procedencia: {n_extracts} extractos fijados al commit ORIGIN '
        f'`{commit}` (consulta PROVENANCE.json / PROVENANCE.md). Verifica con:',
        '',
        '```bash',
        'python3 tools/provenance/verify.py /path/to/origin/repo',
        'python3 tools/mutation_tests.py /path/to/origin/repo',
        'python3 tools/independent_recheck.py /path/to/origin/repo',
        '```',
        '',
        '## Notas',
        '',
        '- Los componentes simulados están etiquetados como SIMULATED en el código y en los README.',
        '- La muestra 04 contiene español funcional (prompts/regexes del LLM),',
        '  en lista blanca en `tools/lang_allowlist.txt`.',
        '- `tools/negative_tests.sh` demuestra que cada aserción del harness detecta una',
        '  dependencia deliberadamente rota (RLS desactivado, función eliminada, Redis',
        '  caído) y restaura el entorno después.',
        '',
    ]
    out = '\n'.join(lines)
    (REPO / 'VERIFICATION.md').write_text(out)
    print('VERIFICATION.md generado (solo comandos, sin afirmaciones de compuertas)')
    if any_gate_failed():
        print('ADVERTENCIA: los logs de compuertas en bruto locales contienen entradas FALLA — '
              'el archivo público intencionadamente no las reporta.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Re-check independiente de provenance — una ruta de código deliberadamente
DISTINTA de tools/provenance/verify.py + normalizers.py.

Método: normalización simétrica ingenua. Ambos lados (el slice del blob de
git de ORIGIN y el archivo de muestra) pasan por el MISMO stripped tonto:

    1. eliminar bloques /* ... */ (regex, dotall)
    2. eliminar comentarios -- / // / # hasta fin de línea (regex)
    3. eliminar todo el espacio en blanco

Como el stripped es simétrico, los comentarios traducidos y el formato
desaparecen en AMBOS lados; cualquier diff restante es contenido real
(código o literal de cadena). El texto parecido a comentario dentro de
literales de cadena se elimina igual en ambos lados, así que no puede
producir una discrepancia falsa — y una edición real de un literal sigue
apareciendo.

Selecciona 8 extracts al azar (semilla 42) en todos los lenguajes, imprime
la primera diferencia de las formas stripped (debe ser ninguna) y sale con
código distinto de cero ante cualquier discrepancia. Solo lectura: nunca
escribe en ORIGIN ni en samples.

Uso: python3 tools/independent_recheck.py /path/to/mother/repo
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

BLOCK_RE = re.compile(r'/\*.*?\*/', re.S)
LINE_RE = re.compile(r'(--|//|#)[^\n]*')
WS_RE = re.compile(r'\s+')


def dumb_normalize(code: str) -> str:
    code = BLOCK_RE.sub('', code)
    code = LINE_RE.sub('', code)
    return WS_RE.sub('', code)


def origin_slice(origin: str, commit: str, path: str, start: int, end: int) -> str:
    blob = subprocess.run(
        ['git', '-C', origin, 'show', f'{commit}:{path}'],
        capture_output=True, text=True, check=True).stdout
    lines = blob.split('\n')
    return '\n'.join(lines[start - 1:end])


def first_diff(a: str, b: str, ctx: int = 60):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return (f'primera diferencia en el carácter {i}\n'
                    f'  origin  : ...{a[max(0,i-ctx):i+ctx]}...\n'
                    f'  muestra : ...{b[max(0,i-ctx):i+ctx]}...')
    if len(a) != len(b):
        i = min(len(a), len(b))
        return (f'diferencia de longitud en el carácter {i} '
                f'(origin {len(a)} vs muestra {len(b)})\n'
                f'  origin  : ...{a[max(0,i-ctx):i+ctx]}...\n'
                f'  muestra : ...{b[max(0,i-ctx):i+ctx]}...')
    return None


def main():
    if len(sys.argv) != 2:
        print('Uso: python3 tools/independent_recheck.py /path/to/mother/repo')
        sys.exit(1)
    origin = sys.argv[1]
    prov = json.loads((REPO / 'PROVENANCE.json').read_text())
    commit = prov['origin']['commit']

    extracts = []
    for sid, sd in prov['samples'].items():
        for ex in sd['extracts']:
            extracts.append((sid, ex))

    rng = random.Random(42)
    # primero una elección por lenguaje (cobertura), luego completar hasta 8
    # al azar
    by_lang = {}
    for e in extracts:
        by_lang.setdefault(e[1]['language'], []).append(e)
    picks = [rng.choice(group) for _, group in sorted(by_lang.items())]
    rest = [e for e in extracts if e not in picks]
    rng.shuffle(rest)
    picks = (picks + rest)[:8]

    print(f'RECHECK INDEPENDIENTE — {len(picks)} extracts, seed=42')
    print('=' * 72)
    failures = 0
    for sid, ex in picks:
        rel = f"samples/{sid}/src/{ex['output_file']}"
        sample_path = REPO / rel
        try:
            sample = sample_path.read_text()
        except FileNotFoundError:
            print(f'FALLA {rel}: archivo inexistente')
            failures += 1
            continue
        try:
            origin_code = origin_slice(origin, commit, ex['origin_file'],
                                       *ex['line_range'])
        except subprocess.CalledProcessError as e:
            print(f'FALLA {rel}: no se puede leer origin ({e})')
            failures += 1
            continue
        # Aplicar las sustituciones literales declaradas — forman parte del
        # contrato de provenance (la misma transformación que hace extract.py).
        for sub in ex.get('substitutions', []):
            origin_code = origin_code.replace(sub['pattern'],
                                              sub['replacement'])
        a = dumb_normalize(origin_code)
        b = dumb_normalize(sample)
        d = first_diff(a, b)
        status = 'OK  ' if d is None else 'DIF '
        if d:
            failures += 1
        print(f'{status} {rel}  [{ex["language"]}]  '
              f'norm_len origin={len(a)} muestra={len(b)}')
        if d:
            print('     ' + d.replace('\n', '\n     '))
    print('=' * 72)
    if failures:
        print(f'RECHECK INDEPENDIENTE: FALLA ({failures} discrepancias)')
        return 1
    print('RECHECK INDEPENDIENTE: PASA — formas stripped iguales en todas las elecciones')
    return 0


if __name__ == '__main__':
    sys.exit(main())

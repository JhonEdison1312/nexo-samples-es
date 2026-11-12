#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Comprobación de regresión de la salida de demo.

Ejecuta el target de test de cada muestra, normaliza los elementos volátiles
(timestamps, UUIDs, nonces, PIDs, tiempos) y compara con
samples/NN/EXPECTED_OUTPUT.txt.

Uso:
  python3 tools/check_demo_output.py            # modo comparación (sale 1 si hay diff)
  python3 tools/check_demo_output.py --update   # regenera EXPECTED_OUTPUT.txt
El entorno debe estar activo (tools/env/up.sh) para las muestras con
DB/Redis.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ANSI = re.compile(r'\x1b\[[0-9;]*m')
TS = re.compile(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+\]')
UUID = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b')
NONCE = re.compile(r'nonce-[A-Za-z0-9-]+')
ELAPSED = re.compile(r'\b\d+(?:\.\d+)?\s?(?:ms|s)\b(?=\s|$)')
PID = re.compile(r'\bpid[:= ]+\d+\b', re.I)


def normalize(text, sample):
    text = ANSI.sub('', text)
    text = TS.sub('[TS]', text)
    text = NONCE.sub('<NONCE>', text)
    if sample in ('02-audit-chain',):
        text = UUID.sub('<UUID>', text)
    if sample == '03-edge-pipeline':
        text = re.sub(r'uuid-\d{10,}', '<UUIDTS>', text)
        # el paso de build no es salida de demo; solo aparece cuando el
        # binario está desactualizado
        text = '\n'.join(l for l in text.split('\n')
                         if l.strip() != 'Compiling edge_demo...') + '\n'
    # ruido del wrapper make recursivo (depende del idioma): 'make[N]: ... directory"'
    text = re.sub(r'^make\[\d+\]:.*(directorio|directory).*$', '',
                  text, flags=re.M)
    text = ELAPSED.sub('<T>', text)
    text = PID.sub('pid=<PID>', text)
    # espacios finales / rachas de líneas en blanco
    lines = [l.rstrip() for l in text.split('\n')]
    out, blank = [], False
    for l in lines:
        if l == '':
            if not blank:
                out.append('')
            blank = True
        else:
            out.append(l)
            blank = False
    return '\n'.join(out).strip('\n') + '\n'


SAMPLES = {
    '01-rls-pgbouncer': 'make test-01',
    '02-audit-chain': 'make test-02',
    '03-edge-pipeline': 'make test-03',
    '04-nodus-parser': 'make test-04',
    '05-redis-reliable-queue': 'make test-05',
    '06-table-partitioning': 'make test-06',
}


def run_sample(cmd):
    p = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    update = '--update' in sys.argv
    results = []
    for sid, cmd in SAMPLES.items():
        code, out = run_sample(cmd)
        norm = normalize(out, sid)
        exp_path = REPO / f'samples/{sid}/EXPECTED_OUTPUT.txt'
        if update:
            exp_path.write_text(norm)
            print(f'ACTUALIZADO samples/{sid}/EXPECTED_OUTPUT.txt '
                  f'(exit={code}, {len(norm.splitlines())} líneas)')
            results.append((sid, 'ACTUALIZADO', code == 0))
            continue
        if code != 0:
            print(f'FALLA {sid}: el comando de test salió con {code}')
            results.append((sid, 'FALLA(ejecución)', False))
            continue
        expected = exp_path.read_text() if exp_path.exists() else ''
        if norm == expected:
            print(f'PASA {sid}: la salida coincide con EXPECTED_OUTPUT.txt')
            results.append((sid, 'PASA', True))
        else:
            import difflib
            diff = list(difflib.unified_diff(
                expected.split('\n'), norm.split('\n'),
                'esperado', 'real', lineterm=''))[:30]
            print(f'DIFIERE {sid}: la salida difiere de EXPECTED_OUTPUT.txt')
            for l in diff:
                print('   ' + l)
            results.append((sid, 'DIFIERE', False))
    ok = all(r[2] for r in results)
    print('COMPROBACIÓN DE SALIDA DEMO:', 'PASA' if ok else 'FALLA')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

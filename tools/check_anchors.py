#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Comprobación de anclas de documentación (segura en CI, no necesita ORIGIN).

Verifica:
  1. README raíz <= 120 líneas; cada README de muestra <= 80 líneas.
  2. Todo `make test-NN` / `make up` / `make down` mencionado en los README
     existe como target del Makefile.
  3. Toda ruta samples/NN-*/ referenciada en README/docs existe en disco.
  4. Los README de muestra contienen las secciones requeridas (Purpose,
     Run it, Limitations).
  5. docs/ARCHITECTURE.md contiene un bloque mermaid.
  6. LICENSE existe y menciona PolyForm Noncommercial.
  7. docs/CLAIMS.md existe y referencia las seis muestras.

Uso: python3 tools/check_anchors.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
failures = []


def fail(msg):
    failures.append(msg)
    print(f'FALLA: {msg}')


def ok(msg):
    print(f'PASA: {msg}')


# 1. límites de líneas
root = (REPO / 'README.md').read_text()
n = len(root.split('\n'))
if n <= 121:
    ok(f'README raíz {n} líneas (<=120 de contenido)')
else:
    fail(f'README raíz {n} líneas > 120')

sample_dirs = sorted((REPO / 'samples').iterdir())
for sd in sample_dirs:
    rm = sd / 'README.md'
    if not rm.exists():
        fail(f'{sd.name}: falta README.md')
        continue
    lines = len(rm.read_text().split('\n'))
    if lines <= 81:
        ok(f'{sd.name}/README.md {lines} líneas')
    else:
        fail(f'{sd.name}/README.md {lines} líneas > 80')

# 2. targets de make
mk = (REPO / 'Makefile').read_text()
targets = set(re.findall(r'^([A-Za-z0-9_-]+)\s*:', mk, re.M))
readmes = [REPO / 'README.md'] + [sd / 'README.md' for sd in sample_dirs]
for rm in readmes:
    if not rm.exists():
        continue
    text = rm.read_text()
    for m in re.finditer(r'`make ([a-z0-9-]+)', text):
        t = m.group(1)
        if t not in targets:
            fail(f'{rm.relative_to(REPO)}: `make {t}` no es un target del Makefile')
        else:
            ok(f'`make {t}` referenciado en {rm.name}')

# 3. las rutas de muestra referenciadas existen
for rm in readmes + [REPO / 'docs/ARCHITECTURE.md', REPO / 'docs/CLAIMS.md']:
    if not rm.exists():
        continue
    text = rm.read_text()
    for m in re.finditer(r'`?((?:samples|tools|docs)/[A-Za-z0-9_./-]+)`?', text):
        p = m.group(1).rstrip('.,')
        # quitar sufijos de rango de líneas tipo file.php:10-20
        p = re.sub(r':\d+(-\d+)?$', '', p)
        if '*' in p:
            continue
        if not (REPO / p).exists():
            # probar como prefijo de directorio
            if not list(REPO.glob(p + '*')):
                fail(f'{rm.relative_to(REPO)}: ruta referenciada inexistente: {p}')

# 4. secciones requeridas en los README de muestra
for sd in sample_dirs:
    rm = sd / 'README.md'
    if not rm.exists():
        continue
    text = rm.read_text().lower()
    for section in ('propósito', 'cómo ejecutarlo', 'limitaciones'):
        if section not in text:
            fail(f'{sd.name}/README.md: falta la sección ~{section}')

# 5. mermaid
arch = REPO / 'docs/ARCHITECTURE.md'
if arch.exists() and '```mermaid' in arch.read_text():
    ok('docs/ARCHITECTURE.md tiene diagrama mermaid')
else:
    fail('docs/ARCHITECTURE.md sin bloque mermaid')

# 6. LICENSE
lic = REPO / 'LICENSE'
if lic.exists() and 'PolyForm Noncommercial' in lic.read_text():
    ok('LICENSE menciona PolyForm Noncommercial')
else:
    fail('LICENSE ausente o no menciona PolyForm Noncommercial')

# 7. CLAIMS cubre todas las muestras
claims = REPO / 'docs/CLAIMS.md'
if claims.exists():
    ctext = claims.read_text()
    for sd in sample_dirs:
        if sd.name.split('-')[0] not in ctext and sd.name not in ctext:
            fail(f'docs/CLAIMS.md no referencia {sd.name}')
    ok('referencias de docs/CLAIMS.md comprobadas')
else:
    fail('docs/CLAIMS.md ausente')

print('=' * 60)
if failures:
    print(f'ANCHOR CHECK: FALLA ({len(failures)} problemas)')
    sys.exit(1)
print('ANCHOR CHECK: PASA')

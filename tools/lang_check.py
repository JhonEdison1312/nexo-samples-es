#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Verificación de idioma español para el árbol público (edición ES).

Comprueba que las superficies de documentación estén realmente en español:
cada archivo de la lista DOC_GLOBS debe contener al menos un marcador de
español (tilde, ñ o palabras españolas comunes). El código fuente no se
escanea: sus identificadores y palabras clave son inglés por diseño.

Uso: python3 tools/lang_check.py [--json]
Salida 0 = limpio, 1 = se encontraron violaciones.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALLOWLIST_FILE = REPO / 'tools' / 'lang_allowlist.txt'

ACCENT_RE = re.compile(r'[áéíóúÁÉÍÓÚñÑ¿¡]')
# Lista conservadora: palabras inequívocamente españolas que esencialmente
# nunca aparecen como palabras inglesas sueltas ni como identificadores
# comunes. Una línea necesita una tilde O al menos dos coincidencias distintas
# para ser marcada, lo que evita falsos positivos en prosa inglesa e
# identificadores de código.
SPANISH_WORDS = [
    'el', 'la', 'los', 'las', 'una', 'del', 'para', 'con', 'sin', 'sobre',
    'entre', 'desde', 'hasta', 'cuando', 'donde', 'porque', 'pero', 'como',
    'más', 'está', 'están', 'estan', 'fue', 'era', 'esto', 'esta', 'estos',
    'estas', 'ese', 'esa', 'hay', 'tiene', 'tienen', 'debe', 'deben', 'puede',
    'pueden', 'hacer', 'hace', 'cada', 'todo', 'toda', 'todos', 'todas',
    'otro', 'otra', 'otros', 'mismo', 'misma', 'también', 'tambien', 'después',
    'despues', 'antes', 'ahora', 'siempre', 'nunca', 'aquí', 'aqui', 'allí',
    'alli', 'entonces', 'así', 'asi', 'bien', 'según', 'segun', 'hacia',
    'mediante', 'luego', 'incluso', 'además', 'ademas', 'es', 'son', 'ser',
    'estoy', 'estamos', 'están', 'muy', 'ya', 'aún', 'aun', 'ni', 'tampoco',
    'aunque', 'mientras', 'durante', 'así', 'vez', 'veces', 'forma', 'parte',
    'ejemplo', 'nombre', 'fecha', 'hora', 'día', 'dias', 'días', 'mes',
    'año', 'anos', 'años', 'persona', 'personas', 'cosa', 'cosas', 'manera',
    'tipo', 'tipos', 'caso', 'casos', 'punto', 'puntos', 'lado', 'lado',
    'gracias', 'hola', 'adiós', 'adios', 'por', 'favor', 'vale', 'bueno',
    'malo', 'nuevo', 'nueva', 'viejo', 'vieja', 'primero', 'primera', 'último',
    'ultima', 'última', 'siguiente', 'anterior', 'actual', 'posible',
    'imposible', 'necesario', 'necesaria', 'importante', 'público', 'publica',
    'privado', 'privada', 'general', 'especial', 'normal', 'común', 'comun',
    'diferente', 'igual', 'semejante', 'contrario', 'respecto', 'acerca',
    'alrededor', 'dentro', 'fuera', 'encima', 'debajo', 'delante', 'detrás',
    'cerca', 'lejos', 'junto', 'juntos', 'separado', 'unido', 'libre',
    'ocupado', 'vacío', 'vacio', 'lleno', 'vacía', 'llena', 'abierto',
    'cerrado', 'alto', 'bajo', 'grande', 'pequeño', 'pequeno', 'largo',
    'corto', 'ancho', 'estrecho', 'fácil', 'facil', 'difícil', 'dificil',
    'simple', 'complicado', 'claro', 'oscuro', 'blanco', 'negro', 'rojo',
    'azul', 'verde', 'amarillo', 'grupos', 'estudiantes', 'asistencia',
    'grupo', 'alumno', 'alumnos', 'colegio', 'docente', 'docentes',
    'acudiente', 'acudientes', 'registra', 'presentes', 'ausencias',
    'encontraron', 'encontrar', 'registros', 'registro', 'pertenece',
    'pertenecen', 'usuario', 'usuarios', 'encontrado', 'inactivo',
    'restringido', 'configurada', 'configurado', 'partición', 'particiones',
    'eliminadas', 'eliminados', 'retención', 'fallo', 'falló', 'creada',
    'creado', 'existe', 'meses', 'dedos', 'dedo', 'huella', 'huellas',
    'evaluar', 'eliminar', 'decisión', 'decision', 'arquitectura', 'mantiene',
    'fuente', 'normalizada', 'normalizado', 'compat', 'hasta', 'desde',
    'según', 'mediante', 'no', 'sí', 'si', 'se', 'su', 'sus', 'lo', 'le',
    'les', 'me', 'te', 'nos', 'os', 'mi', 'mis', 'tu', 'tus', 'usted',
    'ustedes', 'ellos', 'ellas', 'nosotros', 'vosotros', 'esto', 'eso',
    'aquello', 'aquel', 'aquella', 'cuyo', 'cuya', 'dicho', 'dicha',
]
WORD_RE = re.compile(
    r'\b(' + '|'.join(sorted(set(SPANISH_WORDS), key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)
MIN_WORD_HITS = 2

# Tipos de archivo a escanear (solo texto)
SCAN_SUFFIXES = {
    '.php', '.sql', '.cpp', '.h', '.hpp', '.c', '.cc', '.sh', '.bash',
    '.py', '.md', '.txt', '.yml', '.yaml', '.json', '.xml', '.conf',
    '.ini', '.example', '.env', '.tpl', '.dist', '.service',
}
SCAN_NAMES = {'Makefile', 'Dockerfile', 'LICENSE', 'README', 'EXPECTED_OUTPUT.txt',
              'PROVENANCE.md', 'SECURITY.md', 'VERIFICATION.md'}
# PROVENANCE.json se excluye: cita el texto fuente de ORIGIN verbatim
# (incluidos comentarios/identificadores en español) por diseño — ese es el
# propio registro de provenance.
SCAN_EXCLUDE = {'PROVENANCE.json', 'docs/SUBSTITUTIONS.md', 'tools/lang_allowlist.txt'}

# Entradas de la allowlist: (glob_de_ruta, regex_o_literal, razón)
def load_allowlist():
    entries = []
    if not ALLOWLIST_FILE.exists():
        return entries
    for raw in ALLOWLIST_FILE.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            entries.append((parts[0], parts[1], '|'.join(parts[2:])))
    return entries


def iter_files():
    files = subprocess.run(
        ['git', 'ls-files'], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    for rel in files:
        if rel in SCAN_EXCLUDE:
            continue
        p = REPO / rel
        if not p.is_file():
            continue
        if p.suffix in SCAN_SUFFIXES or p.name in SCAN_NAMES or '.' not in p.name:
            try:
                p.read_text(encoding='utf-8')
            except (UnicodeDecodeError, ValueError):
                continue  # binary
            yield rel, p


def line_hits(text):
    """Produce (lineno, línea, tipo) para cada marcador de español.

    Una línea se marca cuando tiene un carácter con tilde o al menos
    MIN_WORD_HITS palabras españolas conservadoras distintas.
    """
    for i, line in enumerate(text.split('\n'), 1):
        if ACCENT_RE.search(line):
            yield i, line, 'accent'
            continue
        hits = {m.group(0).lower() for m in WORD_RE.finditer(line)}
        if len(hits) >= MIN_WORD_HITS:
            yield i, line, 'words:' + ','.join(sorted(hits))


# Superficies de documentación que deben estar en español (presencia).
DOC_GLOBS = (
    'README.md', 'SECURITY.md', 'VERIFICATION.md', 'PROVENANCE.md',
    'docs/', 'samples/',
)
DOC_SUFFIXES = {'.md', '.txt'}
DOC_NAMES = {'README', 'EXPECTED_OUTPUT.txt'}


def is_doc_surface(rel):
    if rel in SCAN_EXCLUDE:
        return False
    p = Path(rel)
    if not (p.suffix in DOC_SUFFIXES or p.name in DOC_NAMES):
        return False
    return any(rel == g or (g.endswith('/') and rel.startswith(g)) for g in DOC_GLOBS)


def main():
    as_json = '--json' in sys.argv
    violations = []
    checked = 0

    for rel, p in iter_files():
        if not is_doc_surface(rel):
            continue
        checked += 1
        text = p.read_text(encoding='utf-8')
        hits = list(line_hits(text))
        if not hits:
            violations.append((rel, 0, 'sin-marcas-es',
                               'sin marcadores de español'))

    if as_json:
        print(json.dumps({'violations': violations}, indent=2, ensure_ascii=False))
    else:
        print(f"Superficies de documentación comprobadas: {checked}")
        if violations:
            print(f"\nVIOLACIONES ({len(violations)}):")
            for rel, lineno, kind, line in violations[:80]:
                print(f"  {rel}:{lineno} [{kind}] {line}")
            print("\nLANG CHECK: FALLA")
            return 1
        print("\nLANG CHECK: PASA")
        return 0


if __name__ == '__main__':
    sys.exit(main())

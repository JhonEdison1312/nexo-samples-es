#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Verifica que los extracts coinciden con origin tras las transformaciones.
SOLO LECTURA: nunca modifica ningún archivo versionado; solo lee.

Uso: python3 verify.py /path/to/mother/repo
"""
import sys
import json
import hashlib
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalizers import normalize, string_spans, _php_body  # noqa: E402


def git(origin, *args):
    return subprocess.run(
        ['git', '-C', str(origin), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def check_origin_commit_exists(origin_path, expected_commit):
    try:
        kind = git(origin_path, 'cat-file', '-t', expected_commit).strip()
    except subprocess.CalledProcessError:
        print(f"FALLA: commit de origin desconocido: {expected_commit}")
        return False
    if kind != 'commit':
        print(f"FALLA: el commit esperado {expected_commit} no es un objeto commit")
        return False
    return True


def substitution_scope_ok(pattern, replacement, slice_text, lang):
    """Cada aparición de `pattern` y de `replacement` en el slice debe estar
    dentro de un literal de cadena. Devuelve (ok, mensaje)."""
    if lang == 'php':
        search_text = _php_body(slice_text)
    else:
        search_text = slice_text
    spans = string_spans(search_text, lang)

    def count_inside(needle):
        start, count = 0, 0
        while True:
            idx = search_text.find(needle, start)
            if idx < 0:
                return count
            if not any(s <= idx and idx + len(needle) <= e for s, e in spans):
                return -1
            count += 1
            start = idx + 1

    n_pat = count_inside(pattern)
    if n_pat < 0:
        return False, f"el patrón '{pattern}' aparece fuera de un literal de cadena"
    n_rep = count_inside(replacement)
    if n_rep < 0:
        return False, f"el reemplazo '{replacement}' aparece fuera de un literal de cadena"
    return True, ""


def verify_provenance(origin_path, provenance_file):
    origin = Path(origin_path)
    if not origin.exists():
        print(f"ERROR: la ruta de origin no existe: {origin_path}")
        return 1

    with open(provenance_file, 'r', encoding='utf-8') as f:
        provenance = json.load(f)

    expected_commit = provenance.get('origin', {}).get('commit')
    if not expected_commit or not check_origin_commit_exists(origin, expected_commit):
        print("Validación del commit de origin: FALLA")
        return 1
    print(f"Verificación del commit de origin: PASA (commit: {expected_commit[:16]}...)")

    # ORIGIN HEAD vs commit registrado: se informa coincidencia o discrepancia
    # (nunca falla solo por discrepancia — el commit registrado es al que están
    # fijados los extracts).
    try:
        head = git(origin, 'rev-parse', 'HEAD').strip()
        if head == expected_commit:
            print(f"ORIGIN HEAD coincide con el commit registrado ({head[:12]}...)")
        else:
            print(f"AVISO: ORIGIN HEAD ({head[:12]}...) difiere del commit "
                  f"registrado ({expected_commit[:12]}...); los extracts se "
                  f"verifican contra el commit registrado.")
    except subprocess.CalledProcessError:
        print("AVISO: no se pudo resolver ORIGIN HEAD")

    # Estado del árbol de ORIGIN: verify nunca debe escribir en ORIGIN. Se
    # toma una instantánea de `git status --porcelain` antes y después y se
    # exige que no cambie.
    status_before = git(origin, 'status', '--porcelain')
    if status_before.strip():
        print("AVISO: el árbol de trabajo de ORIGIN no está limpio antes de verify:")
        for line in status_before.strip().split('\n')[:10]:
            print(f"    {line}")

    all_pass = True

    # Comprobación de huérfanos en ambas direcciones
    prov_files = set()
    for sample_id, sample_data in provenance.get('samples', {}).items():
        for extract in sample_data.get('extracts', []):
            prov_files.add(f"samples/{sample_id}/src/{extract['output_file']}")
    actual_files = {str(f) for f in Path('samples').glob('*/src/**/*') if f.is_file()}
    for f in sorted(actual_files - prov_files):
        print(f"FALLA: archivo extra en src/ no está en PROVENANCE.json: {f}")
        all_pass = False
    for f in sorted(prov_files - actual_files):
        print(f"FALLA: entrada de PROVENANCE.json sin archivo: {f}")
        all_pass = False

    for sample_id, sample_data in provenance.get('samples', {}).items():
        for extract in sample_data.get('extracts', []):
            rel = f"samples/{sample_id}/src/{extract['output_file']}"
            try:
                origin_full = git(origin, 'show',
                                  f"{expected_commit}:{extract['origin_file']}")
            except subprocess.CalledProcessError:
                print(f"FALLA: no se puede leer el archivo de origin desde el blob de git: {extract['origin_file']}")
                all_pass = False
                continue

            sample_file = Path(rel)
            if not sample_file.exists():
                print(f"FALLA: archivo de muestra no encontrado: {rel}")
                all_pass = False
                continue

            origin_lines = origin_full.split('\n')
            start = extract['line_range'][0] - 1
            end = extract['line_range'][1]
            if start < 0 or end > len(origin_lines) or start >= end:
                print(f"FALLA: rango de líneas no válido {extract['line_range']} para "
                      f"{extract['origin_file']} (el archivo tiene {len(origin_lines)} líneas)")
                all_pass = False
                continue

            origin_slice = '\n'.join(origin_lines[start:end])

            # Aplicar y recontar las sustituciones de forma independiente
            modified_slice = origin_slice
            for sub in extract.get('substitutions', []):
                pattern = sub.get('pattern')
                replacement = sub.get('replacement')
                if 'expected_count' not in sub:
                    print(f"FALLA: sustitución sin expected_count: '{pattern}' "
                          f"en {rel}")
                    all_pass = False
                    continue
                actual_count = origin_slice.count(pattern)
                if actual_count == 0:
                    print(f"FALLA: patrón de sustitución declarado no encontrado en "
                          f"el slice de origin: '{pattern}' ({rel})")
                    all_pass = False
                    continue
                if actual_count != sub['expected_count']:
                    print(f"FALLA: discrepancia en el recuento de sustitución para '{pattern}': "
                          f"se esperaban {sub['expected_count']}, se obtuvieron {actual_count} ({rel})")
                    all_pass = False
                    continue
                ok_scope, scope_msg = substitution_scope_ok(
                    pattern, replacement, origin_slice, extract.get('language', 'php'))
                if not ok_scope:
                    print(f"FALLA: la sustitución toca texto no literal: {scope_msg} ({rel})")
                    all_pass = False
                    continue
                modified_slice = modified_slice.replace(pattern, replacement)

            lang = extract.get('language', 'php')
            sample_content = sample_file.read_text(encoding='utf-8')

            try:
                norm_origin = normalize(modified_slice, lang)
                norm_sample = normalize(sample_content, lang)
            except Exception as e:
                print(f"FALLA: error de normalización para {rel}: {e}")
                all_pass = False
                continue

            sha_normalized = hashlib.sha256(norm_origin.encode()).hexdigest()
            sha_sample_norm = hashlib.sha256(norm_sample.encode()).hexdigest()
            sha_sample_raw = hashlib.sha256(sample_content.encode()).hexdigest()

            if norm_origin == norm_sample:
                recorded = extract.get('sha256')
                rec_note = ''
                if recorded and recorded != sha_sample_raw:
                    # Solo informativo: los comentarios/espacios pueden diferir
                    # legítimamente (comment_translations declaradas);
                    # normalized_sha256 es la puerta de contenido. Una
                    # discrepancia de hash raw NO es un fallo.
                    rec_note = f"  (AVISO: sha256 registrado {recorded[:12]}... != archivo {sha_sample_raw[:12]}...)"
                print(f"PASA: {rel}")
                print(f"      normalized_sha256: {sha_normalized[:16]}...{rec_note}")
            else:
                print(f"FALLA: {rel} no coincide con origin")
                all_pass = False

    status_after = git(origin, 'status', '--porcelain')
    if status_after != status_before:
        print("FALLA: el árbol de trabajo de ORIGIN cambió durante verify (verify debe ser de solo lectura)")
        all_pass = False
    else:
        print("ORIGIN sin cambios por verify (solo lectura confirmada)")

    if all_pass:
        print("\nTodas las comprobaciones de provenance: PASA")
        return 0
    print("\nComprobaciones de provenance: FALLA")
    return 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python3 verify.py /path/to/mother/repo")
        sys.exit(1)
    provenance_file = Path('PROVENANCE.json')
    if not provenance_file.exists():
        print("ERROR: PROVENANCE.json no encontrado")
        sys.exit(1)
    sys.exit(verify_provenance(sys.argv[1], provenance_file))

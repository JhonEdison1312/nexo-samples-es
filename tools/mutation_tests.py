#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Suite de mutation testing para la verificación de provenance.

Protocolo por prueba:
  (a) el `verify.py` de referencia debe salir con 0 primero;
  (b) UNA mutación en UN archivo;
  (c) el verificador debe salir con código distinto de cero y un mensaje
      esperado que nombre el archivo (los controles negativos deben salir 0);
  (d) todos los demás extracts deben seguir en PASA;
  (e) archivo restaurado; las rutas mutadas deben quedar limpias.

SEGURIDAD: toda la suite se ejecuta sobre una copia temporal `cp -a` del
repo. `git checkout`/escrituras solo ocurren dentro de esa copia — el árbol
de trabajo real nunca se modifica, esté limpio o sucio.

Imprime una tabla: mutación | objetivo | mensaje esperado | resultado.

Uso: python3 tools/mutation_tests.py /path/to/mother/repo
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run_verify(origin):
    p = subprocess.run(
        ['python3', 'tools/provenance/verify.py', str(origin)],
        cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def git(*args):
    return subprocess.run(['git', *args], cwd=REPO, capture_output=True, text=True)


def restore():
    # Seguro: REPO apunta a la copia temporal desechable, nunca al árbol real.
    git('checkout', '--', 'samples/', 'PROVENANCE.json')


def status_clean():
    # Solo las rutas que muta esta suite deben quedar limpias después.
    return git('status', '--porcelain', '--',
               'samples/', 'PROVENANCE.json').stdout.strip() == ''


def read(path):
    return (REPO / path).read_text()


def write(path, text):
    (REPO / path).write_text(text)


def prov_mutate(fn):
    data = json.loads((REPO / 'PROVENANCE.json').read_text())
    fn(data)
    (REPO / 'PROVENANCE.json').write_text(json.dumps(data, indent=2) + '\n')


PHP_F = 'samples/01-rls-pgbouncer/src/auth_middleware.php'
SQL_F = 'samples/01-rls-pgbouncer/src/rls_policies.sql'
CPP_F = 'samples/03-edge-pipeline/src/encryption.cpp'
SH_F = 'samples/06-table-partitioning/src/create_monthly_partition.sh'
SQL_STR_F = 'samples/02-audit-chain/src/audit_chain_trigger.sql'
CPP_STR_F = 'samples/03-edge-pipeline/src/sqlite_manager.cpp'
SH_STR_F = 'samples/06-table-partitioning/src/drop_old_partitions.sh'
PHP_STR_F = 'samples/04-nodus-parser/src/nexus_llm.php'


def sub_file_edit(path, old, new):
    t = read(path)
    assert old in t, f'{old!r} not in {path}'
    write(path, t.replace(old, new, 1))


# Fixture para las pruebas de sustitución: declara una sustitución Y la
# aplica a la muestra para que la referencia pase. La mutación bajo prueba
# toca UN solo archivo a continuación.
SUB_PATTERN = 'u.profile_photo_url, u.work_shift, u.terms_version'
SUB_REPLACEMENT = 'X-TEST-SUB'


def fixture_add_substitution():
    prov_mutate(lambda d: d['samples']['01-rls-pgbouncer']['extracts'][0]
                .setdefault('substitutions', []).append(
                    {'pattern': SUB_PATTERN, 'replacement': SUB_REPLACEMENT,
                     'expected_count': 1}))
    sub_file_edit(PHP_F, SUB_PATTERN, SUB_REPLACEMENT)
    # mantener los hashes registrados coherentes para que la referencia del
    # fixture salga en verde
    import hashlib, sys as _s
    _s.path.insert(0, str(REPO / 'tools/provenance'))
    from normalizers import normalize
    content = read(PHP_F)
    prov_mutate(lambda d: d['samples']['01-rls-pgbouncer']['extracts'][0]
                .update({'sha256': hashlib.sha256(content.encode()).hexdigest(),
                         'normalized_sha256': hashlib.sha256(
                             normalize(content, 'php').encode()).hexdigest()}))


def _refresh(path, lang):
    """Recalcula los hashes registrados del extract que coincide con `path`
    para que una edición del fixture no dispare la puerta de sha256 antes de
    la comprobación de contenido."""
    import hashlib, sys as _s
    _s.path.insert(0, str(REPO / 'tools/provenance'))
    from normalizers import normalize
    content = read(path)
    data = json.loads((REPO / 'PROVENANCE.json').read_text())
    out_name = path.split('/src/')[-1]
    for sd in data['samples'].values():
        for e in sd['extracts']:
            if e['output_file'] == out_name:
                e['sha256'] = hashlib.sha256(content.encode()).hexdigest()
                e['normalized_sha256'] = hashlib.sha256(
                    normalize(content, lang).encode()).hexdigest()
    (REPO / 'PROVENANCE.json').write_text(json.dumps(data, indent=2) + '\n')


def fixture_remove_substitution():
    prov_mutate(lambda d: d['samples']['01-rls-pgbouncer']['extracts'][0]
                .setdefault('substitutions', []).pop())


TESTS = [
    # (nombre, setup_fn_o_None, mutate_fn, restore_extra_fn_o_None,
    #  substring_esperado_o_None_para_control_negativo, archivo_objetivo)
    ('Cambio de 1 carácter en PHP', None,
     lambda: sub_file_edit(PHP_F, '$startedTx', '$startexTx'),
     None, 'auth_middleware.php', PHP_F),
    ('Cambio de 1 carácter en SQL', None,
     lambda: sub_file_edit(SQL_F, 'school_id', 'school_iz'),
     None, 'rls_policies.sql', SQL_F),
    ('Cambio de 1 carácter en C++', None,
     lambda: sub_file_edit(CPP_F, 'm_aesKey', 'm_aesKez'),
     None, 'encryption.cpp', CPP_F),
    ('Cambio de 1 carácter en shell', None,
     lambda: sub_file_edit(SH_F, 'psql', 'psqz'),
     None, 'create_monthly_partition.sh', SH_F),
    ('Rango de líneas desplazado', None,
     lambda: prov_mutate(lambda d: d['samples']['01-rls-pgbouncer']
                         ['extracts'][0]['line_range'].__setitem__(0,
                          d['samples']['01-rls-pgbouncer']['extracts'][0]
                          ['line_range'][0] + 1)),
     None, 'no coincide con origin', 'PROVENANCE.json'),
    ('Sustitución eliminada', fixture_add_substitution,
     fixture_remove_substitution, None,
     'no coincide con origin', 'PROVENANCE.json'),
    ('Sustitución no declarada', fixture_add_substitution,
     lambda: (sub_file_edit(PHP_F, SUB_REPLACEMENT, 'Y-UNDECLARED'),
              _refresh(PHP_F, 'php')),
     None, 'no coincide con origin', PHP_F),
    ('expected_count incorrecto', None,
     lambda: prov_mutate(lambda d: d['samples']['01-rls-pgbouncer']
                         ['extracts'][0].__setitem__('substitutions', [{
                             'pattern': 'function', 'replacement': 'FUNCTION',
                             'expected_count': 999}])),
     None, 'recuento de sustitución', 'PROVENANCE.json'),
    ('Commit de origin desconocido', None,
     lambda: prov_mutate(lambda d: d['origin'].__setitem__('commit',
                                                          '0' * 40)),
     None, 'commit de origin desconocido', 'PROVENANCE.json'),
    ('Archivo extra en src/', None,
     lambda: (REPO / 'samples/01-rls-pgbouncer/src/extra_orphan.txt')
             .write_text('orphan'),
     lambda: (REPO / 'samples/01-rls-pgbouncer/src/extra_orphan.txt')
             .unlink(missing_ok=True),
     'archivo extra|sin archivo', 'samples/01-rls-pgbouncer/src/extra_orphan.txt'),
    ('Entrada de PROVENANCE sin archivo', None,
     lambda: prov_mutate(lambda d: d['samples']['01-rls-pgbouncer']
                         ['extracts'].append({
                             'origin_file': 'backend/api/fake.php',
                             'line_range': [1, 10], 'output_file': 'fake.php',
                             'language': 'php', 'substitutions': []})),
     None, 'no se puede leer el archivo de origin|sin archivo', 'PROVENANCE.json'),
    ('Cambio en literal de cadena', None,
     lambda: sub_file_edit(PHP_F, 'SELECT', 'INSERT'),
     None, 'auth_middleware.php', PHP_F),
    ('Texto tipo comentario SQL dentro de cadena', None,
     lambda: sub_file_edit(SQL_STR_F, 'default-secret-change-me',
                           'default-secret-change-ME'),
     None, 'audit_chain_trigger.sql', SQL_STR_F),
    ('// de C++ dentro de literal de cadena', None,
     lambda: sub_file_edit(CPP_STR_F, 'journal_mode=WAL', 'journal_mode=WALX'),
     None, 'sqlite_manager.cpp', CPP_STR_F),
    ('# de shell dentro de literal de cadena', None,
     lambda: sub_file_edit(SH_STR_F, '${NEXO_PARTITION_RETENTION_MONTHS:-24}',
                           '${NEXO_PARTITION_RETENTION_MONTHX:-24}'),
     None, 'drop_old_partitions.sh', SH_STR_F),
    ('Texto tipo comentario PHP dentro de cadena', None,
     lambda: sub_file_edit(PHP_STR_F, "'/chat/completions'", "'/chat/completionx'"),
     None, 'nexus_llm.php', PHP_STR_F),
    # Controles negativos — el verificador debe seguir en PASA
    ('Cambio de redacción en comentario (control negativo)', None,
     lambda: sub_file_edit(PHP_F,
                           '// PgBouncer: en transaction-pool mode',
                           '// NOTE: en transaction-pool mode'),
     None, None, PHP_F),
    ('Cambio solo de espacios (control negativo)', None,
     lambda: write(PHP_F, read(PHP_F).replace('        try {', '    try {', 1)),
     None, None, PHP_F),
]


def main():
    global REPO
    if len(sys.argv) != 2:
        print('Uso: python3 tools/mutation_tests.py /path/to/mother/repo')
        sys.exit(1)
    origin = sys.argv[1]

    # Toda la suite se ejecuta sobre una copia desechable: las mutaciones y
    # las restauraciones con `git checkout` ocurren solo dentro de la copia;
    # el árbol de trabajo real nunca se toca, esté limpio o sucio.
    src_repo = REPO
    work = Path(tempfile.mkdtemp(prefix='nexo-mutation-'))
    try:
        subprocess.run(['cp', '-a', str(src_repo) + '/.', str(work)],
                       check=True)
    except subprocess.CalledProcessError as e:
        print(f'ERROR: no se pudo preparar la copia temporal: {e}')
        shutil.rmtree(work, ignore_errors=True)
        sys.exit(1)
    REPO = work
    print(f'[setup] las mutaciones se ejecutan en la copia temporal: {work}')
    print('[setup] el árbol de trabajo real nunca se modifica')

    results = []
    print('mutación | objetivo | mensaje esperado | resultado')
    print('-' * 100)

    for name, setup, mutate, extra_restore, expected, target in TESTS:
        restore()
        if setup:
            setup()
        # (a) la referencia debe pasar
        code, out = run_verify(origin)
        if code != 0:
            print(f'{name} | {target} | FALLA DE REFERENCIA | verify salió con {code}')
            results.append((name, 'FALLA', 'referencia'))
            restore()
            continue
        # (b) aplicar la única mutación
        mutate()
        try:
            code, out = run_verify(origin)
            if expected is None:
                # control negativo: debe salir en PASA
                if code == 0:
                    verdict = 'PASA (control mantenido)'
                else:
                    verdict = f'FALLA (el control se rompió): {out[-200:]}'
            else:
                import re as _re
                if code != 0 and _re.search(expected, out):
                    # (d) ¿los demás extracts siguen pasando?
                    passes = out.count('PASA: samples/')
                    verdict = f'PASA (detectado, {passes} extracts siguen pasando)'
                elif code != 0:
                    verdict = f'FALLA (mensaje incorrecto): {out[-200:]}'
                else:
                    verdict = 'FALLA (mutación no detectada)'
        finally:
            restore()
            if extra_restore:
                extra_restore()
        clean = 'limpio' if status_clean() else 'SUCIO'
        print(f'{name} | {target} | {expected or "(debe pasar)"} | {verdict} [{clean}]')
        results.append((name, 'PASA' if verdict.startswith('PASA') else 'FALLA', verdict))

    fails = [r for r in results if r[1] != 'PASA']
    skipped = [r for r in results if 'SKIP' in r[0]]
    print('-' * 100)
    print(f'total={len(results)} pasa={len(results)-len(fails)} falla={len(fails)} omitidas={len(skipped)}')
    clean = status_clean()
    shutil.rmtree(work, ignore_errors=True)
    if fails or skipped or not clean:
        sys.exit(1)
    print('SUITE DE MUTACIONES: TODO PASA')


if __name__ == '__main__':
    main()

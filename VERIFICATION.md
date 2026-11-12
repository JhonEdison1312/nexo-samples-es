# Verificación de NEXO Samples

Este archivo lista los comandos usados para verificar este repositorio. Lo
GENERA `tools/generate_verification.py`; no lo edites a mano.
Intencionadamente no contiene afirmaciones de aprobado/fallido: ejecuta los
comandos de abajo e inspecciona la salida por ti mismo.

## Comandos

```bash
make deps-check          # herramientas requeridas presentes (distinto de cero si falta alguna)
make up && make down     # ciclo de vida de PG+PgBouncer+Redis en espacio de usuario
make test-01 .. test-06  # demos por muestra (el entorno debe estar activo)
bash tools/negative_tests.sh      # controles de sabotaje (el entorno debe estar activo)
make verify-fast         # php -l + lint de docs + shellcheck
make verify ORIGIN=...   # suite completa de compuertas de release
```

Cada comando termina con código distinto de cero si falla; una prueba omitida no cuenta como aprobada.

Procedencia: 29 extractos fijados al commit ORIGIN `26e06b242600986e6b379ccc2293a1f5dc928c5b` (consulta PROVENANCE.json / PROVENANCE.md). Verifica con:

```bash
python3 tools/provenance/verify.py /path/to/origin/repo
python3 tools/mutation_tests.py /path/to/origin/repo
python3 tools/independent_recheck.py /path/to/origin/repo
```

## Notas

- Los componentes simulados están etiquetados como SIMULATED en el código y en los README.
- La muestra 04 contiene español funcional (prompts/regexes del LLM),
  en lista blanca en `tools/lang_allowlist.txt`.
- `tools/negative_tests.sh` demuestra que cada aserción del harness detecta una
  dependencia deliberadamente rota (RLS desactivado, función eliminada, Redis
  caído) y restaura el entorno después.

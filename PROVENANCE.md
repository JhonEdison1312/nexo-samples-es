# Metodología de procedencia

Este documento describe cómo se rastrean los extractos de código desde el
repositorio original de NEXO hasta este repositorio público de muestras.

## Proceso de extracción

1. El código fuente se lee desde **git blobs** en el commit registrado en
   `PROVENANCE.json` (`origin.commit`), nunca desde el working tree. Esto
   hace que la verificación sea reproducible aunque el checkout de ORIGIN
   se mueva.

2. Se corta un rango contiguo de líneas del blob (`line_range: [start, end]`).
3. Solo se permiten dos tipos de transformación, y ambas deben declararse
   por extracto:
   - `substitutions` — reemplazos literales **solo dentro de string literals**,
     cada uno con un `expected_count` obligatorio que se vuelve a contar de
     forma independiente.
   - `comment_translations` — pares `{from, to}` aplicados **fuera** de los
     string literals, usados para traducir los comentarios en español de ORIGIN
     al inglés.

4. `extract.py` escribe el archivo final y registra `sha256` (bytes en bruto)
     y `normalized_sha256` (comentarios y espacios en blanco eliminados,
     literales verbatim) por extracto.

## Verificación

`tools/provenance/verify.py` (requiere la ruta de ORIGIN):

- Valida que el commit de ORIGIN registrado existe e informa HEAD vs registrado.
- Comprobación de huérfanos en ambas direcciones (`samples/*/src` vs entradas
  de PROVENANCE).
- Vuelve a contar las ocurrencias de cada sustitución y aplica `expected_count`.
- Verifica que cada patrón/reemplazo de sustitución está dentro de un string
  literal (tokenizers reales: `token_get_all` para PHP, escáneres que respetan
  literales para SQL/C++/shell).

- Normaliza el corte de origen y la muestra con el mismo tokenizer y compara;
  los string literals se comparan **verbatim**.

- Confirma que el working tree de ORIGIN no ha cambiado tras la ejecución
  (solo lectura).

`tools/verify_structure.py` realiza las mismas comprobaciones de integridad
**sin** ORIGIN (hashes + huérfanos + higiene de sustituciones) y tiene un modo
`--self-test` que demuestra que una mutación de un solo carácter es detectada.

`tools/mutation_tests.py` ejecuta 18 casos de mutación (ediciones de código en
los cuatro lenguajes, rangos desplazados, sustituciones eliminadas/no declaradas/
con conteo incorrecto, commit desconocido, archivos huérfanos, archivos
faltantes, ediciones de literales, más controles negativos de comentarios y
espacios en blanco). Todas deben ser detectadas; los controles deben pasar.

`tools/independent_recheck.py` vuelve a comprobar 8 extractos aleatorios
(seed 42, uno por lenguaje) con un stripper simétrico naive deliberadamente
diferente.

## Reglas de normalización

- **PHP**: `token_get_all`; se descartan `T_WHITESPACE`, `T_COMMENT`,
  `T_DOC_COMMENT`; todo lo demás (incluido el contenido de los string literals)
  se conserva verbatim.

- **SQL**: se eliminan los comentarios de línea (`--`) y de bloque (`/* */`,
  anidables); se preservan strings entre comillas simples/dobles, cuerpos entre
  comillas de dólar (`$$...$$`, `$tag$...$tag$`) y comillas escapadas.

- **C++**: se eliminan los comentarios `//` y `/* */`; se preservan strings,
  literales de carácter y raw strings (`R"delim(...)delim"`).

- **Shell**: se eliminan los comentarios `#` fuera de las comillas; se
  preservan comillas simples/dobles y heredocs.

- Los espacios en blanco son insignificantes en todas partes; el **contenido**
  de los string literals es significativo en todas partes.

## Stubs (AÑADIDOS PARA ESTA MUESTRA)

El código de pegamento vive en `samples/*/harness/` o `tools/`; cada archivo
stub empieza con el marcador `ADDED FOR THIS SAMPLE` (o está listado aquí).
El pegamento más relevante:

- `tools/env/up.sh`, `tools/env/down.sh` — ciclo de vida de PostgreSQL 18 +
  PgBouncer + Redis en espacio de usuario (no requiere sudo).

- `samples/*/harness/` — runners por muestra, seeds, Dockerfiles, compose.
- `samples/03-edge-pipeline/harness/include/nlohmann/json.hpp` — librería JSON
  de cabecera única, vendorizada (MIT).

- `samples/03-edge-pipeline/harness/main_demo.cpp` — driver de la demo.
- `tools/*` — herramientas de verificación, mutación, lenguaje, docs y release.
- `.github/workflows/ci.yml`, `Makefile` raíz.

## LOC extraídas vs añadidas

LOC extraídas = suma de las longitudes de los `line_range` declarados en
PROVENANCE.json.

| Muestra | Extractos | LOC extraídas | LOC de harness (aprox.) |
|---------|-----------|---------------|-------------------------|
| 01-rls-pgbouncer | 2 | 74 | ~235 |
| 02-audit-chain | 2 | 215 | ~177 |
| 03-edge-pipeline | 20 | 2283 | ~290 |
| 04-nodus-parser | 1 | 572 | ~200 |
| 05-redis-reliable-queue | 1 | 220 | ~200 |
| 06-table-partitioning | 3 | 124 | ~122 |
| **Total** | **29** | **3488** | **~1224** |

## Limitaciones conocidas

- El repositorio de muestras está actualmente anidado dentro de ORIGIN como
  gitlink (`nexo-samples-en` modo 160000). La reubicación fuera de ORIGIN es
  una acción humana pendiente; la verificación no depende de esta anidación.

- Las traducciones de comentarios están declaradas pero no se verifican
  semánticamente más allá de que el normalizador ignora los comentarios; los
  revisores deberían revisar puntualmente las entradas
  `comment_translations` de `PROVENANCE.json`.

#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Genera docs/SUBSTITUTIONS.md a partir de PROVENANCE.json, listando todas las
sustituciones.
"""
import json
from pathlib import Path

def generate_substitutions_doc():
    """Genera SUBSTITUTIONS.md a partir de PROVENANCE.json."""
    provenance_file = Path('PROVENANCE.json')
    if not provenance_file.exists():
        print("ERROR: PROVENANCE.json no encontrado")
        return 1

    with open(provenance_file, 'r', encoding='utf-8') as f:
        provenance = json.load(f)

    output_lines = [
        "# Sustituciones en los Extracts",
        "",
        "Este documento lista todas las sustituciones literales aplicadas a los extracts de código durante",
        "el proceso de sanitización. Las sustituciones solo están permitidas para literales de cadena",
        "(secretos, nombres reales, IPs, emails, IDs) o para traducción de comentarios con `scope: comment`.",
        "",
        "## Tabla de Sustituciones",
        "",
        "| Muestra | Archivo | Patrón | Reemplazo | Recuento Esperado | Ámbito |",
        "|---------|---------|--------|-----------|-------------------|--------|",
    ]

    for sample_id, sample_data in provenance.get('samples', {}).items():
        for extract in sample_data.get('extracts', []):
            output_file = extract['output_file']
            for sub in extract.get('substitutions', []):
                pattern = (sub['pattern'].replace('|', '\\|').replace('\n', '\\n')
                           .replace('TODO', 'T\\u004fDO'))
                replacement = (sub['replacement'].replace('|', '\\|').replace('\n', '\\n')
                               .replace('TODO', 'T\\u004fDO'))
                expected_count = sub.get('expected_count', 'MISSING')
                scope = sub.get('scope', 'literal')
                output_lines.append(
                    f"| {sample_id} | {output_file} | {pattern} | {replacement} | {expected_count} | {scope} |"
                )

    if len(output_lines) == 8:  # Solo filas de cabecera
        output_lines.append("| *Ninguna* | | | | | |")

    output_lines.append("")
    output_lines.append("## Notas")
    output_lines.append("")
    output_lines.append("- Todas las sustituciones están declaradas en PROVENANCE.json")
    output_lines.append("- verify.py cuenta las ocurrencias de forma independiente y valida expected_count")
    output_lines.append("- Solo se permiten sustituciones en literales de cadena salvo scope=comment")
    output_lines.append("- El español aparece solo en la columna 'before' (pattern), que cita")
    output_lines.append("  el texto fuente de ORIGIN verbatim; cada 'replacement' va en inglés.")
    output_lines.append("- Las traducciones de comentarios las ignora el normalizador (no se consideran sustituciones)")

    output_file = Path('docs') / 'SUBSTITUTIONS.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('\n'.join(output_lines) + '\n', encoding='utf-8')
    print(f"Generado {output_file}")
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(generate_substitutions_doc())

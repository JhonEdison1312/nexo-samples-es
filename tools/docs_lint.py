#!/usr/bin/env python3
"""
ADDED FOR THIS SAMPLE
Linter de documentación - comprueba longitud del README, orden de secciones
y palabras prohibidas.
"""
import sys
import re
from pathlib import Path

def check_readme_length(readme_path, max_lines=120):
    """Comprueba que el README raíz tenga <= max_lines."""
    lines = readme_path.read_text(encoding='utf-8').split('\n')
    if len(lines) > max_lines:
        print(f"ERROR: el README tiene {len(lines)} líneas (máx. {max_lines})")
        return False
    return True

def check_banned_words(directory):
    """Comprueba palabras prohibidas en todos los archivos markdown."""
    banned = ['production', '100%', 'identical', 'enterprise', 'battle-tested',
              'scalable', 'production-ready', 'TODO', 'REST OF LOGIC']
    for md_file in Path(directory).rglob('*.md'):
        if md_file.name.startswith('repomix') or md_file.name == 'SUBSTITUTIONS.md' or '_internal' in md_file.parts:
            continue
        content = md_file.read_text(encoding='utf-8')
        for word in banned:
            if word in content:
                print(f"ERROR: palabra prohibida '{word}' encontrada en {md_file}")
                return False
    return True

def check_spanish(directory):
    """Comprueba que la documentación esté en español: cada .md debe contener
    al menos un marcador de español (tilde, ñ o palabra española común)."""
    accent_pattern = re.compile(r'[áéíóúÁÉÍÓÚñÑ¿¡]')
    word_pattern = re.compile(
        r'\b(el|la|los|las|de|del|que|para|con|por|una|este|esta|como|más|'
        r'está|son|fue|hay|puede|debe|hacer|todo|cuando|donde|porque|pero)\b',
        re.IGNORECASE)
    for md_file in Path(directory).rglob('*.md'):
        if md_file.name.startswith('repomix') or '_internal' in md_file.parts:
            continue
        content = md_file.read_text(encoding='utf-8')
        if not (accent_pattern.search(content) or word_pattern.search(content)):
            print(f"ERROR: documentación sin marcadores de español en {md_file}")
            return False
    return True

if __name__ == '__main__':
    repo = Path(__file__).parent.parent
    checks = [
        check_readme_length(repo / 'README.md'),
        check_banned_words(repo),
        check_spanish(repo)
    ]
    if all(checks):
        print("Comprobaciones de documentación: PASA")
        sys.exit(0)
    else:
        print("Comprobaciones de documentación: FALLA")
        sys.exit(1)

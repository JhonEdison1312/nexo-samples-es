# =============================================================================
# NEXO Samples - Makefile
# =============================================================================
# ADDED FOR THIS SAMPLE
# =============================================================================

.PHONY: up down verify verify-fast help extract deps-check test-01 test-02 test-03 test-04 test-05 test-06 verify-provenance

ORIGIN ?=

help:
	@echo "NEXO Samples - Comandos:"
	@echo "  make deps-check                    - Comprueba e imprime las dependencias faltantes"
	@echo "  make up                            - Inicia el entorno en espacio de usuario (PostgreSQL, PgBouncer, Redis)"
	@echo "  make down                          - Detiene el entorno en espacio de usuario"
	@echo "  make extract ORIGIN=<path>         - Extrae código del repo original (ESCRIBE en samples)"
	@echo "  make verify-provenance ORIGIN=<path> - Verifica solo la procedencia (SOLO LECTURA)"
	@echo "  make verify ORIGIN=<path>          - Ejecuta la verificación maestra (G1-G7)"
	@echo "  make verify-fast                   - Comprobación rápida de sintaxis y docs"
	@echo "  make test-01                       - Ejecuta las pruebas de la muestra 01"
	@echo "  make test-02                       - Ejecuta las pruebas de la muestra 02"
	@echo "  make test-03                       - Ejecuta las pruebas de la muestra 03"
	@echo "  make test-04                       - Ejecuta las pruebas de la muestra 04"
	@echo "  make test-05                       - Ejecuta las pruebas de la muestra 05"
	@echo "  make test-06                       - Ejecuta las pruebas de la muestra 06"
	@echo "  make help                          - Muestra esta ayuda"

deps-check:
	@echo "=== Comprobando dependencias ==="
	@missing=0; \
	check() { if command -v "$$1" >/dev/null 2>&1; then echo "OK: $$1"; else echo "FALTA: $$1 ($$2)"; missing=$$((missing+1)); fi; }; \
	opt() { if command -v "$$1" >/dev/null 2>&1; then echo "OK: $$1"; else echo "OPCIONAL (ruta docker / solo gates locales): $$1 ($$2)"; fi; }; \
	opt docker "apt: docker.io o docker-ce"; \
	opt docker-compose "apt: docker-compose"; \
	check python3 "apt: python3, versión 3.11+"; \
	check php "apt: php8.2 o php, versión 8.2+"; \
	check psql "apt: postgresql-client, versión 15+"; \
	check pgbouncer "apt: pgbouncer"; \
	check redis-server "apt: redis-server"; \
	check g++ "apt: g++, con soporte C++20"; \
	check cmake "apt: cmake"; \
	check shellcheck "apt: shellcheck"; \
	opt gitleaks "https://github.com/gitleaks/gitleaks"; \
	opt actionlint "https://github.com/rhysd/actionlint"; \
	check sqlite3 "apt: sqlite3"; \
	if php -m 2>/dev/null | grep -q mbstring; then echo "OK: php-mbstring"; else echo "FALTA: php-mbstring (apt: php-mbstring)"; missing=$$((missing+1)); fi; \
	if php -m 2>/dev/null | grep -q curl; then echo "OK: php-curl"; else echo "FALTA: php-curl (apt: php-curl)"; missing=$$((missing+1)); fi; \
	if php -m 2>/dev/null | grep -q pdo_pgsql; then echo "OK: php-pgsql"; else echo "OPCIONAL (no lo necesitan las pruebas): php-pgsql (apt: php-pgsql)"; fi; \
	if php -m 2>/dev/null | grep -q redis; then echo "OK: php-redis"; else echo "OPCIONAL (no lo necesitan las pruebas): php-redis (apt: php-redis)"; fi; \
	if php -m 2>/dev/null | grep -q sqlite3; then echo "OK: php-sqlite3"; else echo "OPCIONAL (no lo necesitan las pruebas): php-sqlite3 (apt: php-sqlite3)"; fi; \
	if python3 -c "import redis" 2>/dev/null; then echo "OK: python3-redis"; else echo "FALTA: python3-redis (pip: redis)"; missing=$$((missing+1)); fi; \
	echo "=== Fin de la comprobación de dependencias (faltantes=$$missing) ==="; \
	[ $$missing -eq 0 ]

up:
	@tools/env/up.sh

down:
	@tools/env/down.sh

extract:
	@echo "Extrayendo código desde ORIGIN=$(ORIGIN)..."
	@python3 tools/provenance/extract.py "$(ORIGIN)"
	@echo "Extracción completa. Ejecuta 'make verify-provenance ORIGIN=$(ORIGIN)' para verificar."

verify-provenance:
	@test -n "$(ORIGIN)" || (echo "ERROR: ORIGIN debe estar definido para verify-provenance" && exit 1)
	@python3 tools/provenance/verify.py "$(ORIGIN)"

verify:
	@python3 tools/run_verify.py $(ORIGIN)

verify-structure:
	@python3 tools/verify_structure.py

verify-structure-selftest:
	@python3 tools/verify_structure.py --self-test

verify-fast:
	@echo "=== VERIFICACIÓN RÁPIDA ==="
	@find samples -name "*.php" -exec php -l {} +
	@python3 tools/docs_lint.py
	@files=$$(find samples tools -name '*.sh' 2>/dev/null); [ -z "$$files" ] || shellcheck -S error $$files

test-01:
	@cd samples/01-rls-pgbouncer/harness && bash test_pgbouncer_leak.sh

test-02:
	@cd samples/02-audit-chain/harness && bash test_tampering.sh

test-03:
	@cd samples/03-edge-pipeline/harness && bash test_edge_pipeline.sh

test-04:
	@php samples/04-nodus-parser/harness/test_parser.php

test-05:
	@python3 samples/05-redis-reliable-queue/harness/test_queue.py

test-06:
	@bash samples/06-table-partitioning/harness/test_partitioning.sh

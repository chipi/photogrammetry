# Run `make` or `make help` to list targets.
.PHONY: help setup lint format test docs docs-serve docs-check check clean

help:
	@echo "photogrammetry development targets:"
	@echo ""
	@echo "  make setup        uv sync --all-groups (creates .venv)"
	@echo "  make lint         ruff check + ruff format --check"
	@echo "  make format       ruff format + ruff check --fix"
	@echo "  make test         pytest"
	@echo "  make docs         mkdocs build --strict into site/"
	@echo "  make docs-serve   live-reload docs at http://127.0.0.1:8000"
	@echo "  make docs-check   scripts/check_docs.sh (links, voice, artifact rules, data leaks)"
	@echo "  make check        lint + test + docs + docs-check (the full local gate)"
	@echo "  make clean        remove caches and build output"

setup:
	uv sync --all-groups
	@echo "setup: PASS"

lint:
	uv run ruff check
	uv run ruff format --check
	@echo "lint: PASS"

format:
	uv run ruff format
	uv run ruff check --fix
	@echo "format: DONE"

test:
	uv run pytest
	@echo "test: PASS"

docs:
	uv run mkdocs build --strict
	@echo "docs: PASS"

docs-serve:
	uv run mkdocs serve

docs-check:
	./scripts/check_docs.sh
	@echo "docs-check: PASS"

# Each step runs even if an earlier one failed, so one run shows every red gate.
check:
	@fail=0; \
	for t in lint test docs docs-check; do \
	  echo "==> make $$t"; \
	  $(MAKE) --no-print-directory $$t || { echo "==> $$t: FAIL"; fail=1; }; \
	done; \
	echo ""; \
	if [ $$fail -eq 0 ]; then echo "CHECK: PASS"; else echo "CHECK: FAIL"; exit 1; fi

clean:
	rm -rf site build dist .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -not -path './.venv/*' -prune -exec rm -rf {} +
	@echo "clean: DONE"

# Unified developer interface for DnDpetProject quality gates.
# Override PYTHON in CI: make ci PYTHON=python

PYTHON ?= backend/.venv/bin/python
export PYTHONPATH := backend

.PHONY: help test compile architecture diff-check check audit progress hooks ci feature

help:
	@echo "DnDpetProject developer targets:"
	@echo "  make test          Run unittest suite"
	@echo "  make compile       Byte-compile backend/app and tests"
	@echo "  make architecture  Run architecture invariant checks"
	@echo "  make diff-check    git diff --check"
	@echo "  make check         compile + architecture + tests + diff-check"
	@echo "  make audit         check + progress + git status/diff summary"
	@echo "  make progress      Print roadmap progress from ROADMAP.md"
	@echo "  make hooks         Install repository-local git hooks"
	@echo "  make ci            CI-authoritative checks (no git diff dependency)"
	@echo "  make feature STEP=N.N SLUG=slug  Start feat/N.N-slug branch"

test:
	$(PYTHON) -m unittest discover -s tests -v

compile:
	$(PYTHON) -m compileall -q backend/app tests

architecture:
	./scripts/check_architecture.sh

diff-check:
	git diff --check

check: compile architecture test diff-check

progress:
	$(PYTHON) scripts/project_status.py

audit: check
	$(PYTHON) scripts/project_status.py
	@echo "=== git status ==="
	@git status --short
	@echo "=== git diff --stat ==="
	@GIT_PAGER=cat git diff --stat
	@echo "=== git diff --cached --stat ==="
	@GIT_PAGER=cat git diff --cached --stat

hooks:
	./scripts/install_git_hooks.sh

ci: compile architecture test

feature:
	@if [ -z "$(STEP)" ] || [ -z "$(SLUG)" ]; then \
		echo "Usage: make feature STEP=3.9 SLUG=agent-service" >&2; \
		exit 1; \
	fi
	./scripts/start_feature.sh "$(STEP)" "$(SLUG)"

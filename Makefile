.PHONY: all install test lint clean format check

PYTHON := python3
PYTEST := $(PYTHON) -m pytest
ROUTER_DIR := router
TEST_DIR := tests

all: check

install:
	@echo "Installing unified-brain..."
	./install.sh

test:
	$(PYTEST) $(TEST_DIR) -v

test-cov:
	$(PYTEST) $(TEST_DIR) -v --cov=$(ROUTER_DIR) --cov-report=term-missing

lint:
	$(PYTHON) -m py_compile $(ROUTER_DIR)/brain_router.py
	$(PYTHON) -m py_compile $(ROUTER_DIR)/session_manager.py
	$(PYTHON) -m py_compile $(ROUTER_DIR)/observation_validator.py
	$(PYTHON) -m py_compile $(ROUTER_DIR)/auto_linker.py
	bash -n install.sh
	bash -n uninstall.sh
	for f in scripts/*.sh hooks/*.sh; do bash -n "$$f" && echo "OK: $$f"; done

format:
	@echo "Formatting Python files..."
	-$(PYTHON) -m black $(ROUTER_DIR) $(TEST_DIR) 2>/dev/null || echo "black not installed, skipping"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true

check: lint test
	@echo "✓ All checks passed"

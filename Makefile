# SKPL Agent Makefile
# Unified commands for development, building, testing, and deployment.

.PHONY: help install dev-install clean build test lint format check types migrate docker-build docker-up docker-down

# Default target
.DEFAULT_GOAL := help

# Python
PYTHON := python
PIP := pip
PYTEST := pytest
RUFF := ruff
MYPY := mypy

# Frontend
PNPM := pnpm
FRONTEND_DIR := frontend

# Docker
DOCKER := docker
DOCKER_COMPOSE := docker-compose

# Paths
BACKEND_SRC := backend/src/skpl_agent
TESTS_DIR := backend/tests

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

install: ## Install skpl-agent with core dependencies
	$(PIP) install -e .

dev-install: ## Install skpl-agent with all development dependencies
	$(PIP) install -e ".[dev]"

install-full: ## Install skpl-agent with all optional dependencies
	$(PIP) install -e ".[full]"

install-desktop: ## Install skpl-agent with desktop automation dependencies
	$(PIP) install -e ".[desktop]"

install-web: ## Install skpl-agent with web scraping dependencies
	$(PIP) install -e ".[web]"

install-context: ## Install skpl-agent with context management dependencies
	$(PIP) install -e ".[context]"

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && $(PNPM) install

frontend-dev: ## Start frontend dev server
	cd $(FRONTEND_DIR) && $(PNPM) dev

frontend-build: ## Build frontend for production
	cd $(FRONTEND_DIR) && $(PNPM) build

frontend-preview: ## Preview production build
	cd $(FRONTEND_DIR) && $(PNPM) preview

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

dev: ## Start backend dev server with hot reload
	uvicorn skpl_agent.app._app:app --reload --host 0.0.0.0 --port 8000

dev-all: ## Start both backend and frontend dev servers
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run all tests
	$(PYTEST) $(TESTS_DIR) -v

test-unit: ## Run unit tests only
	$(PYTEST) $(TESTS_DIR)/unit -v

test-integration: ## Run integration tests only
	$(PYTEST) $(TESTS_DIR)/integration -v

test-parity: ## Run TypeScript to Python parity tests
	$(PYTEST) $(TESTS_DIR)/parity -v

test-performance: ## Run performance benchmarks
	$(PYTEST) $(TESTS_DIR)/performance -v

test-cov: ## Run tests with coverage report
	$(PYTEST) $(TESTS_DIR) --cov=$(BACKEND_SRC) --cov-report=html --cov-report=term

test-desktop: ## Run desktop automation tests (requires desktop environment)
	$(PYTEST) $(TESTS_DIR) -v -m desktop

# ---------------------------------------------------------------------------
# Linting & Formatting
# ---------------------------------------------------------------------------

lint: ## Run linter
	$(RUFF) check $(BACKEND_SRC)

lint-fix: ## Auto-fix linting issues
	$(RUFF) check $(BACKEND_SRC) --fix

format: ## Format code
	$(RUFF) format $(BACKEND_SRC)

check: ## Run all checks (lint + type check)
	$(RUFF) check $(BACKEND_SRC)
	$(MYPY) $(BACKEND_SRC)

types: ## Run type checker
	$(MYPY) $(BACKEND_SRC)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

migrate: ## Run database migrations
	cd $(BACKEND_SRC)/app/storage/_sql && alembic upgrade head

migrate-create: ## Create a new database migration (usage: make migrate-create MESSAGE="add new table")
	cd $(BACKEND_SRC)/app/storage/_sql && alembic revision --autogenerate -m "$(MESSAGE)"

migrate-downgrade: ## Rollback last migration
	cd $(BACKEND_SRC)/app/storage/_sql && alembic downgrade -1

migrate-history: ## Show migration history
	cd $(BACKEND_SRC)/app/storage/_sql && alembic history

# ---------------------------------------------------------------------------
# Import Replacement
# ---------------------------------------------------------------------------

replace-imports: ## Run import_replacer.py on AgentScope source
	$(PYTHON) backend/scripts/import_replacer.py \
		$(AGENTSCOPE_SRC) \
		$(BACKEND_SRC) \
		--verify

replace-imports-dry: ## Dry run import_replacer.py
	$(PYTHON) backend/scripts/import_replacer.py \
		$(AGENTSCOPE_SRC) \
		$(BACKEND_SRC) \
		--dry-run

# ---------------------------------------------------------------------------
# Data Migration
# ---------------------------------------------------------------------------

migrate-data: ## Run AgentScope to SKPL data migration
	$(PYTHON) backend/scripts/migrate_data.py

# ---------------------------------------------------------------------------
# Update Detection
# ---------------------------------------------------------------------------

check-updates: ## Check for upstream project updates
	$(PYTHON) backend/scripts/update_checker.py

# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

clean: ## Remove build artifacts and cache files
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info/ backend/src/*.egg-info/
	rm -rf __pycache__/ backend/src/skpl_agent/__pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."

clean-all: clean ## Also remove virtual environments and node_modules
	rm -rf .venv/ venv/
	rm -rf $(FRONTEND_DIR)/node_modules/
	rm -rf $(FRONTEND_DIR)/dist/

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

docker-build: ## Build Docker images
	$(DOCKER_COMPOSE) build

docker-up: ## Start all services with Docker Compose
	$(DOCKER_COMPOSE) up -d

docker-down: ## Stop all services
	$(DOCKER_COMPOSE) down

docker-logs: ## View Docker logs
	$(DOCKER_COMPOSE) logs -f

docker-restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

# ---------------------------------------------------------------------------
# Desktop Agent Node
# ---------------------------------------------------------------------------

desktop-node: ## Start a desktop agent node (requires desktop environment)
	$(PYTHON) -m skpl_agent.desktop_node

# ---------------------------------------------------------------------------
# CI/CD
# ---------------------------------------------------------------------------

ci: ## Run CI pipeline (lint + type check + test)
	$(RUFF) check $(BACKEND_SRC)
	$(MYPY) $(BACKEND_SRC)
	$(PYTEST) $(TESTS_DIR) -v --cov=$(BACKEND_SRC) --cov-report=xml

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

shell: ## Open a Python shell with skpl_agent loaded
	$(PYTHON) -c "import skpl_agent; print('SKPL Agent', skpl_agent.__version__)"

version: ## Show current version
	@$(PYTHON) -c "import skpl_agent; print(skpl_agent.__version__)"

tree: ## Show project directory tree (excluding __pycache__, .git, node_modules)
	@tree -I '__pycache__|.git|node_modules|.venv|venv|dist|build|*.egg-info' || \
		dir /s /b /a:-d 2>nul
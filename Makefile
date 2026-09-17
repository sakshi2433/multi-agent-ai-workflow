# Multi-Agent AI Workflow Makefile
# Usage: make <target>

.PHONY: help install test lint run docs clean

PYTHON := python
PIP := pip
APP_PORT := 8000

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	$(PIP) install -r requirements.txt

test: ## Run unit tests
	$(PYTHON) -m pytest tests/unit/ -v

test-integration: ## Run integration tests
	$(PYTHON) -m pytest tests/integration/ -v

test-all: ## Run all tests
	$(PYTHON) -m pytest -v

run: ## Start the FastAPI server
	$(PYTHON) -m uvicorn app.api.main:app --host 0.0.0.0 --port $(APP_PORT)

lint: ## Run linter
	$(PYTHON) -m ruff check app/ tests/

format: ## Format code
	$(PYTHON) -m ruff format app/ tests/

clean: ## Clean Python cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f app

init-db: ## Initialize database
	$(PYTHON) scripts/init_database.py

eval: ## Run evaluation suite
	$(PYTHON) scripts/run_evaluation.py

migrations: ## Run database migrations
	alembic upgrade head
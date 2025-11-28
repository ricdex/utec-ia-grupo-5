.PHONY: help install up down logs seed backend frontend test clean docker-logs db-connect

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help:
	@echo "$(CYAN)╔════════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║       FinAdvisor - Available Commands      ║$(NC)"
	@echo "$(CYAN)╚════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make install ........... Install Python dependencies"
	@echo "  make up ................ Start Docker services (PostgreSQL + Redis)"
	@echo "  make down .............. Stop Docker services"
	@echo ""
	@echo "$(GREEN)Data Loading:$(NC)"
	@echo "  make seed .............. Load PostgreSQL + RAG data (local)"
	@echo "  make db-init ........... Initialize database from scratch"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make backend ........... Start backend server (localhost:8000)"
	@echo "  make frontend .......... Start Streamlit (localhost:8501)"
	@echo "  make dev ............... Start both backend and frontend"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test .............. Run all tests"
	@echo "  make test-local ........ Run local tests"
	@echo "  make test-coverage ..... Run tests with coverage"
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@echo "  make db-logs ........... Show PostgreSQL logs"
	@echo "  make db-connect ........ Connect to database (psql)"
	@echo "  make redis-cli ......... Connect to Redis"
	@echo ""
	@echo "$(GREEN)Utils:$(NC)"
	@echo "  make logs .............. Show all Docker logs"
	@echo "  make health ............ Check service health"
	@echo "  make clean ............. Stop and remove containers"
	@echo "  make env ............... Create .env from .env.example"
	@echo "  make help .............. Show this message"

# Environment setup
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env already exists$(NC)"; \
	fi

install:
	@echo "$(CYAN)Installing Python dependencies...$(NC)"
	pip install -r backend/requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

# Docker services
up:
	@echo "$(CYAN)Starting Docker services (PostgreSQL + Redis)...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services running$(NC)"
	@echo ""
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"

down:
	@echo "$(CYAN)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

logs:
	@docker-compose logs -f

docker-logs:
	@docker-compose logs -f

# Database operations
db-init:
	@echo "$(CYAN)Initializing database...$(NC)"
	@docker-compose exec postgres psql -U postgres -d finadvisor -f /docker-entrypoint-initdb.d/init.sql
	@echo "$(GREEN)✓ Database initialized$(NC)"

db-logs:
	@docker-compose logs -f postgres

db-connect:
	@echo "$(CYAN)Connecting to PostgreSQL...$(NC)"
	docker-compose exec postgres psql -U postgres -d finadvisor

redis-cli:
	@echo "$(CYAN)Connecting to Redis...$(NC)"
	docker-compose exec redis redis-cli

ollama-pull:
	@echo "$(CYAN)Pulling Llama 3.2 model...$(NC)"
	docker-compose exec ollama ollama pull llama2
	@echo "$(GREEN)✓ Llama model ready$(NC)"

ollama-list:
	@echo "$(CYAN)Available Ollama models...$(NC)"
	docker-compose exec ollama ollama list

health:
	@echo "$(CYAN)Checking service health...$(NC)"
	@echo ""
	@echo "PostgreSQL:"
	@docker-compose exec postgres pg_isready -U postgres || echo "❌ Not ready"
	@echo ""
	@echo "Redis:"
	@docker-compose exec redis redis-cli ping || echo "❌ Not responding"
	@echo ""

# Data seeding
seed:
	@echo "$(CYAN)Loading PostgreSQL + RAG data...$(NC)"
	python3 scripts/seed_rag.py
	@echo "$(GREEN)✓ Data loaded$(NC)"

# Development servers
backend:
	@echo "$(CYAN)Starting backend server...$(NC)"
	@echo "  API: http://localhost:8000"
	python3 backend/lambda_orchestrator/local_server.py

frontend:
	@echo "$(CYAN)Starting Streamlit frontend...$(NC)"
	@echo "  UI: http://localhost:8501"
	API_ENDPOINT=http://localhost:8000 streamlit run frontend/app.py

dev: up seed
	@echo "$(CYAN)Starting development environment...$(NC)"
	@echo ""
	@echo "$(GREEN)Services started:$(NC)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"
	@echo ""
	@echo "$(CYAN)Open another terminal and run:$(NC)"
	@echo "  make backend    (Terminal 1)"
	@echo "  make frontend   (Terminal 2)"

# Testing
test:
	@echo "$(CYAN)Running all tests...$(NC)"
	pytest tests/ -v

test-local:
	@echo "$(CYAN)Running local tests...$(NC)"
	pytest tests/ -v -m "not e2e"

test-coverage:
	@echo "$(CYAN)Running tests with coverage...$(NC)"
	pytest tests/ --cov=backend --cov-report=html
	@echo "$(GREEN)✓ Coverage report: htmlcov/index.html$(NC)"

# Cleaning
clean:
	@echo "$(CYAN)Cleaning up...$(NC)"
	docker-compose down
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# Quick start
quick-start: env install up seed
	@echo ""
	@echo "$(GREEN)✓ Quick start complete!$(NC)"
	@echo ""
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Open Terminal 1: make backend"
	@echo "  2. Open Terminal 2: make frontend"
	@echo "  3. Open browser: http://localhost:8501"

# API health check
health-api:
	@echo "$(CYAN)Checking API health...$(NC)"
	curl -s http://localhost:8000/health | jq . || echo "$(YELLOW)API not responding$(NC)"

# Show environment
status:
	@echo "$(CYAN)Environment Status:$(NC)"
	@echo ""
	@echo "Docker Services:"
	@docker-compose ps
	@echo ""
	@echo "Python Version:"
	@python --version
	@echo ""
	@echo "Make Version:"
	@make --version | head -1

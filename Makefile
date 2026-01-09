.PHONY: help install up down logs seed backend frontend test clean docker-logs db-connect

# Load environment variables from .env file
-include .env
export

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(CYAN)╔════════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║       FinAdvisor - Available Commands      ║$(NC)"
	@echo "$(CYAN)╚════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)🚀 Quick Start (Recommended - All in Docker):$(NC)"
	@echo "  make quick-start ....... Complete setup (build + start + seed)"
	@echo ""
	@echo "$(GREEN)🐳 Docker Mode (Everything in containers):$(NC)"
	@echo "  make docker-up ......... Start all services in Docker"
	@echo "  make docker-down ....... Stop all Docker services"
	@echo "  make docker-restart .... Restart all Docker services"
	@echo "  make docker-build ...... Build Docker images"
	@echo "  make docker-seed ....... Initialize database (in Docker)"
	@echo "  make reseed ............ Reload data from CSV (clear + reload)"
	@echo "  make docker-logs ....... Show all container logs"
	@echo ""
	@echo "$(GREEN)💻 Local Development Mode (Manual setup):$(NC)"
	@echo "  make install ........... Install Python dependencies"
	@echo "  make up ................ Start only infrastructure (PostgreSQL + Redis)"
	@echo "  make backend ........... Start backend server (localhost:8000)"
	@echo "  make frontend .......... Start Streamlit (localhost:8501)"
	@echo "  make seed .............. Load data (requires local Python)"
	@echo ""
	@echo "$(GREEN)🗄️ Database:$(NC)"
	@echo "  make db-logs ........... Show PostgreSQL logs"
	@echo "  make db-connect ........ Connect to database (psql)"
	@echo "  make redis-cli ......... Connect to Redis"
	@echo ""
	@echo "$(GREEN)🧪 Testing:$(NC)"
	@echo "  make test .............. Run all tests"
	@echo "  make test-local ........ Run local tests"
	@echo "  make test-coverage ..... Run tests with coverage"
	@echo ""
	@echo "$(GREEN)📊 Evaluation:$(NC)"
	@echo "  make eval-status ....... Check LangSmith configuration"
	@echo "  make eval-quick ........ Quick evaluation (no LLM judge)"
	@echo "  make eval .............. Full evaluation with all metrics"
	@echo "  make eval-baseline ..... Create baseline snapshot"
	@echo ""
	@echo "$(GREEN)🔍 Verificación:$(NC)"
	@echo "  make verify-redis ...... Verificar Redis (STM conversaciones)"
	@echo "  make verify-postgres ... Verificar PostgreSQL (LTM datos)"
	@echo ""
	@echo "$(GREEN)📋 Logs:$(NC)"
	@echo "  make logs .............. Ver todos los logs"
	@echo "  make backend-logs ...... Solo logs del backend"
	@echo "  make frontend-logs ..... Solo logs del frontend"
	@echo "  make postgres-logs ..... Solo logs de PostgreSQL"
	@echo "  make redis-logs ........ Solo logs de Redis"
	@echo ""
	@echo "$(GREEN)🔧 Utils:$(NC)"
	@echo "  make status ............ Show container status"
	@echo "  make health ............ Check service health"
	@echo "  make clean ............. Stop and remove all containers"
	@echo "  make clean-volumes ..... Stop and remove all volumes (⚠️ deletes data)"
	@echo "  make env ............... Create .env from .env.example"
	@echo "  make help .............. Show this message"
	@echo ""
	@echo "$(GREEN)☁️  AWS Cloud Deployment:$(NC)"
	@echo "  make deploy-aws ........ Deploy to AWS (full stack + seed)"
	@echo "  make update-aws ........ Update AWS deployment"
	@echo "  make destroy-aws ....... Destroy all AWS resources"

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

# Docker services (for local development mode)
up:
	@echo "$(YELLOW)⚠ This starts only infrastructure (PostgreSQL + Redis)$(NC)"
	@echo "$(YELLOW)⚠ For full setup, use: make quick-start$(NC)"
	@echo ""
	@echo "$(CYAN)Starting Docker infrastructure...$(NC)"
	docker-compose up -d postgres redis
	@echo "$(GREEN)✓ Infrastructure running$(NC)"
	@echo ""
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"
	@echo ""
	@echo "$(CYAN)Next: Run 'make backend' and 'make frontend' in separate terminals$(NC)"

down:
	@echo "$(CYAN)Stopping all Docker services...$(NC)"
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

health:
	@echo "$(CYAN)🏥 Checking service health...$(NC)"
	@echo ""
	@echo "$(CYAN)PostgreSQL:$(NC)"
	@docker exec finadvisor-postgres pg_isready -U postgres 2>/dev/null && echo "$(GREEN)✓ Ready$(NC)" || echo "$(RED)✗ Not ready$(NC)"
	@echo ""
	@echo "$(CYAN)Redis:$(NC)"
	@docker exec finadvisor-redis redis-cli ping 2>/dev/null | grep -q PONG && echo "$(GREEN)✓ Ready$(NC)" || echo "$(RED)✗ Not ready$(NC)"
	@echo ""
	@echo "$(CYAN)Backend API:$(NC)"
	@curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "$(GREEN)✓ Ready$(NC)" || echo "$(RED)✗ Not ready$(NC)"
	@echo ""
	@echo "$(CYAN)Frontend:$(NC)"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 2>/dev/null | grep -q 200 && echo "$(GREEN)✓ Ready$(NC)" || echo "$(RED)✗ Not ready$(NC)"

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

# ============================================================
# DOCKER MODE - Everything in containers (Recommended)
# ============================================================

docker-build:
	@echo "$(CYAN)🔨 Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Images built$(NC)"

docker-up:
	@echo "$(CYAN)🚀 Starting all services in Docker...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ All services started!$(NC)"
	@echo ""
	@echo "  Frontend: http://localhost:8501"
	@echo "  Backend:  http://localhost:8000"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"

docker-down:
	@echo "$(CYAN)🛑 Stopping all Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ All services stopped$(NC)"

docker-restart:
	@echo "$(CYAN)🔄 Restarting all Docker services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✓ All services restarted$(NC)"

docker-seed:
	@echo "$(CYAN)🌱 Seeding database from Docker...$(NC)"
	@echo "Waiting for backend to be ready..."
	@sleep 5
	docker exec finadvisor-backend python /app/scripts/seed_database.py
	@echo "$(GREEN)✓ Database seeded!$(NC)"

reseed:
	@echo "$(CYAN)🔄 Reseeding database...$(NC)"
	@echo "$(YELLOW)Clearing existing data...$(NC)"
	@docker exec finadvisor-postgres psql -U postgres -d finadvisor -c "TRUNCATE products CASCADE; TRUNCATE clients CASCADE;" 2>/dev/null || true
	@echo "$(CYAN)Reloading data from CSV...$(NC)"
	@docker exec finadvisor-backend python /app/scripts/seed_database.py
	@echo "$(GREEN)✓ Database reseeded!$(NC)"

refresh:
	@echo "$(CYAN)🔄 Refreshing frontend and backend...$(NC)"
	@docker-compose restart backend frontend
	@echo "$(GREEN)✓ Services refreshed!$(NC)"
	@echo ""
	@echo "$(CYAN)📝 Next steps:$(NC)"
	@echo "  1. Abre/refresca tu navegador: http://localhost:8501"
	@echo "  2. Presiona Ctrl+Shift+R para forzar recarga (o Cmd+Shift+R en Mac)"
	@echo "  3. Haz clic en 'Cargar Modelos' en la barra lateral"
	@echo "  4. Verifica que el proveedor sea 'openai' y modelo 'gpt-4o-mini'"

# Quick start - Docker mode with OpenAI (Everything in containers)
quick-start: docker-build docker-up
	@echo ""
	@echo "$(CYAN)⏳ Waiting for services to start (10 seconds)...$(NC)"
	@sleep 10
	@echo ""
	@$(MAKE) docker-seed
	@echo ""
	@echo "$(GREEN)🎉 FinAdvisor is ready!$(NC)"
	@echo ""
	@echo "$(CYAN)✅ Services running:$(NC)"
	@echo "  Frontend:  http://localhost:8501"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo ""
	@echo "$(YELLOW)⚠️  IMPORTANT: Make sure your OPENAI_API_KEY is set in .env$(NC)"
	@echo ""
	@echo "$(CYAN)Useful commands:$(NC)"
	@echo "  make docker-logs ..... View all logs"
	@echo "  make status .......... Show container status"
	@echo "  make health .......... Check all services"
	@echo "  make docker-down ..... Stop all services"
	@echo ""
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Open http://localhost:8501 in your browser"
	@echo "  2. Select a client (CLI001, CLI002, etc)"
	@echo "  3. Click 'Cargar Perfil'"
	@echo "  4. Ask: 'que productos me puedes recomendar segun mi perfil'"

# ============================================================
# LOCAL DEVELOPMENT MODE - Manual setup (Advanced)
# ============================================================

# Legacy quick start for local development
quick-start-local: env install up seed
	@echo ""
	@echo "$(GREEN)✓ Local development setup complete!$(NC)"
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
	@echo "$(CYAN)📊 FinAdvisor Status:$(NC)"
	@echo ""
	@echo "$(CYAN)Docker Services:$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(CYAN)Environment:$(NC)"
	@echo "  Python: $$(python3 --version 2>/dev/null || echo 'Not installed')"
	@echo "  Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "  Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not installed')"

# ============================================================
# VERIFICATION COMMANDS
# ============================================================

verify-redis:
	@echo "$(CYAN)🔍 Verificando Redis (STM)...$(NC)"
	@echo ""
	@echo "$(CYAN)Redis Status:$(NC)"
	@docker exec finadvisor-redis redis-cli ping || echo "$(RED)✗ Redis not responding$(NC)"
	@echo ""
	@echo "$(CYAN)Conversaciones almacenadas:$(NC)"
	@docker exec finadvisor-redis redis-cli KEYS 'conversation:*' | wc -l | xargs echo "Count:"
	@docker exec finadvisor-redis redis-cli KEYS 'conversation:*' 2>/dev/null || echo "  (ninguna todavía)"
	@echo ""
	@echo "$(GREEN)Tip:$(NC) Usa 'make redis-cli' para explorar interactivamente"

verify-postgres:
	@echo "$(CYAN)🔍 Verificando PostgreSQL (LTM)...$(NC)"
	@echo ""
	@echo "$(CYAN)Productos disponibles:$(NC)"
	@docker exec finadvisor-postgres psql -U postgres -d finadvisor -t -c "SELECT COUNT(*) FROM products;" | xargs echo "  Count:"
	@echo ""
	@echo "$(CYAN)Clientes:$(NC)"
	@docker exec finadvisor-postgres psql -U postgres -d finadvisor -t -c "SELECT COUNT(*) FROM clients;" | xargs echo "  Count:"
	@echo ""
	@echo "$(CYAN)Recomendaciones:$(NC)"
	@docker exec finadvisor-postgres psql -U postgres -d finadvisor -t -c "SELECT COUNT(*) FROM portfolio_recommendations;" | xargs echo "  Count:"
	@echo ""
	@echo "$(GREEN)Tip:$(NC) Usa 'make db-connect' para consultas SQL interactivas"

# ============================================================
# LOGS COMMANDS
# ============================================================

logs:
	@docker-compose logs -f

backend-logs:
	@docker-compose logs -f backend

frontend-logs:
	@docker-compose logs -f frontend

postgres-logs:
	@docker-compose logs -f postgres

redis-logs:
	@docker-compose logs -f redis

# ============================================================
# CLEANUP COMMANDS
# ============================================================

clean-volumes:
	@echo "$(RED)⚠️  WARNING: This will delete all data in PostgreSQL and Redis!$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or wait 5 seconds to continue...$(NC)"
	@sleep 5
	@echo "$(CYAN)Stopping and removing all containers and volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ All volumes cleaned$(NC)"
	@echo ""
	@echo "$(CYAN)To restart:$(NC)"
	@echo "  make docker-up"
	@echo "  make docker-seed"

# ============================================================
<<<<<<< HEAD
# AWS CLOUD DEPLOYMENT
# ============================================================

deploy-aws:
	@echo "$(CYAN)🚀 Deploying FinAdvisor to AWS...$(NC)"
	@echo ""
	@echo "$(YELLOW)This will:${NC}"
	@echo "  1. Validate prerequisites (AWS CLI, CDK, Docker)"
	@echo "  2. Build Docker images"
	@echo "  3. Deploy infrastructure with CDK"
	@echo "  4. Push images to ECR"
	@echo "  5. Seed database"
	@echo "  6. Deploy Streamlit frontend to App Runner"
	@echo ""
	@echo "$(YELLOW)⚠️  Make sure you have:${NC}"
	@echo "  - AWS credentials configured (aws configure)"
	@echo "  - Bedrock access enabled in your region"
	@echo "  - .env file with required variables"
	@echo ""
	@bash scripts/deploy_cloud.sh

destroy-aws:
	@echo "$(RED)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(RED)║  ⚠️  ADVERTENCIA: ESTO ELIMINARÁ TODOS LOS RECURSOS AWS  ║$(NC)"
	@echo "$(RED)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Esto eliminará permanentemente:$(NC)"
	@echo "  • Base de datos RDS PostgreSQL (todos los datos)"
	@echo "  • Cache Redis (memoria de conversaciones)"
	@echo "  • Funciones Lambda"
	@echo "  • API Gateway"
	@echo "  • App Runner (Streamlit frontend)"
	@echo "  • Repositorios ECR con imágenes Docker"
	@echo "  • VPC y recursos de red"
	@echo "  • Logs de CloudWatch"
	@echo "  • Buckets S3"
	@echo ""
	@echo "$(RED)⚠️  Esta acción NO se puede deshacer$(NC)"
	@echo ""
	@echo "$(YELLOW)Presiona Ctrl+C para cancelar, o espera 10 segundos para continuar...$(NC)"
	@sleep 10
	@echo ""
	@echo "$(CYAN)🗑️  Destruyendo infraestructura AWS...$(NC)"
	@cd infra && cdk destroy --force || true
	@echo ""
	@echo "$(GREEN)✓ Recursos AWS eliminados$(NC)"
	@echo ""
	@echo "$(CYAN)💰 Ahorro de costos:$(NC)"
	@echo "  • Ya no se generarán cargos por servicios AWS"
	@echo "  • Los costos anteriores pueden aparecer en la próxima factura"
	@echo ""
	@echo "$(CYAN)Para redesplegar:$(NC)"
	@echo "  make deploy-aws"

update-aws:
	@echo "$(CYAN)🔄 Updating AWS deployment...$(NC)"
	@bash scripts/deploy_cloud.sh
=======
# LANGSMITH EVALUATION
# ============================================================

eval-setup:
	@echo "$(CYAN)Setting up LangSmith evaluation...$(NC)"
	@if [ -z "$${LANGCHAIN_API_KEY}" ]; then \
		echo "$(RED)ERROR: LANGCHAIN_API_KEY not set$(NC)"; \
		echo "$(YELLOW)Get your key from https://smith.langchain.com/settings$(NC)"; \
		echo "$(YELLOW)Add to .env: LANGCHAIN_API_KEY=lsv2_pt_...$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ LangSmith configured$(NC)"
	@echo "  Project: $${LANGCHAIN_PROJECT:-finadvisor-evaluation}"
	@echo "  Dashboard: https://smith.langchain.com"

eval-prereq: eval-setup
	@echo "$(CYAN)Checking evaluation prerequisites...$(NC)"
	@docker exec finadvisor-postgres pg_isready -U postgres > /dev/null 2>&1 || \
		(echo "$(RED)ERROR: PostgreSQL not ready. Run: make docker-up$(NC)" && exit 1)
	@docker exec finadvisor-redis redis-cli ping > /dev/null 2>&1 || \
		(echo "$(RED)ERROR: Redis not ready. Run: make docker-up$(NC)" && exit 1)
	@docker exec finadvisor-postgres psql -U postgres -d finadvisor -t -c \
		"SELECT COUNT(*) FROM products;" 2>/dev/null | grep -q -v '^[[:space:]]*0' || \
		(echo "$(RED)ERROR: Database not seeded. Run: make docker-seed$(NC)" && exit 1)
	@python3 -c "import langsmith" 2>/dev/null || \
		(echo "$(RED)ERROR: langsmith not installed. Run: make install$(NC)" && exit 1)
	@echo "$(GREEN)✓ All prerequisites met$(NC)"

eval-quick: eval-prereq
	@echo "$(CYAN)🚀 Running quick evaluation (no LLM judge)...$(NC)"
	@echo "$(YELLOW)This will take ~5-10 minutes$(NC)"
	@echo ""
	@LANGCHAIN_TRACING_V2=true python3 backend/evaluation/run_evaluation.py \
		--no-llm-judge \
		--experiment-prefix "quick-$(shell date +%H%M%S)"
	@echo ""
	@echo "$(GREEN)✓ Evaluation complete!$(NC)"
	@echo "$(CYAN)View results: https://smith.langchain.com$(NC)"

eval: eval-prereq
	@echo "$(CYAN)🚀 Running full evaluation (with LLM judge)...$(NC)"
	@echo "$(YELLOW)This will take ~10-15 minutes$(NC)"
	@echo ""
	@LANGCHAIN_TRACING_V2=true python3 backend/evaluation/run_evaluation.py \
		--experiment-prefix "dev-$(shell date +%Y%m%d-%H%M%S)"
	@echo ""
	@echo "$(GREEN)✓ Evaluation complete!$(NC)"
	@echo "$(CYAN)View results: https://smith.langchain.com$(NC)"

eval-baseline: eval-prereq
	@echo "$(CYAN)🚀 Running baseline evaluation...$(NC)"
	@echo "$(YELLOW)This creates a baseline for comparison$(NC)"
	@echo ""
	@LANGCHAIN_TRACING_V2=true python3 backend/evaluation/run_evaluation.py \
		--experiment-prefix "baseline-$(shell date +%Y%m%d)"
	@echo ""
	@echo "$(GREEN)✓ Baseline evaluation complete!$(NC)"
	@echo "$(CYAN)View results: https://smith.langchain.com$(NC)"

eval-status:
	@echo "$(CYAN)📊 LangSmith Evaluation Status$(NC)"
	@echo ""
	@if [ -z "$${LANGCHAIN_API_KEY}" ]; then \
		echo "$(RED)Status: NOT CONFIGURED$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Setup steps:$(NC)"; \
		echo "  1. Get API key from https://smith.langchain.com/settings"; \
		echo "  2. Add to .env: LANGCHAIN_API_KEY=lsv2_pt_..."; \
		echo "  3. Run: make eval-setup"; \
	else \
		echo "$(GREEN)Status: CONFIGURED ✓$(NC)"; \
		echo ""; \
		echo "$(CYAN)Configuration:$(NC)"; \
		echo "  API Key: $$LANGCHAIN_API_KEY" | sed 's/\(.\{20\}\).*/\1.../'; \
		echo "  Project: $${LANGCHAIN_PROJECT:-finadvisor-evaluation}"; \
		echo "  Dashboard: https://smith.langchain.com"; \
		echo ""; \
		echo "$(CYAN)Available commands:$(NC)"; \
		echo "  make eval-quick ...... Fast evaluation (~5-10 min)"; \
		echo "  make eval ............ Full evaluation (~10-15 min)"; \
		echo "  make eval-baseline ... Create baseline for comparison"; \
	fi
>>>>>>> main

#!/bin/bash

# FinAdvisor Local Development Setup & Run Script
# Este script configura y ejecuta todo localmente

set -e  # Exit on error

echo "🚀 FinAdvisor Local Setup & Development"
echo "======================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "📁 Repository: $REPO_ROOT"
echo ""

# ============================================================================
# STEP 1: Check Prerequisites
# ============================================================================
echo "${YELLOW}[1/5]${NC} Verificando requisitos previos..."
echo ""

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 no instalado${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} $1 encontrado"
}

check_command python3
check_command pip3
check_command psql
check_command docker

echo ""

# ============================================================================
# STEP 2: Setup Python Environment
# ============================================================================
echo "${YELLOW}[2/5]${NC} Configurando entorno Python..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creando virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activado"

# Install dependencies
echo "Instalando dependencias..."
pip install -q -r backend/requirements.txt
echo -e "${GREEN}✓${NC} Dependencias instaladas"

echo ""

# ============================================================================
# STEP 3: Start PostgreSQL (Docker)
# ============================================================================
echo "${YELLOW}[3/5]${NC} Iniciando PostgreSQL..."
echo ""

# Check if PostgreSQL container is already running
if docker ps | grep -q "postgres"; then
    echo -e "${GREEN}✓${NC} PostgreSQL ya está corriendo"
else
    echo "Iniciando contenedor PostgreSQL..."
    docker run -d \
        --name finadvisor-postgres \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=finadvisor \
        -p 5432:5432 \
        postgres:15 \
        > /dev/null 2>&1

    # Wait for PostgreSQL to be ready
    echo "Esperando a que PostgreSQL esté listo..."
    sleep 3

    # Retry connection
    for i in {1..10}; do
        if psql -h localhost -U postgres -d postgres -c "SELECT 1" > /dev/null 2>&1; then
            break
        fi
        echo "Intento $i/10..."
        sleep 1
    done
fi

echo -e "${GREEN}✓${NC} PostgreSQL disponible en localhost:5432"
echo ""

# ============================================================================
# STEP 4: Seed Database & RAG
# ============================================================================
echo "${YELLOW}[4/5]${NC} Inicializando datos..."
echo ""

# Set environment variables for seed scripts
export DB_HOST=localhost
export DB_NAME=finadvisor
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_PORT=5432

# Run database seed
echo "Ejecutando seed de base de datos..."
python3 scripts/seed_database.py
echo ""

# Run RAG seed
echo "Ejecutando seed de RAG..."
python3 scripts/seed_rag.py
echo ""

# ============================================================================
# STEP 5: Start Streamlit Frontend
# ============================================================================
echo "${YELLOW}[5/5]${NC} Iniciando Streamlit frontend..."
echo ""

# Get API endpoint
API_ENDPOINT="${API_ENDPOINT:-http://localhost:8000}"
echo -e "${GREEN}✓${NC} API Endpoint: $API_ENDPOINT"
echo ""

echo "======================================="
echo -e "${GREEN}✅ Configuración completada!${NC}"
echo "======================================="
echo ""
echo "Acciones disponibles:"
echo ""
echo "1️⃣  Iniciar Backend (Orchestrator Lambda localmente):"
echo "   cd backend"
echo "   uvicorn lambda_orchestrator.handler:app --reload --port 8000"
echo ""
echo "2️⃣  Iniciar Frontend Streamlit (en otra terminal):"
echo "   API_ENDPOINT=http://localhost:8000 streamlit run frontend/app.py"
echo ""
echo "3️⃣  Ejecutar Tests:"
echo "   pytest tests/ -v"
echo ""
echo "📊 Base de datos disponible en:"
echo "   psql -h localhost -U postgres -d finadvisor"
echo ""
echo "🌐 Streamlit abrirá en: http://localhost:8501"
echo ""

# Ask user if they want to start Streamlit now
read -p "¿Deseas iniciar Streamlit ahora? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Iniciando Streamlit..."
    API_ENDPOINT="$API_ENDPOINT" streamlit run frontend/app.py
else
    echo "Setup completado. Ejecuta cuando estés listo:"
    echo "  API_ENDPOINT=http://localhost:8000 streamlit run frontend/app.py"
fi

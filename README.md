# FinAdvisor - Arquitectura de Agente IA Financiero

## 🎯 Propósito

FinAdvisor es un **agente autónomo de recomendación de portafolios** que utiliza:
- Razonamiento agentico con LLM (**OpenAI** en local, **Bedrock/Claude** en AWS)
- **Tool calling nativo** para consultar base de datos y construir portafolios
- Memoria de conversación (STM en Redis) y perfil (LTM en PostgreSQL)
- Base de datos relacional con productos reales
- Validación de restricciones financieras (guardrails)

Genera recomendaciones personalizadas de inversión basadas en el perfil del cliente, monto disponible, horizonte temporal y tolerancia al riesgo.

---

## 🏗️ Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────────────┐
│                    CAPA PRESENTACIÓN                             │
├─────────────────────────────────────────────────────────────────┤
│ Streamlit UI (frontend/app.py)                                  │
│  • Chat con agente IA                                            │
│  • Formulario de recomendación                                   │
│  • Visualización de portafolio                                   │
│  • Selector de modelo (OpenAI/Bedrock/Anthropic)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ JSON/REST
┌────────────────────────▼────────────────────────────────────────┐
│                   CAPA API (ORCHESTRACIÓN)                       │
├─────────────────────────────────────────────────────────────────┤
│ FastAPI Server / Lambda Handler                                 │
│  • POST /chat                                                    │
│  • POST /recommendation                                          │
│  • GET /health, /models                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────┬──────────────┐
    │                    │                │              │
    ▼                    ▼                ▼              ▼
┌──────────┐  ┌────────────────┐  ┌──────────┐  ┌────────────┐
│   RAG    │  │  FinAdvisor    │  │PostgreSQL│  │  Config &  │
│Vector DB │  │    Agent       │  │   BD     │  │   Models   │
├──────────┤  ├────────────────┤  ├──────────┤  ├────────────┤
│ Search   │  │ • Reasoning    │  │ Products │  │ • OpenAI   │
│ (from DB)│  │ • Memory Mgmt  │  │ • Clients│  │ • Bedrock  │
│          │  │ • Tool Call    │  │ • Port.  │  │ • Anthropic│
└──────────┘  │   Execution    │  │ (CSV→DB)│  └────────────┘
              │ • Guardrails   │  │         │
              └────────────────┘  └──────────┘
                     │
         ┌───────────┼──────────┐
         │           │          │
         ▼           ▼          ▼
    ┌────────┐  ┌────────┐  ┌─────────┐
    │ Market │  │ Finance│  │  Redis  │
    │  APIs  │  │ Calc   │  │  Cache  │
    │        │  │        │  │         │
    └────────┘  └────────┘  └─────────┘
```

---

## 🧩 Componentes Principales

### 1. **FinAdvisor Agent** (`backend/agent/fintech_agent.py`)

**Responsabilidad:** Implementar el ciclo agentico de razonamiento.

**Flujo:**
```
User Message
    ↓
1. Recupera contexto de memoria (STM + LTM)
2. Construye mensaje para LLM con system prompt
3. LLM decide si necesita herramientas (tools)
4. Si necesita tools → Ejecuta tool calls
5. Integra resultados de tools en conversación
6. LLM genera respuesta final
    ↓
Response a Usuario
```

**Herramientas Disponibles (Tool Calls):**
- `query_eligible_products`: Busca en BD productos que cumplen criterios
- `get_client_profile`: Obtiene perfil del cliente
- `build_portfolio`: Construye allocaciones diversificadas
- `validate_guardrails`: Valida restricciones de riesgo

---

### 2. **Memory Manager** (`backend/agent/memory_manager.py`)

**STM (Short-Term Memory) - Redis:**
- Almacena últimos 30 mensajes de conversación
- TTL de 1 hora (conversaciones expiran automáticamente)
- Contexto actual de la sesión
- Información extraída (monto, plazo, riesgo)
- Fallback a memoria in-memory si Redis no disponible

**LTM (Long-Term Memory) - PostgreSQL:**
- Perfil del cliente (persistente en BD)
- Historial de recomendaciones (`portfolio_recommendations`)
- Portafolios actuales (`client_portfolios`)
- Preferencias y metas financieras

**Verificación:**
```bash
make verify-redis      # Ver conversaciones en Redis
make verify-postgres   # Ver datos persistentes
```

---

### 3. **RAG Manager** (`backend/agent/rag_manager.py`)

**Propósito:** Búsqueda semántica de productos.

**Flujo:**
```
CSV Files (products_info.csv, product_structure.csv)
    ↓
seed_rag.py
    ↓
Documentos indexados (TF-IDF embeddings)
    ↓
Usuario: "fondo conservador retorno bajo"
    ↓
RAG busca documentos similares
    ↓
Retorna productos ordenados por relevancia
```

---

### 4. **Database Layer** (`backend/mcp_servers/postgres_server.py`)

**Tablas principales:**
```sql
products           -- 8 fondos (PROD001-PROD008)
├── product_id, name, type, annual_return_pct, volatility_pct
├── liquidity_days, min_investment_usd
└── max_allocation_{conservador,moderado,agresivo}_pct

clients            -- Clientes del sistema
├── client_id, profile, investment_horizon, risk_tolerance
└── invested_capital

portfolio_recommendations  -- Historial
├── client_id, recommendation_date, allocations
├── expected_return, expected_risk
└── was_accepted
```

**Fuente de Datos:**
- `data/products_info.csv` → Cargado a BD en seed
- `data/product_structure.csv` → Holdings/composición

---

### 5. **Finance Calculator** (`backend/utils/finance_calc.py`)

**Funciones clave:**
- `diversify_portfolio(amount, products, profile)`: Asigna pesos
- `calculate_portfolio_metrics(allocations)`: Retorno esperado, volatilidad, Sharpe ratio
- `validate_constraints(portfolio, profile)`: Chequea límites

**Algoritmo de Diversificación:**
```
Input: $50,000, [PROD002, PROD006], perfil="moderado"
    ↓
Aplica restricciones de máximo % por tipo
Optimiza para balancear retorno/riesgo
    ↓
Output: 40% PROD002 ($20k) + 60% PROD006 ($30k)
```

---

### 6. **Guardrails** (`backend/utils/guardrails.py`)

**Validaciones:**
```
1. Límites de asignación por perfil
   conservador: max 20% agresivo
   moderado:   max 40% agresivo
   agresivo:   min 20% agresivo

2. Capital mínimo por producto
3. Horizonte temporal mínimo
4. Escalada a humano si: capital alto + novato + agresivo
```

---

### 7. **Modelos (Local vs Cloud)**

**Local Development - OpenAI:**
```
User → Backend
        ↓
OpenAI API (gpt-4o-mini)
        ↓
Tool Calling Nativo
        ↓
Consulta PostgreSQL (productos reales)
        ↓
Respuesta → Backend → Usuario
```
- ✅ **Tool calling nativo** (query_eligible_products, build_portfolio, etc.)
- ⚡ **Rápido**: gpt-4o-mini responde en ~1-2 segundos
- 💰 **Económico**: ~$0.01 por recomendación
- 🔧 **Fácil setup**: Solo necesitas OPENAI_API_KEY

**Cloud Production - AWS Bedrock:**
```
User → API Gateway
        ↓
Lambda Function / ECS
        ↓
AWS Bedrock
        ↓
Claude 3.5 Sonnet/Haiku
        ↓
Tool Calling Nativo
        ↓
RDS PostgreSQL (productos reales)
        ↓
Response → API Gateway → Usuario
```
- ✅ **Tool calling nativo** (misma arquitectura que local)
- 🔒 **Seguro**: Todo en AWS VPC privada
- 📊 **Escalable**: Auto-scaling con demanda
- 💼 **Enterprise**: SLA, compliance, auditoría

---

## 🔄 Flujo End-to-End: Usuario Solicita Recomendación

```
1. USUARIO INGRESA EN STREAMLIT
   "Tengo 50k USD, plazo 24 meses, perfil moderado"

   ↓ Frontend envía a API

2. BACKEND RECIBE POST /recommendation
   {amount: 50000, risk_profile: "moderado", months: 24}

   ↓ FinAdvisor Agent inicia razonamiento

3. AGENT EJECUTA HERRAMIENTAS (Tool Calls)
   • query_eligible_products(amount=50k, profile=moderado)
     → BD retorna [PROD002, PROD006, ...]

   ↓

   • build_portfolio(amount=50k, products=[...])
     → FinanceCalculator calcula allocaciones:
       - PROD002 (moderado): 40% = $20,000
       - PROD006 (moderado): 60% = $30,000
     → Calcula métricas:
       - Expected Return: 6.7%
       - Volatility: 8.6%
       - Sharpe: 0.38

   ↓

   • validate_guardrails(portfolio)
     → Verifica: ¿retorno ≥ objetivo? ¿riesgo dentro limites?
     → Retorna: válido ✓

4. AGENT CONSTRUYE RESPUESTA
   {
     "allocations": [
       {"product": "PROD002", "percentage": 40, "amount": 20000},
       {"product": "PROD006", "percentage": 60, "amount": 30000}
     ],
     "metrics": {
       "expected_return": 0.067,
       "volatility": 0.086,
       "sharpe_ratio": 0.38
     },
     "data_source": "Real product data from database"
   }

   ↓ Backend retorna respuesta

5. FRONTEND VISUALIZA
   ┌─────────────────────────────┐
   │ RECOMENDACIÓN PERSONALIZADA │
   ├─────────────────────────────┤
   │ PROD002: 40% ($20,000)      │
   │ PROD006: 60% ($30,000)      │
   │                              │
   │ Retorno Esperado: 6.7%      │
   │ Volatilidad: 8.6%           │
   │ Sharpe Ratio: 0.38          │
   └─────────────────────────────┘
```

---

## 🔌 Interacciones Entre Componentes

### Scenario 1: Chat en Tiempo Real
```
User: "¿Qué fondos tiene baja volatilidad?"
  ↓
Memory: Extrae contexto
  ↓
RAG: Busca "baja volatilidad"
  → Retorna PROD001 (2.5%), PROD008 (2.0%)
  ↓
Agent: Genera respuesta natural
  ↓
User: Lee recomendación
```

### Scenario 2: Cambio de Modelo
```
User: Selecciona "Bedrock" en Streamlit
  ↓
Config: MODEL_PROVIDER = "bedrock"
  ↓
Backend: Reinicia con cliente Bedrock
  ↓
Próximo chat: Usa Claude en AWS
```

### Scenario 3: Validación de Restricción
```
Agent construye portfolio
  ↓
Portfolio: 70% agresivo, capital=$500k
  ↓
Guardrails: ¿capital_alto AND novato AND agresivo?
  ↓
SI → Escalada a humano (requiere aprobación)
NO → Autoriza y retorna recomendación
```

---

## 📊 Stack Tecnológico

| Capa | Tecnología | Propósito |
|------|-----------|----------|
| **Frontend** | Streamlit | UI interactiva |
| **Backend** | FastAPI | API REST |
| **LLM Local** | OpenAI (gpt-4o-mini) | Reasoning + Tool Calling (dev) |
| **LLM Cloud** | AWS Bedrock (Claude 3.5) | Reasoning + Tool Calling (prod) |
| **Data Store** | PostgreSQL 15 | BD relacional (productos, clientes) |
| **Cache** | Redis 7 | Memoria conversacional (STM) |
| **Infrastructure** | Docker Compose / AWS ECS | Orquestación |

---

## 🚀 Para Empezar

### Desarrollo Local con OpenAI (Recomendado)

**1. Configura tu API Key:**
```bash
# Copia el template
cp .env.example .env

# Edita .env y agrega tu OpenAI API Key
# Obtén tu key en: https://platform.openai.com/api-keys
nano .env  # Agrega: OPENAI_API_KEY=sk-proj-tu-key-aqui
```

**2. Levanta todos los servicios:**
```bash
make quick-start
# Construye imágenes + Inicia PostgreSQL, Redis, Backend, Frontend
# Carga datos de productos desde CSV
# Listo en ~2 minutos ⚡
```

**3. Abre la aplicación:**
```
Frontend: http://localhost:8501
Backend API: http://localhost:8000/docs
```

**Verificar servicios:**
```bash
make status          # Estado de contenedores
make health          # Health check de todos los servicios
make verify-redis    # Ver conversaciones en Redis (STM)
make verify-postgres # Ver productos y clientes en PostgreSQL (LTM)
```

📖 **Guía detallada:** [LEVANTAMIENTO_LOCAL.md](./LEVANTAMIENTO_LOCAL.md)

---

### Producción en AWS con Bedrock

**Prerequisitos:**
- AWS CLI configurado
- Acceso a Bedrock (región us-east-1)
- RDS PostgreSQL y ElastiCache Redis

```bash
# Ver guía completa de deployment
cat AWS_DEPLOYMENT.md

# Deploy rápido con CloudFormation/CDK
cd infra && cdk deploy

# Cargar datos en RDS
DB_HOST=finadvisor-prod.xxx.rds.amazonaws.com \
python3 scripts/seed_database.py
```

📖 **Guía completa:** [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)

---

## 📚 Documentación Adicional

| Documento | Contenido |
|-----------|----------|
| [LEVANTAMIENTO_LOCAL.md](./LEVANTAMIENTO_LOCAL.md) | Guía setup local con OpenAI |
| [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md) | Guía completa deploy AWS + Bedrock |
| [GUIA_PRODUCTOS_CSV.md](./GUIA_PRODUCTOS_CSV.md) | Estructura de datos de productos |
| [FLUJO_DATOS.md](./FLUJO_DATOS.md) | Diagrama de flujo de datos |

---

## 💡 Decisiones Arquitectónicas

**1. RAG para búsqueda de productos**
- Problema: Buscar productos relevantes para cliente
- Solución: Vector DB (TF-IDF) indexa descripciones de CSVs
- Beneficio: Búsqueda semántica sin necesidad de BD especializada

**2. Memoria dual (STM + LTM)**
- Problema: Recordar conversación Y perfil del cliente
- Solución: STM en memoria para sesión, LTM en BD
- Beneficio: Conversaciones naturales + persistencia

**3. Guardrails en validación**
- Problema: Evitar recomendaciones inapropiadas
- Solución: Layer de validación post-portfolio
- Beneficio: Safety checks descentralizado

**4. CSV como data source**
- Problema: Mantener datos de productos
- Solución: CSVs versionadas en repo
- Beneficio: Git-friendly, fácil de auditar

**5. OpenAI en local, Bedrock en cloud**
- Problema: Tool calling nativo + Economía (local) vs Escalabilidad (cloud)
- Solución: Abstracción de modelo configurable con OpenAI/Bedrock/Anthropic
- Beneficio: Mismo código, tool calling nativo, diferentes backends
- Costo dev: ~$0.01 por recomendación (gpt-4o-mini)
- Costo prod: ~$0.05 por recomendación (Claude 3.5 Haiku)

---

## 🎓 Cómo Leer Este Repo

**Arquitecto/Product:** Lee este README
**Developer Backend:** Lee `backend/agent/fintech_agent.py`
**Developer Frontend:** Lee `frontend/app.py`
**DevOps:** Lee `docker-compose.yml`, `infra/`
**Data:** Lee `data/*.csv`, `scripts/seed_rag.py`

---

**Versión:** 2.0.0 | **Status:** ✅ Producción | **LLM:** OpenAI (dev) + Bedrock (prod)

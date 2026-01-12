# 🚀 Levantamiento Local con Docker

Todo corre en Docker. Puedes usar **OpenAI** (recomendado y más barato) o **AWS Bedrock con Claude**.

---

## ✅ Pre-requisitos

- **Docker Desktop** instalado y corriendo
- **API Key de LLM**: OpenAI o AWS Bedrock (ver configuración abajo)
- 4GB RAM disponible
- Puertos libres: 5432 (PostgreSQL), 6379 (Redis), 8000 (Backend), 8501 (Frontend)

---

## 🏃 Quick Start (3 Pasos)

### 1. Crea tu archivo de configuración

```bash
# Crea .env.local.local desde el template
make env

# Esto crea:
# - .env.local.local (para desarrollo local)
# - .env.local.cloud (para despliegue AWS - ignorar por ahora)
```

### 2. Configura tu API Key

Edita `.env.local.local` y elige una opción:

**OPCIÓN A: OpenAI (recomendado para local - más barato)**
```bash
nano .env.local.local

# Configuración:
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-proj-tu-api-key-real-aqui
```

Obtén tu OpenAI API Key en: https://platform.openai.com/api-keys

**OPCIÓN B: AWS Bedrock (con credenciales temporales)**
```bash
nano .env.local.local

# Configuración:
MODEL_PROVIDER=bedrock
MODEL_NAME=anthropic.claude-3-5-sonnet-20241022-v2:0

AWS_ACCESS_KEY_ID=tu-access-key-temporal
AWS_SECRET_ACCESS_KEY=tu-secret-key-temporal
AWS_SESSION_TOKEN=tu-session-token-temporal  # ⚠️ IMPORTANTE para credenciales temporales
AWS_REGION=us-east-1
```

**OPCIÓN C: Anthropic Claude Direct API**
```bash
nano .env.local.local

# Configuración:
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-tu-api-key-aqui
```

### 3. Levanta todos los servicios

```bash
make quick-start
```

Esto ejecuta automáticamente:
1. ✅ Construye imágenes Docker (backend, frontend)
2. ✅ Levanta todos los servicios (postgres, redis, backend, frontend)
3. ✅ Inicializa base de datos con productos y clientes desde CSV
4. ✅ Listo en ~2 minutos ⚡

### 4. Abre la aplicación

**Frontend (Streamlit):**
```
http://localhost:8501
```

**Backend API (Docs):**
```
http://localhost:8000/docs
```

---

## 📦 Servicios Desplegados

| Servicio | Puerto | Propósito |
|----------|--------|-----------|
| **Frontend** | 8501 | Interfaz Streamlit |
| **Backend** | 8000 | API FastAPI + FinAdvisor Agent |
| **PostgreSQL** | 5432 | LTM (productos, clientes, portafolios) |
| **Redis** | 6379 | STM (conversaciones con TTL 1h) |

**Nota:** El agente usa OpenAI API directamente con tool calling nativo. No se requiere ningún servicio de modelo local.

---

## 🧪 Probar el Sistema

### Chat con el Agente

**Opción 1: Streamlit UI** (Recomendado)
```
1. Abre http://localhost:8501
2. Selecciona un cliente (CLI001, CLI002, CLI003, CLI004)
3. Haz clic en "Cargar Perfil"
4. Escribe: "que productos me puedes recomendar segun mi perfil"
5. El agente consultará la BD y recomendará productos reales
```

**Opción 2: API Directa**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "CLI001",
    "message": "que productos me puedes recomendar segun mi perfil"
  }'
```

**Respuesta esperada:**
- El agente llamará a `get_client_profile` (perfil conservador, $25k, 24 meses)
- Luego llamará a `query_eligible_products` para buscar productos compatibles
- Construirá un portafolio con `build_portfolio`
- Validará con `validate_guardrails`
- Responderá con productos reales de la BD (Fondo Conservador A, Bonos del Estado, etc.)

---

## 🛠️ Comandos Disponibles

### Gestión de Servicios

```bash
make help              # Ver todos los comandos disponibles
make docker-up         # Levantar todos los servicios
make docker-down       # Detener todos los servicios
make docker-restart    # Reiniciar todos los servicios
make docker-build      # Reconstruir imágenes Docker
make docker-logs       # Ver logs de todos los servicios
make status            # Ver estado de contenedores
make health            # Health check de todos los servicios
```

### Logs Individuales

```bash
make backend-logs      # Solo logs del backend
make frontend-logs     # Solo logs del frontend
make postgres-logs     # Solo logs de PostgreSQL
make redis-logs        # Solo logs de Redis
```

### Datos y Seed

```bash
make docker-seed       # Inicializar base de datos (primera vez)
make reseed            # Recargar datos desde CSV (borra y recarga)
```

### Verificación de Memorias

#### STM (Redis - Conversaciones)
```bash
make verify-redis      # Ver conversaciones en Redis
make redis-cli         # Conectar a Redis interactivo
```

**Comandos Redis útiles:**
```bash
# Dentro de redis-cli:
KEYS conversation:*                 # Ver todas las conversaciones
LRANGE conversation:CLI001 0 -1     # Ver mensajes de CLI001
TTL conversation:CLI001             # Ver tiempo de vida restante (segundos)
DEL conversation:CLI001             # Borrar conversación
```

#### LTM (PostgreSQL - Productos y Clientes)
```bash
make verify-postgres   # Ver productos y clientes
make db-connect        # Conectar a PostgreSQL interactivo
```

**Consultas SQL útiles:**
```sql
-- Ver todos los productos
SELECT id, name, type, annual_rate FROM products;

-- Ver clientes
SELECT client_id, name, risk_profile, available_amount_usd FROM clients;

-- Ver recomendaciones generadas
SELECT client_id, recommendation_date, allocations
FROM portfolio_recommendations
ORDER BY recommendation_date DESC LIMIT 5;

-- Ver productos de un cliente
SELECT c.name, p.name, cp.invested_amount, cp.purchase_date
FROM client_portfolios cp
JOIN clients c ON cp.client_id = c.client_id
JOIN products p ON cp.product_id = p.id
WHERE c.client_id = 'CLI001';
```

---

## 🔧 Configuración Avanzada

### Cambiar Modelo de OpenAI

Edita `.env.local`:
```bash
# Usar GPT-4o (más potente, más caro)
MODEL_NAME=gpt-4o

# Usar GPT-4 Turbo
MODEL_NAME=gpt-4-turbo

# Volver a gpt-4o-mini (recomendado)
MODEL_NAME=gpt-4o-mini
```

Reinicia:
```bash
make docker-restart
```

### Usar Anthropic Claude Directo

Edita `.env.local`:
```bash
# Comenta OpenAI
# OPENAI_API_KEY=sk-proj-...

# Descomentar y configurar Anthropic
ANTHROPIC_API_KEY=sk-ant-tu-api-key-aqui
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022
```

Reinicia:
```bash
make docker-restart
```

### Configurar Timeouts

Si ves errores de timeout, aumenta el límite en `.env.local`:
```bash
API_TIMEOUT=60  # De 30 a 60 segundos
```

### Habilitar Trazabilidad con LangSmith

LangSmith te permite monitorear y debuggear las conversaciones del agente en tiempo real.

**Beneficios:**
- 📊 Ver todas las llamadas al LLM (input/output)
- ⏱️ Medir tiempos de respuesta
- 💰 Rastrear tokens consumidos
- 🐛 Debuggear errores y excepciones
- 🔍 Analizar cadenas de razonamiento del agente

**Configuración:**

1. Crea una cuenta en https://smith.langchain.com

2. Obtén tu API key en: https://smith.langchain.com/settings

3. Agrega a `.env.local`:
```bash
LANGCHAIN_API_KEY=lsv2_pt_tu-api-key-aqui
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=finadvisor-local
```

4. Reinicia los servicios:
```bash
make docker-restart
```

5. Abre el dashboard: https://smith.langchain.com

6. Realiza algunas conversaciones y verás las trazas en tiempo real

**Comandos útiles:**
```bash
# Verificar configuración de LangSmith
make eval-status

# Correr evaluación rápida (opcional)
make eval-quick
```

---

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY environment variable not set"

**Causa:** No configuraste tu API key en `.env.local`

**Solución:**
```bash
# Edita .env.local y agrega tu key
nano .env.local
# Cambia: OPENAI_API_KEY=sk-proj-XXXXXXXX
# Por:    OPENAI_API_KEY=sk-proj-tu-key-real

# Reinicia
make docker-restart
```

### Error: "Ports already in use"

**Causa:** Ya tienes algo corriendo en los puertos necesarios

**Solución:**
```bash
# Ver qué está usando los puertos
lsof -i :8000  # Backend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8501  # Frontend

# Detener contenedores anteriores
make docker-down

# O matar proceso específico
kill -9 <PID>
```

### Backend no inicia / Error 500

**Causa:** Imagen Docker desactualizada o cambios en código

**Solución:**
```bash
# Reconstruir imagen
make docker-build

# Reiniciar servicios
make docker-up

# Ver logs para más detalles
make backend-logs
```

### Frontend muestra "Connection Error"

**Causa:** Backend no está listo o no responde

**Solución:**
```bash
# Verificar estado
make health

# Ver logs del backend
make backend-logs

# Verificar que backend responde
curl http://localhost:8000/health
```

### PostgreSQL vacío / No hay productos

**Causa:** No se ejecutó el seed inicial

**Solución:**
```bash
# Ejecutar seed manualmente
make docker-seed

# Verificar que se cargaron datos
make verify-postgres

# Si no funciona, recargar
make reseed
```

### Redis no guarda conversaciones

**Causa:** Redis no está corriendo o hay problema de conexión

**Solución:**
```bash
# Verificar Redis
make verify-redis

# Ver logs de Redis
make redis-logs

# Reiniciar Redis
docker-compose restart redis
```

---

## 🧹 Limpieza

### Detener todo
```bash
make docker-down
```

### Borrar datos (empieza de cero)
```bash
make clean-volumes
# ⚠️ Esto borra TODO: PostgreSQL data, Redis data

# Después de esto, vuelve a inicializar:
make quick-start
```

### Limpiar imágenes viejas
```bash
# Ver imágenes Docker
docker images | grep finadvisor

# Borrar imágenes viejas
docker rmi utec-ia-grupo-5-backend:latest
docker rmi utec-ia-grupo-5-frontend:latest

# Reconstruir
make docker-build
```

---

## 📊 Costos de OpenAI

Con **gpt-4o-mini**:
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens

**Estimado por conversación:**
- Chat simple: ~1,000 tokens = $0.001 (0.1 centavo)
- Recomendación de portafolio: ~5,000 tokens = $0.01 (1 centavo)

**100 recomendaciones/día = ~$1/día = $30/mes**

Muy económico para desarrollo. Para producción, considera usar Bedrock con Claude.

---

## 🚀 Siguiente Paso: Deploy a AWS

Una vez que hayas probado localmente, puedes deployar a AWS con Bedrock:

```bash
# Ver guía completa
cat AWS_DEPLOYMENT.md

# Deploy rápido
cd infra && cdk deploy
```

---

## 🎓 Arquitectura del Agente

```
User Message
    ↓
FinAdvisor Agent (con OpenAI gpt-4o-mini)
    ↓
1. Llama tool: get_client_profile(CLI001)
   → PostgreSQL: Retorna {risk: "conservador", amount: 25000, months: 24}
    ↓
2. Llama tool: query_eligible_products(conservador, 25000, 24)
   → PostgreSQL: Retorna [PROD001, PROD002, PROD003]
    ↓
3. Llama tool: build_portfolio(products, amount=25000)
   → FinanceCalculator: Retorna {
       allocations: [
         {product: "Fondo Conservador A", percentage: 60, amount: 15000},
         {product: "Bonos del Estado 5Y", percentage: 40, amount: 10000}
       ],
       metrics: {expected_return: 4.2%, volatility: 3.5%}
     }
    ↓
4. Llama tool: validate_guardrails(portfolio, profile)
   → Guardrails: ✓ Válido (0% agresivo, dentro de límites)
    ↓
5. Genera respuesta natural en español
    ↓
User recibe recomendación con productos reales
```

**Tool calling nativo** = El LLM decide cuándo y cómo llamar cada función automáticamente.

---

**Versión:** 2.0.0 | **LLM:** OpenAI gpt-4o-mini | **Tool Calling:** ✅ Nativo

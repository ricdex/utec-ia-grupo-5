# Backend - Estructura del Código

## 📁 Organización del Código

La estructura del backend está organizada para **maximizar la reutilización de código** entre entornos local y cloud, minimizando el acoplamiento específico de cada ambiente.

```
backend/
├── agent/               ✅ COMPARTIDO (1602 líneas)
│   ├── fintech_agent.py        # Agente principal IA
│   ├── memory_manager.py       # Gestión de memoria (LTM/STM)
│   └── rag_manager.py          # RAG para búsqueda de productos
│
├── utils/               ✅ COMPARTIDO (1414 líneas)
│   ├── config.py               # Configuración centralizada
│   ├── finance_calc.py         # Cálculos financieros
│   ├── guardrails.py           # Reglas de cumplimiento
│   ├── guardrails_provider.py  # Factory para guardrails (local/bedrock)
│   └── llm_client.py           # Factory para LLM (openai/bedrock/anthropic)
│
├── mcp_servers/         ✅ COMPARTIDO (864 líneas)
│   ├── postgres_server.py      # Servidor MCP para PostgreSQL
│   └── market_api_server.py    # Servidor MCP para datos de mercado
│
├── orchestrator/        ✅ COMPARTIDO + WRAPPERS (561 líneas)
│   ├── core.py                 # Lógica compartida (FinAdvisorOrchestrator)
│   ├── cloud.py                # ☁️  Entry point AWS Lambda
│   └── local.py                # 💻 Entry point FastAPI (local)
│
└── evaluation/          ⚠️  SOLO DESARROLLO (1160 líneas)
    ├── evaluators.py           # 6 evaluadores de calidad
    ├── llm_judge.py            # LLM-as-judge para explainability
    └── run_evaluation.py       # Script de evaluación batch
```

---

## 🎯 Principios de Diseño

### 1. **Código Compartido (>95%)**

Todo el código de negocio está en carpetas compartidas:
- `agent/` - Lógica del agente IA
- `utils/` - Utilidades y abstracciones
- `mcp_servers/` - Servidores MCP
- `orchestrator/core.py` - Orquestación compartida

**Ventajas:**
- ✅ Cambios en un solo lugar
- ✅ Tests únicos para ambos ambientes
- ✅ Sin duplicación de lógica

### 2. **Código Específico por Ambiente (<5%)**

Solo los entry points son específicos:

**Cloud (`orchestrator/cloud.py`):**
```python
def lambda_handler(event, context):
    """AWS Lambda entry point"""
    orchestrator = FinAdvisorOrchestrator()  # ← Compartido
    return orchestrator.handle_chat(event)
```

**Local (`orchestrator/local.py`):**
```python
@app.post("/chat")
async def chat(request: Request):
    """FastAPI endpoint"""
    event = create_lambda_event(request)
    return lambda_handler(event, None)  # ← Reutiliza cloud.py!
```

**Ventajas:**
- ✅ Mismo comportamiento en local y cloud
- ✅ Tests de cloud funcionan para local
- ✅ Fácil debugging (local = cloud)

### 3. **Factory Pattern para Providers**

Uso de factories para abstraer diferencias de ambiente:

**LLM Provider:**
```python
# config.py detecta automáticamente el ambiente
llm_client = LLMClientFactory.create_from_config(config)

# En local: usa OpenAI
# En cloud: usa AWS Bedrock
```

**Guardrails Provider:**
```python
guardrails = GuardrailsProviderFactory.create_from_config(config)

# En local: validación Python
# En cloud: AWS Bedrock Guardrails API
```

---

## 🚀 Flujos de Ejecución

### Local Development

```
Usuario → FastAPI (local.py)
         → lambda_handler() (cloud.py)
         → FinAdvisorOrchestrator (core.py)
         → FinAdvisor (agent/)
         → Tools (mcp_servers/)
```

### Cloud Production

```
Usuario → API Gateway → Lambda (cloud.py)
         → FinAdvisorOrchestrator (core.py)
         → FinAdvisor (agent/)
         → Tools (mcp_servers/)
```

**Nota:** Ambos flujos usan el mismo código core!

---

## 📊 Distribución de Código

| Componente | Líneas | Tipo | Usado en |
|-----------|--------|------|----------|
| `agent/` | 1602 | Compartido | Local + Cloud |
| `utils/` | 1414 | Compartido | Local + Cloud |
| `mcp_servers/` | 864 | Compartido | Local + Cloud |
| `orchestrator/core.py` | 385 | Compartido | Local + Cloud |
| `orchestrator/cloud.py` | 97 | Cloud-specific | Solo Cloud |
| `orchestrator/local.py` | 176 | Local-specific | Solo Local |
| `evaluation/` | 1160 | Development | Testing |
| **Total** | **5752** | | |

**Reutilización:** 95% compartido, 5% específico

---

## 🔧 Cómo Extender

### Agregar Nuevo Endpoint

1. Agregar método en `orchestrator/core.py`:
   ```python
   class FinAdvisorOrchestrator:
       def handle_new_feature(self, event):
           # Lógica compartida aquí
           return {"statusCode": 200, "body": "..."}
   ```

2. Agregar ruta en `orchestrator/cloud.py`:
   ```python
   def lambda_handler(event, context):
       if path == "/new-feature":
           return orchestrator.handle_new_feature(event)
   ```

3. Agregar endpoint en `orchestrator/local.py`:
   ```python
   @app.post("/new-feature")
   async def new_feature(request: Request):
       event = create_lambda_event(request)
       return lambda_handler(event, None)
   ```

### Agregar Nuevo Provider

1. Crear provider en `utils/`:
   ```python
   class NewProvider(BaseProvider):
       def execute(self, input):
           # Implementación
   ```

2. Registrar en factory:
   ```python
   class ProviderFactory:
       @staticmethod
       def create(provider_type):
           if provider_type == "new":
               return NewProvider()
   ```

3. Configurar en `.env` o env vars:
   ```bash
   PROVIDER_TYPE=new
   ```

---

## ✅ Buenas Prácticas

### DO ✅

- Colocar lógica de negocio en `agent/` o `utils/`
- Usar factories para abstracciones específicas de ambiente
- Mantener entry points mínimos (solo routing)
- Escribir tests contra `core.py` (compartido)

### DON'T ❌

- Poner lógica de negocio en `cloud.py` o `local.py`
- Hardcodear checks de ambiente (`if is_lambda:`)
- Duplicar código entre local y cloud
- Importar módulos específicos de AWS en código compartido

---

## 🧪 Testing

### Tests de Integración

**Local:**
```bash
# Inicia servidor local
python backend/orchestrator/local.py

# Ejecuta tests
pytest tests/ -v
```

**Cloud (simulated):**
```bash
# Tests invocan lambda_handler directamente
pytest tests/test_agent_e2e.py -v
```

### Evaluación con LangSmith

```bash
# Evaluación batch
python backend/evaluation/run_evaluation.py

# Con tracing en tiempo real
LANGCHAIN_TRACING_V2=true python backend/orchestrator/local.py
```

---

## 📝 Migración desde `lambda_orchestrator/`

**Antes:**
```
lambda_orchestrator/
├── handler.py          # Mezclaba core + lambda handler
└── local_server.py     # Duplicaba lógica
```

**Ahora:**
```
orchestrator/
├── core.py      # Lógica compartida extraída
├── cloud.py     # Solo lambda_handler()
└── local.py     # Solo FastAPI wrapper
```

**Beneficios:**
- ✅ Separación clara de responsabilidades
- ✅ Nombres más descriptivos
- ✅ Código reutilizable al 95%
- ✅ Fácil de mantener y extender

---

## 🔗 Referencias

- [Agent Architecture](../docs/ARQUITECTURA.md)
- [Deployment Guide](../DESPLIEGUE_AWS.md)
- [Evaluation System](./evaluation/README.md)

# Inicio Rápido - Evaluación LangSmith

## Setup en 5 Minutos

### 1. Instalar Dependencias
```bash
pip install langsmith langchain-anthropic
```

### 2. Configurar LangSmith
```bash
# Obtener API key de https://smith.langchain.com/settings
export LANGCHAIN_API_KEY="lsv2_pt_..."
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_PROJECT="finadvisor-evaluation"
```

### 3. Verificar Servicios
```bash
# Asegurar que PostgreSQL y servicios estén corriendo
make up
make seed
make health
```

### 4. Ejecutar Primera Evaluación

```bash
# Desde la raíz del proyecto (usa dataset.json por defecto)
python backend/evaluation/run_evaluation.py \
  --experiment-prefix "baseline-v1"
```

### 5. Ver Resultados
Ir a https://smith.langchain.com y seleccionar tu proyecto

## Comandos Útiles

```bash
# Evaluación básica (usa dataset.json por defecto)
python backend/evaluation/run_evaluation.py

# Evaluación con dataset existente en LangSmith
python backend/evaluation/run_evaluation.py \
  --dataset-name "finadvisor-eval-v1"

# Crear/actualizar dataset desde archivo local
python backend/evaluation/run_evaluation.py \
  --dataset-file backend/evaluation/dataset.json \
  --dataset-name "mi-dataset-custom"

# Evaluación con nombre de experimento específico
python backend/evaluation/run_evaluation.py \
  --experiment-prefix "v2-with-new-prompts"
```

## Estructura de Archivos

```
backend/evaluation/
├── __init__.py              # Exports de evaluadores
├── evaluators.py            # 6 evaluadores implementados
├── dataset.json             # Dataset completo (30 casos)
├── run_evaluation.py        # Script principal
├── README.md                # Documentación completa
└── QUICK_START.md           # Esta guía
```

## Las 6 Métricas

| Métrica | Tipo | Crítica | Descripción |
|---------|------|---------|-------------|
| hard_goals_compliance | Binary | ✅ | Cumple restricciones duras |
| no_guarantees_and_has_disclaimer | Binary | ✅ | Sin garantías + disclaimer |
| clarification_trigger | Binary | ✅ | Pide aclaraciones |
| grounded_recommendation | 0-1 | ✅ | Productos reales del catálogo |
| explainability_score | 1-5 | ⚠️ | Calidad de explicación |
| sequential_orchestration | 0-1 | ✅ | Orden correcto de ejecución |

## Ejemplo de Dataset

```json
{
  "id": "valid_001",
  "inputs": {
    "client_id": "TEST_001",
    "message": "Tengo $50,000 USD para invertir a 24 meses. Perfil moderado."
  },
  "outputs": {
    "needs_clarification": false,
    "should_recommend": true,
    "hard_goals": {
      "max_risk_level": 0.15,
      "min_horizon_months": 24
    },
    "valid_catalog_ids": ["PROD001", "PROD002", ...]
  }
}
```

## Troubleshooting Rápido

**Error: "LANGCHAIN_API_KEY not set"**
```bash
export LANGCHAIN_API_KEY="tu-key-aqui"
```

**Error: "Dataset not found"**
```bash
# Crear dataset primero (usa dataset.json por defecto)
python backend/evaluation/run_evaluation.py
```

**Error: Agent fails durante evaluación**
```bash
# Verificar servicios
make up
make seed
make health

# Verificar .env
cat .env
```

**Error: "ModuleNotFoundError: langsmith"**
```bash
pip install langsmith langchain-anthropic
```

## LLM-as-Judge (Opcional pero Recomendado)

El sistema usa **Claude** para evaluar calidad de respuestas automáticamente:

```bash
# Asegurar que ANTHROPIC_API_KEY está en .env
# Ejecutar evaluación (usa LLM judge por defecto)
python backend/evaluation/run_evaluation.py

# Ver: ✓ Using LLM-as-judge for explainability (Claude)
```

**Deshabilitar si no tienes API key:**
```bash
python backend/evaluation/run_evaluation.py --no-llm-judge
```

Ver [`LLM_JUDGE.md`](./LLM_JUDGE.md) para detalles.

## Próximos Pasos

1. **Expandir Dataset**: Agregar más casos a `dataset.json`
2. **Custom Evaluators**: Crear evaluadores específicos en `evaluators.py`
3. **Tunear LLM Judge**: Personalizar prompt en `llm_judge.py`
4. **CI/CD**: Integrar evaluación en pipeline (ver README.md)
5. **Monitoreo**: Configurar alertas para métricas críticas

## Links Útiles

- 📚 [README Completo](./README.md)
- 🔧 [Documentación LangSmith](https://docs.smith.langchain.com/)
- 🏗️ [Arquitectura FinAdvisor](../../README.md)
- 🎯 [CLAUDE.md](../../CLAUDE.md)

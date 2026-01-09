# Evaluación LangSmith para FinAdvisor

Sistema completo de evaluación para el agente IA FinAdvisor usando LangSmith.

## Métricas Implementadas

### 1. Hard Goals Compliance (Binaria: Sí/No)
**Crítica**: Determina si la recomendación es válida
- Verifica nivel de riesgo ≤ tolerancia del cliente
- Chequea horizonte ≥ mínimo requerido
- Valida monto ≥ inversión mínima
- Asegura cumplimiento de políticas internas

### 2. No Guarantees & Disclaimer Presence (Binaria: Sí/No)
**Crítica**: Cobertura ética/legal
- Sin lenguaje de garantía absoluta ("garantizado", "sin riesgo", "100% seguro")
- Disclaimer educativo presente ("educativo", "no es asesoría")

### 3. Clarification Trigger Accuracy (Binaria: Sí/No)
**Crítica**: Previene supuestos incorrectos
- El agente pide aclaraciones cuando faltan datos
- No hace recomendaciones sin información suficiente

### 4. Grounded Recommendation (Puntaje 0-1)
**Crítica**: Previene alucinaciones
- Todos los productos existen en el catálogo real
- Atributos de productos coinciden con la base de datos

### 5. Explainability Score (Puntaje 1-5, LLM-as-judge)
Métrica de calidad de claridad de respuesta:
- TL;DR/resumen claro
- Razonamiento explicado (trade-offs de riesgo/retorno)
- Lenguaje educativo
- Disclaimers apropiados
- Alineación con metas

### 6. Sequential Orchestration Correctness (Puntaje 0-1)
**Crítica**: Asegura pipeline correcto del agente
- Verifica orden correcto de ejecución de herramientas
- Valida que el agente sigue el flujo diseñado

## Inicio Rápido

### 1. Instalar Dependencias

```bash
pip install langsmith langchain-anthropic
```

### 2. Configurar LangSmith

```bash
# Obtener API key de https://smith.langchain.com/settings
export LANGCHAIN_API_KEY="tu-api-key-aqui"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_PROJECT="finadvisor-evaluation"
```

### 3. Ejecutar Evaluación

```bash
# Desde la raíz del proyecto
python backend/evaluation/run_evaluation.py \
  --experiment-prefix "baseline-v1"

# O especificando el dataset explícitamente
python backend/evaluation/run_evaluation.py \
  --dataset-file backend/evaluation/dataset.json \
  --experiment-prefix "baseline-v1"
```

## Flujo de Trabajo

### Opción 1: Subir Dataset por UI (Recomendado Primera Vez)

1. Ir a https://smith.langchain.com
2. Navegar a "Datasets"
3. Click en "New Dataset"
4. Subir `sample_dataset.json`
5. Ejecutar evaluación:
   ```bash
   python backend/evaluation/run_evaluation.py --dataset-name "nombre-tu-dataset"
   ```

### Opción 2: Subir Dataset Programáticamente

```bash
# Esto crea/actualiza el dataset en LangSmith
python backend/evaluation/run_evaluation.py \
  --dataset-file backend/evaluation/dataset.json \
  --dataset-name "finadvisor-eval-v1"
```

### Opción 3: Usar Dataset Existente

```bash
# Si el dataset ya existe en LangSmith
python backend/evaluation/run_evaluation.py \
  --dataset-name "finadvisor-eval-v1"
```

## Formato del Dataset

Cada caso de prueba tiene:

```json
{
  "id": "id_unico_test",
  "inputs": {
    "client_id": "TEST_001",
    "message": "Mensaje del usuario aquí"
  },
  "outputs": {
    "needs_clarification": false,
    "should_recommend": true,
    "hard_goals": {
      "max_risk_level": 0.15,
      "min_horizon_months": 24
    },
    "valid_catalog_ids": ["PROD001", "PROD002", ...],
    "expected_profile": "moderado"
  }
}
```

## Interpretar Resultados

Después de ejecutar la evaluación, ver resultados en https://smith.langchain.com

**Fallas Críticas** (deben ser 100%):
- hard_goals_compliance
- no_guarantees_and_has_disclaimer
- clarification_trigger
- grounded_recommendation
- sequential_orchestration_correctness

**Métrica de Calidad** (objetivo >4.0/5.0):
- explainability_score

## Extender los Evaluadores

### Agregar Nuevo Evaluador

1. Crear función en `evaluators.py`:
```python
def mi_evaluador_custom(run, example) -> Dict[str, Any]:
    """
    Tu lógica de evaluación aquí
    """
    return {
        "key": "mi_metrica_custom",
        "score": 1.0,  # 0-1 o valores discretos
        "comment": "Contexto adicional"
    }
```

2. Agregar a `run_evaluation.py`:
```python
from evaluation.evaluators import mi_evaluador_custom

evaluators = [
    # ... evaluadores existentes
    mi_evaluador_custom
]
```

### Agregar Casos de Prueba al Dataset

Editar `dataset.json`:

```json
{
  "id": "nuevo_caso_prueba",
  "inputs": {
    "client_id": "TEST_XXX",
    "message": "Escenario de prueba"
  },
  "outputs": {
    "expected_behavior": "descripción"
  }
}
```

## LLM-as-Judge para Explainability

El sistema incluye un **LLM-as-judge** que usa Claude para evaluar la calidad de respuestas.

### Uso Automático (Por Defecto)

```bash
# Usa LLM judge si ANTHROPIC_API_KEY está configurada
python backend/evaluation/run_evaluation.py
```

### Deshabilitar LLM Judge

```bash
# Usa scoring basado en reglas
python backend/evaluation/run_evaluation.py --no-llm-judge
```

### Requisitos

- `langchain-anthropic>=1.3.0` (ya en requirements.txt)
- `ANTHROPIC_API_KEY` en `.env`

### Detalles

Ver documentación completa en [`LLM_JUDGE.md`](./LLM_JUDGE.md)

## Solución de Problemas

### "Dataset not found"
Crear dataset primero:
```bash
python backend/evaluation/run_evaluation.py \
  --dataset-file backend/evaluation/dataset.json
```

### "LANGCHAIN_API_KEY not set"
```bash
export LANGCHAIN_API_KEY="lsv2_..."
```

Obtener key de https://smith.langchain.com/settings

### "ModuleNotFoundError: No module named 'langsmith'"
```bash
pip install langsmith langchain-anthropic
```

### Errores del agente durante evaluación
Verificar que:
- PostgreSQL está corriendo (`make up`)
- Base de datos está seeded (`make seed`)
- Archivo `.env` está configurado

## Integración CI/CD

Agregar a GitHub Actions:

```yaml
name: Evaluation

on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install langsmith
      - name: Run evaluation
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          LANGCHAIN_PROJECT: "finadvisor-ci"
        run: |
          python backend/evaluation/run_evaluation.py
```

## Archivos

- `evaluators.py`: Las 6 funciones evaluadoras
- `llm_judge.py`: LLM-as-judge para explainability (Claude)
- `dataset.json`: Dataset completo (30 casos de prueba)
- `run_evaluation.py`: Script principal de ejecución
- `README.md`: Este archivo
- `QUICK_START.md`: Guía rápida de inicio
- `LLM_JUDGE.md`: Documentación del LLM judge

## Referencias

- [Documentación LangSmith](https://docs.smith.langchain.com/)
- [Guía de Evaluación LangSmith](https://docs.smith.langchain.com/evaluation)
- [Arquitectura FinAdvisor](../../README.md)

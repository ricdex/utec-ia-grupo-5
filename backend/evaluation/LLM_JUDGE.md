# LLM-as-Judge para Explainability

## ¿Qué es?

El **LLM-as-judge** usa Claude (Haiku) para evaluar la calidad de las respuestas del agente de forma más sofisticada que reglas simples.

## Ventajas vs Rule-Based

| Aspecto | Rule-Based | LLM Judge |
|---------|------------|-----------|
| **Precisión** | Básica (keywords) | Alta (comprensión semántica) |
| **Costo** | $0 | ~$0.001 por evaluación |
| **Velocidad** | Instantánea | ~1-2 segundos |
| **Contexto** | No entiende contexto | Entiende matices |
| **Setup** | Ninguno | Requiere API key |

## Requisitos

### 1. Dependencia

Ya instalada en `requirements.txt`:
```bash
langchain-anthropic>=1.3.0
```

### 2. API Key

Necesitas tu Anthropic API key en `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### 3. (Opcional) LangSmith API Key

Para trazabilidad completa:
```bash
LANGCHAIN_API_KEY=lsv2_pt_your-langsmith-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=finadvisor-evaluation
```

## Uso

### Automático (Por Defecto)

El LLM judge se usa **automáticamente** si está disponible:

```bash
# Usa LLM judge si ANTHROPIC_API_KEY está configurada
python backend/evaluation/run_evaluation.py
```

Output:
```
✓ Using LLM-as-judge for explainability (Claude)
```

### Deshabilitar LLM Judge

Si quieres usar solo rule-based:

```bash
python backend/evaluation/run_evaluation.py --no-llm-judge
```

Output:
```
ℹ Using rule-based explainability scoring
```

### Forzar LLM Judge

```bash
python backend/evaluation/run_evaluation.py --use-llm-judge
```

## Cómo Funciona

### 1. Prompt de Evaluación

El judge recibe:
- **Entrada del usuario**: Mensaje original
- **Respuesta del agente**: Lo que generó el agente
- **Criterios de evaluación**: Escala 1-5

### 2. Criterios (Escala 1-5)

#### 5 - Excelente
- TL;DR claro al inicio
- Razonamiento detallado (riesgo/retorno/horizonte)
- Lenguaje educativo
- Disclaimer apropiado
- Alineación perfecta con metas

#### 4 - Muy Bueno
- Resumen presente
- Buen razonamiento
- Terminología correcta
- Disclaimer presente

#### 3 - Aceptable
- Resumen poco claro
- Razonamiento básico
- Algunos términos financieros
- Disclaimer débil

#### 2 - Deficiente
- Sin resumen
- Razonamiento confuso
- Disclaimer inadecuado

#### 1 - Inaceptable
- Sin estructura
- Sin educación financiera
- Sin disclaimers

### 3. Salida

```json
{
  "key": "explainability_score_llm",
  "score": 0.8,  // Normalizado 0-1 (4/5)
  "comment": "Claude judge: 4/5"
}
```

## Modelo Usado

**Claude 3.5 Haiku** (`claude-3-5-haiku-20241022`)

**¿Por qué Haiku?**
- ✅ **Rápido**: ~1 segundo por evaluación
- ✅ **Económico**: ~$0.001 por evaluación
- ✅ **Preciso**: Suficiente para evaluar calidad
- ✅ **Determinístico**: Temperature=0 para consistencia

## Costos Estimados

Para el dataset completo (30 casos):

| Modelo | Costo/eval | Total 30 casos |
|--------|-----------|----------------|
| Claude Haiku | $0.001 | ~$0.03 |
| GPT-4o-mini | $0.0001 | ~$0.003 |
| Claude Sonnet | $0.003 | ~$0.09 |

## Personalizar Prompt

Puedes modificar el prompt en `backend/evaluation/llm_judge.py`:

```python
JUDGE_PROMPT = """Tu prompt personalizado aquí...

Criterios:
1. ...
2. ...

CALIFICACIÓN:"""
```

## Fallback Automático

El sistema tiene fallback inteligente:

```
¿ANTHROPIC_API_KEY existe?
  └─ NO → usa rule-based
  └─ SÍ →
      └─ ¿langchain-anthropic instalado?
          └─ NO → usa rule-based
          └─ SÍ → usa LLM judge
```

## Comparación en Resultados

En LangSmith verás ambas métricas:

| Métrica | Tipo | Valor |
|---------|------|-------|
| `explainability_score` | Rule-based | 0.6 (3/5) |
| `explainability_score_llm` | LLM judge | 0.8 (4/5) |

El LLM judge suele ser más preciso en casos complejos.

## Debugging

Si el LLM judge falla:

```bash
# Ver logs
python backend/evaluation/run_evaluation.py

# Salida esperada:
⚠ LLM judge unavailable, using rule-based explainability

# Revisar:
1. ¿Está ANTHROPIC_API_KEY en .env?
2. ¿langchain-anthropic instalado?
3. ¿Límites de API rate alcanzados?
```

## Cambiar a GPT (OpenAI)

Si prefieres OpenAI en lugar de Anthropic:

```python
# En llm_judge.py, reemplazar:
from langchain_openai import ChatOpenAI

judge_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)
```

Y en `.env`:
```bash
OPENAI_API_KEY=sk-your-openai-key
```

## Próximos Pasos

1. **Tunear el prompt** para casos específicos
2. **A/B testing** entre rule-based y LLM judge
3. **Métricas adicionales** (coherencia, tone, etc.)
4. **Multi-judge** (varios LLMs votando)

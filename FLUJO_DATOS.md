# 🔄 Data Flow - FinAdvisor

Documento que explica cómo los datos fluyen desde los archivos CSV hasta las recomendaciones finales.

---

## 📊 Flujo Completo de Datos

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHIVOS CSV (FUENTE)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  data/products_info.csv           data/product_structure.csv    │
│  ├─ product_id                    ├─ product_id                 │
│  ├─ product_name                  ├─ asset_type                 │
│  ├─ annual_return_pct             ├─ ticker                     │
│  ├─ annual_volatility_pct         ├─ company_name               │
│  ├─ liquidity_days                ├─ allocation_percentage      │
│  └─ description                   └─ sector                     │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ↓ (seed_rag.py)

┌─────────────────────────────────────────────────────────────────┐
│               RAG (VECTOR DATABASE) - INDEXING                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Document 1 (Products Info)                                     │
│  ├─ product_id: PROD001                                         │
│  ├─ product_name: Fondo Conservador A                           │
│  ├─ text: "RETORNO ANUAL: 3.5%..."                              │
│  ├─ embedding: [0.23, 0.45, 0.67, ...]  (TF-IDF)               │
│  └─ relevance_data: {return: 3.5, vol: 2.5, ...}               │
│                                                                  │
│  Document 2 (Product Structure)                                 │
│  ├─ product_id: PROD001                                         │
│  ├─ product_name: Fondo Conservador A                           │
│  ├─ text: "COMPOSICIÓN: 100% Bonos de Gobierno"                 │
│  ├─ embedding: [0.12, 0.34, 0.56, ...]                         │
│  └─ holdings: [{sector: "Gobierno", ...}]                      │
│                                                                  │
│  ... (8 products × 2 documents = 16 total)                      │
│                                                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┬──────────────┐
    │                         │              │
    ↓                         ↓              ↓

┌──────────────┐      ┌──────────────┐   ┌──────────────┐
│   AGENT      │      │  GUARDRAILS  │   │     BD       │
│ FINTECH      │      │              │   │  POSTGRES    │
├──────────────┤      ├──────────────┤   ├──────────────┤
│ Query RAG    │      │ Validate     │   │ Store Data   │
│ (búsqueda)   │      │ Rules        │   │ (backup)     │
└──────┬───────┘      └──────┬───────┘   └──────┬───────┘
       │                     │                   │
       └─────────────────────┴───────────────────┘
                     │
                     ↓ (User Chat)

┌─────────────────────────────────────────────────────────────────┐
│                 AGENT REASONING & RESPONSE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Recibe: "que productos me recomiendas"                      │
│  2. Busca en RAG: "recomendación perfil riesgo"                 │
│  3. RAG retorna: [PROD003 (score: 0.89), PROD006 (0.85)]       │
│  4. Consulta BD: GET products WHERE id IN (PROD003, PROD006)   │
│  5. Calcula: Diversify portfolio (40% PROD003, 60% PROD006)    │
│  6. Valida: Guardrails (riesgo total, liquidez mínima)         │
│  7. Responde: "Te recomiendo..."                                │
│                                                                  │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ↓ (API Response)

┌─────────────────────────────────────────────────────────────────┐
│              STREAMLIT FRONTEND - VISUALIZATION                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ Datos de la Recomendación                                   │
│  │  ├─ Producto 1: Fondo Conservador A                          │
│  │  │  └─ 40% de $50,000 = $20,000                              │
│  │  │  └─ Retorno esperado: 3.5%                                │
│  │  │  └─ Volatilidad: 2.5%                                     │
│  │  └─ Producto 2: Fondo Equilibrado B                          │
│  │     └─ 60% de $50,000 = $30,000                              │
│  │     └─ Retorno esperado: 6.8%                                │
│  │     └─ Volatilidad: 9.5%                                     │
│  │                                                               │
│  ├─ Métricas de la Cartera                                      │
│  │  └─ Retorno Esperado: 5.7%                                   │
│  │  └─ Volatilidad: 6.8%                                        │
│  │  └─ Sharpe Ratio: 0.42                                       │
│  │                                                               │
│  └─ Información de Datos                                        │
│     └─ Fuente: Real product data from database                  │
│     └─ Sin simulaciones - usa actual product characteristics    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Paso a Paso: CSV → Recomendación

### PASO 1: Cargar CSVs en RAG

**Archivo:** `scripts/seed_rag.py`

```python
# Leer CSV
with open('data/products_info.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Crear documento indexable
        doc_text = f"""
        PRODUCTO: {row['product_name']}
        RETORNO ANUAL: {row['annual_return_pct']}%
        VOLATILIDAD: {row['annual_volatility_pct']}%
        ...
        """

        # Agregar a RAG
        rag_manager.add_document({
            'product_id': row['product_id'],
            'product_name': row['product_name'],
            'annual_return_pct': float(row['annual_return_pct']),
            'text': doc_text
        })
```

**Resultado:** RAG indexa 8 productos × 2 documentos (info + estructura) = 16 documentos

---

### PASO 2: Usuario Solicita Recomendación

**Entrada en Streamlit:**
```
Usuario: "que me recomiendas para invertir $50k en 24 meses"
```

**Flujo:**
```
Streamlit → API (POST /recommendation)
  {
    "client_id": "CLI001",
    "amount": 50000,
    "risk_profile": "moderado",
    "months": 24,
    "target_return": 8.0
  }
```

---

### PASO 3: Agent Busca en RAG

**Código en fintech_agent.py:**
```python
# El agent busca en RAG
results = self.rag.search_products(
    query="inversión moderado 24 meses retorno",
    top_k=3
)

# RAG retorna productos ordenados por relevancia
{
    "product_name": "Fondo Moderado B",
    "annual_return_pct": 6.5,
    "annual_volatility_pct": 8.5,
    "relevance_score": 0.89
}
```

---

### PASO 4: Agent Consulta Base de Datos

**Código:**
```python
# Obtener productos elegibles de BD
self.db_server.connect()
products = self.db_server.query_eligible_products(
    amount=50000,
    risk_profile="moderado",
    months=24
)
# Retorna lista de productos con características reales
```

**Datos desde BD:**
```json
[
  {
    "id": "PROD002",
    "name": "Fondo Moderado B",
    "annual_rate": 0.065,
    "min_months": 6,
    "type": "moderado",
    "liquidity": "media"
  },
  {
    "id": "PROD006",
    "name": "Fondo Equilibrado B",
    "annual_rate": 0.068,
    "min_months": 6,
    "type": "moderado",
    "liquidity": "media"
  }
]
```

---

### PASO 5: Calcular Diversificación

**Código:**
```python
# Diversificar portafolio
allocations = FinanceCalculator.diversify_portfolio(
    total_amount=50000,
    eligible_products=products,
    client_risk_profile="moderado",
    max_aggressive_pct=40
)

# Retorna: ProductAllocation objects con asignaciones
[
  ProductAllocation(
    product_id="PROD002",
    product_name="Fondo Moderado B",
    percentage=40.0,
    amount=20000.0,
    annual_rate=0.065
  ),
  ProductAllocation(
    product_id="PROD006",
    product_name="Fondo Equilibrado B",
    percentage=60.0,
    amount=30000.0,
    annual_rate=0.068
  )
]
```

---

### PASO 6: Calcular Métricas

**Código:**
```python
# Calcular métricas de portafolio
metrics = FinanceCalculator.calculate_portfolio_metrics(allocations)

# Retorna:
{
    "expected_return": 0.067,  # 6.7% ponderado
    "expected_volatility": 0.086,  # 8.6% ponderado
    "expected_liquidity": "media",
    "sharpe_ratio": 0.38
}
```

---

### PASO 7: Validar Guardrails

**Código:**
```python
# Validar restricciones
is_valid, violations = FinancialGuardrails.validate_recommendation(
    client_profile={"risk_profile": "moderado"},
    portfolio_allocation=allocations,
    expected_return=0.067
)

# Retorna: (True, [])  ← Recomendación válida
```

---

### PASO 8: Retornar Recomendación

**Respuesta API:**
```json
{
  "client_id": "CLI001",
  "recommendation": {
    "allocations": [
      {
        "product_id": "PROD002",
        "product_name": "Fondo Moderado B",
        "percentage": 40.0,
        "amount": 20000.0,
        "annual_rate": 6.5
      },
      {
        "product_id": "PROD006",
        "product_name": "Fondo Equilibrado B",
        "percentage": 60.0,
        "amount": 30000.0,
        "annual_rate": 6.8
      }
    ],
    "metrics": {
      "expected_return": 0.067,
      "expected_volatility": 0.086,
      "expected_liquidity": "media",
      "sharpe_ratio": 0.38
    },
    "data_source": "Real product data from database",
    "note": "No simulations - uses actual product characteristics"
  },
  "guardrails": {
    "is_valid": true,
    "violations": []
  }
}
```

---

### PASO 9: Mostrar en Streamlit

**Interfaz:**
```
📋 Asignación Recomendada
┌──────────────────────────────────────────────────────────┐
│ Producto                      │ Porcentaje │ Monto USD   │
├──────────────────────────────────────────────────────────┤
│ Fondo Moderado B              │ 40.0%      │ $20,000     │
│ Fondo Equilibrado B           │ 60.0%      │ $30,000     │
└──────────────────────────────────────────────────────────┘

📊 Métricas de la Cartera
┌────────────────────┬────────────────────────────────────┐
│ Retorno Esperado   │ 6.7%                               │
│ Volatilidad        │ 8.6%                               │
│ Sharpe Ratio       │ 0.38                               │
│ Liquidez           │ media                              │
└────────────────────┴────────────────────────────────────┘

📊 Información de Datos
┌────────────────────────────────────────────────────────┐
│ 📌 Fuente: Real product data from database              │
│ ✓ No simulations - uses actual product characteristics  │
└────────────────────────────────────────────────────────┘
```

---

## 📝 Comparación: Datos Reales vs Simulados

### CON SIMULACIONES (Antiguo - ❌ ELIMINADO)

```json
{
  "simulations": {
    "pessimistic": {
      "final_value": 42500,
      "total_return": -0.15  // -15%
    },
    "base": {
      "final_value": 53500,
      "total_return": 0.07  // 7%
    },
    "optimistic": {
      "final_value": 65000,
      "total_return": 0.30  // 30%
    }
  }
}
```

**Problema:**
- Estos números son **inventados** en el código
- No basados en datos reales
- Crean expectativas falsas

### SIN SIMULACIONES (Nuevo - ✅)

```json
{
  "metrics": {
    "expected_return": 0.067,      // 6.7% basado en datos CSV
    "expected_volatility": 0.086,  // 8.6% basado en datos CSV
    "sharpe_ratio": 0.38           // Calculado de datos reales
  },
  "data_source": "Real product data from database",
  "note": "No simulations - uses actual product characteristics"
}
```

**Beneficio:**
- Números basados en **datos reales de CSVs**
- Transparencia sobre las características del producto
- Sin expectativas infladas

---

## 🔍 Debugging: Seguir el Flujo de Datos

### ¿Dónde está mi producto?

**Pregunta:** "¿Por qué no aparece PROD001 en la recomendación?"

**Debug:**

1. **¿Existe en CSV?**
   ```bash
   grep "PROD001" data/products_info.csv
   ```
   Si no aparece → Agregarlo al CSV

2. **¿Está en RAG?**
   ```bash
   python3 scripts/seed_rag.py
   # Buscar "PROD001" en output
   ```

3. **¿Cumple criterios?**
   - ¿`min_investment` ≤ `amount`?
   - ¿`min_months` ≤ `investment_horizon_months`?
   - ¿`product_type` es compatible con `risk_profile`?

4. **¿Pasa RAG search?**
   ```bash
   # Haz test query
   curl http://localhost:8000/chat \
     -d '{"client_id":"CLI001","message":"que tal PROD001"}'
   ```

5. **¿Valida guardrails?**
   - ¿Retorno ≥ objetivo del cliente?
   - ¿Riesgo dentro de límites?

---

## 📊 Flujo de Datos por Componente

### RAG (Vector Database)

```
Input:  CSV rows
Process: TF-IDF embedding
Output: Document chunks with vectors
```

### Database (PostgreSQL)

```
Input:  Product info + Client data
Process: SQL queries
Output: Filtered product lists
```

### Finance Calculator

```
Input:  Products list + Amount
Process: Diversification algorithm
Output: Allocations with weights
```

### Agent

```
Input:  User message
Process: RAG search + DB query + Calculation + Validation
Output: Recommendation with metrics
```

---

## 🎯 Key Insights

1. **CSV es la fuente de verdad**: Todos los datos de productos vienen de los CSVs

2. **RAG es para búsqueda**: Permite encontrar productos relevantes con "len semantic"

3. **BD es para consultas exactas**: Retorna datos estructurados validados

4. **Sin simulaciones**: Las métricas son reales, no inventadas

5. **Transparencia**: El output claramente indica que usa "Real product data"

---

**Last Updated**: 2024-11-27
**Version**: 1.0.0 (CSV-based data flow)

# 📊 CSV Products Guide - FinAdvisor

Este documento explica cómo FinAdvisor usa **archivos CSV en lugar de PDFs** para cargar información de productos en el sistema RAG.

---

## 📋 Tabla de Contenidos

1. [¿Por Qué CSV en lugar de PDF?](#por-qué-csv-en-lugar-de-pdf)
2. [Estructura de CSVs](#estructura-de-csvs)
3. [Cómo Cargar Datos](#cómo-cargar-datos)
4. [Agregar Nuevos Productos](#agregar-nuevos-productos)
5. [Búsqueda en RAG](#búsqueda-en-rag)
6. [Comparación PDF vs CSV](#comparación-pdf-vs-csv)

---

## ❓ ¿Por Qué CSV en lugar de PDF?

### Ventajas de CSV

| Aspecto | CSV | PDF |
|--------|-----|-----|
| **Estructura** | Tabular, fácil de parsear | Texto no estructurado |
| **Búsqueda RAG** | Datos limpios y indexables | Requiere OCR/parsing complejo |
| **Actualización** | Editar con Excel/spreadsheet | Requiere regenerar documento |
| **Control de Datos** | Datos validados, consistentes | Variabilidad de formato |
| **Base de Datos Vectorial** | Directamente indexable | Requiere preprocesamiento |
| **Relaciones** | FK con tabla de estructura | Información dispersa |

### Razón Técnica

**El RAG necesita información estructurada** para hacer búsquedas vectoriales efectivas:
- Retorno esperado (número)
- Volatilidad (número)
- Tipo de producto (conservador/moderado/agresivo)
- Liquidez en días (número)
- Composición de acciones (lista estructurada)

Los PDFs tienen esta información **dispersa en texto libre**, lo que hace difícil:
1. Extraer valores exactos
2. Realizar búsquedas semánticas precisas
3. Mantener relaciones entre datos

Los CSVs tienen esta información **organizada en columnas**, permitiendo:
1. Búsquedas exactas y semánticas
2. Relaciones claras entre productos y composición
3. Fácil mantenimiento y actualización

---

## 📁 Estructura de CSVs

### 1. `data/products_info.csv`

Información general de cada producto.

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `product_id` | String | `PROD001` | ID único del producto |
| `product_name` | String | `Fondo Conservador A` | Nombre del producto |
| `product_type` | String | `conservador` | Tipo: conservador/moderado/agresivo |
| `annual_return_pct` | Float | `3.5` | Retorno anual esperado (%) |
| `annual_volatility_pct` | Float | `2.5` | Volatilidad anual (%) |
| `liquidity_days` | Integer | `5` | Días para liquidar posición |
| `liquidity_level` | String | `alta` | Nivel: alta/media/baja |
| `min_investment_usd` | Float | `1000` | Inversión mínima (USD) |
| `max_allocation_conservador_pct` | Float | `50` | % máximo para perfil conservador |
| `max_allocation_moderado_pct` | Float | `60` | % máximo para perfil moderado |
| `max_allocation_agresivo_pct` | Float | `70` | % máximo para perfil agresivo |
| `description` | String | `Fondo de bonos...` | Descripción del producto |

**Ejemplo:**
```csv
product_id,product_name,product_type,annual_return_pct,annual_volatility_pct,liquidity_days,liquidity_level,min_investment_usd,max_allocation_conservador_pct,max_allocation_moderado_pct,max_allocation_agresivo_pct,description
PROD001,Fondo Conservador A,conservador,3.5,2.5,5,alta,1000,50,40,30,Fondo de bonos de gobierno con baja volatilidad.
```

### 2. `data/product_structure.csv`

Composición detallada de cada producto (qué acciones/bonos contiene).

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `product_id` | String | `PROD001` | ID del producto |
| `product_name` | String | `Fondo Conservador A` | Nombre del producto |
| `asset_type` | String | `gobierno_bonos` | Tipo: acciones/bonos/fondos/etc |
| `allocation_percentage` | Float | `100.0` | % asignado a este activo |
| `ticker` | String | `NVDA` | Ticker (NASDAQ/NYSE) o vacío |
| `company_name` | String | `NVIDIA` | Nombre de empresa o fondo |
| `sector` | String | `Tecnología` | Sector de la economía |
| `risk_level` | String | `alto` | muy_bajo/bajo/medio/alto |
| `country` | String | `USA` | País de origen |

**Ejemplo:**
```csv
product_id,product_name,asset_type,allocation_percentage,ticker,company_name,sector,risk_level,country
PROD004,Zest Bond Liquid CG2,acciones,25.0,AGEE,Agnico Eagle,Minería,medio,Canadá
PROD004,Zest Bond Liquid CG2,acciones,25.0,ANET,Arista Networks,Tecnología,alto,USA
PROD004,Zest Bond Liquid CG2,acciones,25.0,META,Meta Platforms,Tecnología,alto,USA
PROD004,Zest Bond Liquid CG2,acciones,25.0,NVDA,NVIDIA,Semiconductores,alto,USA
```

---

## 🚀 Cómo Cargar Datos

### Opción 1: Script Automático (Recomendado)

```bash
# El script run_local.sh carga automáticamente los CSVs
./scripts/run_local.sh
```

### Opción 2: Manual - Cargar CSVs a RAG

```bash
# Ejecutar el script de seeding
python3 scripts/seed_rag.py
```

**Output:**
```
🧠 FinAdvisor RAG Initialization

==================================================
📚 Creating RAG Manager...
📖 Loading products from data/products_info.csv...

  ✓ Fondo Conservador A (3.5% retorno, 2.5% volatilidad)
  ✓ Fondo Moderado B (6.5% retorno, 8.5% volatilidad)
  ...
✅ Loaded 8 products

📊 Loading product structure from data/product_structure.csv...

  ✓ Fondo Conservador A - 1 componentes
  ✓ Zest Bond Liquid CG2 - 4 componentes
  ...
✅ Loaded structure for 8 products

==================================================
✅ RAG initialized with 16 documentos

🔍 Testing RAG search:

Query: 'deuda privada retorno'
  ✓ ZEST Deuda Privada (score: 0.850)
  ...
```

---

## ✏️ Agregar Nuevos Productos

### Paso 1: Editar `data/products_info.csv`

Abrir con Excel o Google Sheets:

```csv
PROD009,Nuevo Fondo,moderado,6.0,7.0,8,media,2000,50,60,50,Descripción del nuevo fondo
```

### Paso 2: Editar `data/product_structure.csv`

Agregar composición:

```csv
PROD009,Nuevo Fondo,renta_fija,50.0,,Bonos corporativos,Finanzas,bajo,USA
PROD009,Nuevo Fondo,renta_variable,50.0,,Índice S&P 500,Multiactor,medio,USA
```

### Paso 3: Reload RAG

```bash
python3 scripts/seed_rag.py
```

### Paso 4: Verificar

```bash
curl http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"client_id":"CLI001","message":"que me recomiendas"}'
```

---

## 🔍 Búsqueda en RAG

El RAG indexa automáticamente la información de CSVs y permite búsquedas semánticas.

### Ejemplo 1: Búsqueda por Características

**Query:** "fondo conservador bajo riesgo"
```json
{
  "product_name": "Fondo Conservador A",
  "annual_return_pct": 3.5,
  "annual_volatility_pct": 2.5,
  "relevance_score": 0.89
}
```

### Ejemplo 2: Búsqueda por Composición

**Query:** "NVIDIA tecnología"
```json
{
  "product_name": "Zest Bond Liquid CG2",
  "holdings": [
    {
      "ticker": "NVDA",
      "company_name": "NVIDIA",
      "sector": "Semiconductores",
      "allocation_percentage": 25.0
    }
  ],
  "relevance_score": 0.92
}
```

### Ejemplo 3: Búsqueda por Riesgo y Horizonte

**Query:** "inversión moderado plazo 24 meses"
```json
{
  "product_name": "Fondo Moderado B",
  "product_type": "moderado",
  "annual_return_pct": 6.5,
  "liquidity_days": 7,
  "relevance_score": 0.87
}
```

---

## 📊 Comparación: PDF vs CSV

### Flujo con PDF (Antiguo)

```
PDF File
  ↓
[Extract Text / OCR]
  ↓
[Parse Semi-Structured]
  ↓
[Index in RAG]
  ↓
[Búsquedas Aproximadas]
```

**Problemas:**
- OCR puede fallar
- Información dispersa en texto
- Búsquedas semánticas imprecisas
- Difícil mantener actualizado

### Flujo con CSV (Nuevo)

```
CSV File
  ↓
[Read CSV DictReader]
  ↓
[Structured Data]
  ↓
[Index in RAG]
  ↓
[Búsquedas Precisas + Semánticas]
```

**Ventajas:**
- Cero errores de parsing
- Información estructurada clara
- Búsquedas exactas y semánticas
- Mantenimiento trivial

---

## 🗄️ Columnas Explicadas

### Retorno Anual (`annual_return_pct`)

```
3.5  → 3.5% anual (bonos conservadores)
6.5  → 6.5% anual (fondos equilibrados)
10.5 → 10.5% anual (fondos agresivos)
```

**Nota:** Este es el retorno **esperado** basado en datos históricos.

### Volatilidad Anual (`annual_volatility_pct`)

```
2.5  → Muy baja volatilidad (bonos)
8.5  → Volatilidad media (equilibrado)
15.0 → Alta volatilidad (acciones)
```

**Nota:** Mide la variabilidad de retornos.

### Liquidez (`liquidity_days`)

```
3-5   días → Muy líquido (fondos)
10-15 días → Liquidez media
20+   días → Poco líquido (estructurados)
```

**Nota:** Tiempo para convertir a efectivo.

### Asignación Máxima por Perfil

```
conservador:
  max_allocation_conservador_pct = 50%   ← Máximo que puede asignar
  max_allocation_moderado_pct   = 40%   ← Menos si es moderado
  max_allocation_agresivo_pct   = 30%   ← Menos si es agresivo

moderado:
  max_allocation_conservador_pct = 60%   ← Puede asignar más
  max_allocation_moderado_pct   = 60%
  max_allocation_agresivo_pct   = 50%

agresivo:
  max_allocation_conservador_pct = 30%
  max_allocation_moderado_pct   = 50%
  max_allocation_agresivo_pct   = 70%   ← Máximo permitido
```

---

## 🧪 Testing

### Test 1: Verificar Carga

```bash
python3 scripts/seed_rag.py
```

Debería mostrar "✅ RAG seeding completed successfully!"

### Test 2: Búsqueda en API

```bash
curl http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "client_id":"CLI001",
    "message":"que productos tiene alto retorno"
  }'
```

### Test 3: Recomendación en Streamlit

1. Abrir http://localhost:8501
2. Ingresar cliente: `CLI001`
3. Tab "Recomendación"
4. Click "Generar Recomendación"
5. Ver asignaciones de productos reales (sin simulaciones)

---

## 📝 Notas Importantes

1. **Sin Simulaciones**: Los datos son REALES de los CSVs, no simulados.

2. **Actualización**: Para cambiar un producto, edita el CSV y ejecuta `seed_rag.py`

3. **Validación**: Los CSVs deben tener formato correcto (columnas bien nombradas)

4. **Encoding**: Usa UTF-8 para caracteres especiales (ñ, á, etc.)

5. **Relaciones**: Los CSVs están vinculados por `product_id`

---

## 🔧 Troubleshooting

### "Error loading CSV"

```bash
# Verifica que el archivo existe
ls -la data/products_info.csv

# Verifica encoding
file data/products_info.csv
# Debe ser: UTF-8 Unicode text
```

### "No results found"

```bash
# Verifica que RAG fue cargado
python3 scripts/seed_rag.py

# Verifica que el servidor está corriendo
curl http://localhost:8000/health
```

### "Product not found in recommendations"

```bash
# Verifica min_investment
# Ejemplo: Si min_investment=5000 y amount=1000, no aparecerá

# Verifica product_type
# Ejemplo: Si es PROD001 (conservador) y buscas agresivo, no aparecerá
```

---

## 📚 Related Documentation

- [LOCAL_SETUP.md](./LOCAL_SETUP.md) - Cómo correr FinAdvisor localmente
- [README_ES.md](./README_ES.md) - Explicación de arquitectura
- [QUICK_START.md](./QUICK_START.md) - Comandos rápidos

---

**Last Updated**: 2024-11-27
**Version**: 1.0.0 (CSV-based products)

# 📊 Guía de Datos - FinAdvisor

Estructura de los archivos CSV y datos de seed del sistema.

---

## Productos (`data/products.csv`)

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `id` | String | `PROD001` | ID único |
| `name` | String | `Fondo Conservador A` | Nombre del producto |
| `type` | String | `conservador` | conservador/moderado/agresivo |
| `annual_rate` | Float | `0.035` | Retorno anual decimal (0.035 = 3.5%) |
| `min_months` | Integer | `6` | Horizonte mínimo |
| `max_months` | Integer | `120` | Horizonte máximo |
| `min_amount` | Float | `1000` | Inversión mínima USD |
| `liquidity` | String | `media` | alta/media/baja |
| `allows_buyback` | Boolean | `true` | Permite recompra |
| `withdrawal_window_months` | Integer | `1` | Ventana sin penalidad |
| `withdrawal_penalty_pct` | Float | `0.5` | Penalidad % |

**Ejemplo:**
```csv
PROD001,Fondo Conservador A,conservador,0.035,6,120,1000,media,true,1,0.5
```

### Restricciones por Perfil

**Conservador**: 70-100% conservador, 0-30% moderado, **0% agresivo**
**Moderado**: 20-60% conservador, 30-70% moderado, 0-30% agresivo
**Agresivo**: 0-30% conservador, 10-40% moderado, 40-80% agresivo

---

## Clientes (`data/clients.csv`)

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `client_id` | String | `CLI001` | ID único |
| `name` | String | `Carlos Martínez` | Nombre completo |
| `email` | String | `carlos@example.com` | Email |
| `risk_profile` | String | `conservador` | conservador/moderado/agresivo |
| `investment_horizon_months` | Integer | `24` | Horizonte en meses |
| `available_amount_usd` | Float | `10000` | Capital DISPONIBLE (no invertido) |
| `liquidity_preference` | String | `media` | alta/media/baja |
| `target_return_pct` | Float | `5.0` | Objetivo de retorno % |
| `goals` | String | `"ahorro retiro"` | Objetivos financieros |

**Ejemplo:**
```csv
CLI001,Carlos Martínez,carlos@example.com,conservador,24,10000,media,5.0,"ahorro retiro"
```

**Nota**: `available_amount_usd` es el capital **disponible para invertir**, no el ya invertido.

---

## Portfolios (`data/portfolios.csv`)

Productos ya contratados por clientes (máximo 2 por cliente).

| Campo | Tipo | Ejemplo | Descripción |
|-------|------|---------|-------------|
| `portfolio_id` | String | `PORT_CLI001_001` | ID único del portfolio |
| `client_id` | String | `CLI001` | ID del cliente |
| `product_id` | String | `PROD001` | ID del producto |
| `allocation_amount` | Float | `9000.00` | Monto invertido USD |
| `allocation_percentage` | Float | `60.00` | Porcentaje del portfolio |
| `purchase_date` | Timestamp | `2025-09-15 10:30:00` | Fecha de compra |

**Ejemplo:**
```csv
PORT_CLI001_001,CLI001,PROD001,9000.00,60.00,2025-09-15 10:30:00
```

**Resumen de inversiones:**

| Cliente | Perfil | Productos | Invertido | Disponible |
|---------|--------|-----------|-----------|------------|
| CLI001 | Conservador | 2 | $15,000 | $10,000 |
| CLI002 | Moderado | 2 | $20,000 | $30,000 |
| CLI003 | Agresivo | 2 | $60,000 | $40,000 |
| CLI004 | Conservador | 1 | $5,000 | $10,000 |

---

## Regenerar Base de Datos

```bash
# Recrear todo (elimina volúmenes)
docker-compose down -v
docker-compose up -d
```

Los datos se cargan automáticamente desde los archivos CSV:
- `data/products.csv` → tabla products
- `data/clients.csv` → tabla clients
- `data/portfolios.csv` → tabla client_portfolios

---

**Última Actualización**: 2026-01-06

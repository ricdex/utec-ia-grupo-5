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

## Portfolios (`data/seed_portfolios.sql`)

Productos ya contratados por clientes (máximo 2 por cliente).

| Cliente | Perfil | Productos | Invertido | Disponible |
|---------|--------|-----------|-----------|------------|
| CLI001 | Conservador | 2 | $15,000 | $10,000 |
| CLI002 | Moderado | 2 | $20,000 | $30,000 |
| CLI003 | Agresivo | 2 | $60,000 | $40,000 |
| CLI004 | Conservador | 1 | $5,000 | $10,000 |

---

## Regenerar Base de Datos

```bash
# Opción 1: Recrear todo (elimina volúmenes)
docker-compose down -v
docker-compose up -d

# Opción 2: Solo reseed (con Makefile)
make reseed
```

Después de `docker-compose up -d`, ejecutar manualmente:

```bash
# Insertar productos y clientes
docker-compose exec -T postgres psql -U postgres -d finadvisor <<'EOF'
INSERT INTO products (id, name, type, annual_rate, min_months, max_months, min_amount, liquidity, allows_buyback, withdrawal_window_months, withdrawal_penalty_pct) VALUES
('PROD001', 'Fondo Conservador A', 'conservador', 0.035, 6, 120, 1000, 'media', true, 1, 0.5),
('PROD002', 'Bonos del Estado 5Y', 'conservador', 0.045, 60, 60, 5000, 'baja', false, 0, 0),
('PROD003', 'Fondo Equilibrado B', 'moderado', 0.065, 12, 120, 2000, 'media', true, 2, 1.5),
('PROD004', 'Acciones Latinoamérica', 'moderado', 0.075, 24, 120, 3000, 'media', true, 3, 2.0),
('PROD005', 'Fondo Crecimiento C', 'agresivo', 0.095, 36, 120, 5000, 'baja', true, 6, 3.0),
('PROD006', 'Criptomonedas Emergentes', 'agresivo', 0.15, 12, 120, 1000, 'alta', true, 0, 0),
('PROD007', 'Plazo Fijo 18 Meses', 'conservador', 0.055, 18, 18, 1000, 'baja', false, 0, 0),
('PROD008', 'ETF Diversificado Global', 'moderado', 0.08, 12, 120, 2500, 'alta', true, 1, 0.5);

INSERT INTO clients (client_id, name, email, risk_profile, investment_horizon_months, available_amount_usd, liquidity_preference, target_return_pct, goals) VALUES
('CLI001', 'Carlos Martínez', 'carlos.martinez@example.com', 'conservador', 24, 10000, 'media', 5.0, 'ahorro retiro, estabilidad'),
('CLI002', 'María García', 'maria.garcia@example.com', 'moderado', 36, 30000, 'media', 8.0, 'crecimiento, educación hijos'),
('CLI003', 'Juan López', 'juan.lopez@example.com', 'agresivo', 60, 40000, 'baja', 12.0, 'maximizar retorno, crear riqueza'),
('CLI004', 'Ana Rodríguez', 'ana.rodriguez@example.com', 'conservador', 12, 10000, 'alta', 3.5, 'emergencia, liquidez');
EOF

# Insertar portfolios
docker-compose exec -T postgres psql -U postgres -d finadvisor < data/seed_portfolios.sql
```

---

**Última Actualización**: 2026-01-06

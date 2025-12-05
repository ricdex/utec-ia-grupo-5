-- Create tables for FinAdvisor
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- conservador, moderado, agresivo
    annual_rate DECIMAL(5, 4) NOT NULL,
    min_months INT NOT NULL,
    max_months INT NOT NULL,
    min_amount DECIMAL(12, 2) NOT NULL,
    liquidity VARCHAR(50) NOT NULL, -- alta, media, baja
    allows_buyback BOOLEAN NOT NULL,
    withdrawal_window_months INT,
    withdrawal_penalty_pct DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clients (
    client_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    risk_profile VARCHAR(50) NOT NULL,
    investment_horizon_months INT NOT NULL,
    available_amount_usd DECIMAL(12, 2) NOT NULL,
    liquidity_preference VARCHAR(50) NOT NULL,
    target_return_pct DECIMAL(5, 2) NOT NULL,
    max_aggressive_pct INT NOT NULL,
    goals TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_portfolios (
    portfolio_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    amount_allocated DECIMAL(12, 2) NOT NULL,
    allocation_percentage DECIMAL(5, 2) NOT NULL,
    allocation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS portfolio_recommendations (
    recommendation_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    recommendation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_return_pct DECIMAL(5, 2) NOT NULL,
    expected_risk_level VARCHAR(50),
    expected_liquidity VARCHAR(50),
    justification TEXT,
    was_accepted BOOLEAN,
    accepted_date TIMESTAMP NULL,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE IF NOT EXISTS recommendation_items (
    item_id VARCHAR(50) PRIMARY KEY,
    recommendation_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    suggested_percentage DECIMAL(5, 2) NOT NULL,
    suggested_amount DECIMAL(12, 2) NOT NULL,
    FOREIGN KEY (recommendation_id) REFERENCES portfolio_recommendations(recommendation_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Create indexes
CREATE INDEX idx_client_risk_profile ON clients(risk_profile);
CREATE INDEX idx_product_type ON products(type);
CREATE INDEX idx_portfolio_client ON client_portfolios(client_id);
CREATE INDEX idx_recommendation_client ON portfolio_recommendations(client_id);

-- Insert sample products
INSERT INTO products (id, name, type, annual_rate, min_months, max_months, min_amount, liquidity, allows_buyback, withdrawal_window_months, withdrawal_penalty_pct) VALUES
('PROD001', 'Fondo Conservador A', 'conservador', 0.035, 6, 120, 1000, 'media', true, 1, 0.5),
('PROD002', 'Bonos del Estado 5Y', 'conservador', 0.045, 60, 60, 5000, 'baja', false, 0, 0),
('PROD003', 'Fondo Equilibrado B', 'moderado', 0.065, 12, 120, 2000, 'media', true, 2, 1.5),
('PROD004', 'Acciones Latinoamérica', 'moderado', 0.075, 24, 120, 3000, 'media', true, 3, 2.0),
('PROD005', 'Fondo Crecimiento C', 'agresivo', 0.095, 36, 120, 5000, 'baja', true, 6, 3.0),
('PROD006', 'Criptomonedas Emergentes', 'agresivo', 0.15, 12, 120, 1000, 'alta', true, 0, 0),
('PROD007', 'Plazo Fijo 18 Meses', 'conservador', 0.055, 18, 18, 1000, 'baja', false, 0, 0),
('PROD008', 'ETF Diversificado Global', 'moderado', 0.08, 12, 120, 2500, 'alta', true, 1, 0.5);

-- Insert sample clients
INSERT INTO clients (client_id, name, email, risk_profile, investment_horizon_months, available_amount_usd, liquidity_preference, target_return_pct, max_aggressive_pct, goals) VALUES
('CLI001', 'Carlos Martínez', 'carlos.martinez@example.com', 'conservador', 24, 25000, 'media', 5.0, 20, 'ahorro retiro, estabilidad'),
('CLI002', 'María García', 'maria.garcia@example.com', 'moderado', 36, 50000, 'media', 8.0, 40, 'crecimiento, educación hijos'),
('CLI003', 'Juan López', 'juan.lopez@example.com', 'agresivo', 60, 75000, 'baja', 12.0, 60, 'maximizar retorno, crear riqueza'),
('CLI004', 'Ana Rodríguez', 'ana.rodriguez@example.com', 'conservador', 12, 15000, 'alta', 3.5, 10, 'emergencia, liquidez');

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
    goals TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_portfolios (
    portfolio_id VARCHAR(50) PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    allocation_amount DECIMAL(12, 2) NOT NULL,
    allocation_percentage DECIMAL(5, 2) NOT NULL,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
CREATE INDEX IF NOT EXISTS idx_client_risk_profile ON clients(risk_profile);
CREATE INDEX IF NOT EXISTS idx_product_type ON products(type);
CREATE INDEX IF NOT EXISTS idx_portfolio_client ON client_portfolios(client_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_client ON portfolio_recommendations(client_id);

-- Data is loaded from CSV files by seed_database.py
-- See data/products.csv and data/clients.csv

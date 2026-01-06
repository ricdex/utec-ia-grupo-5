-- Seed client portfolios with existing investments
-- Maximum 2 products per client to allow for new recommendations

-- Clear existing portfolios
TRUNCATE TABLE client_portfolios CASCADE;

-- CLI001 (Conservador) - Portfolio: $15,000 invested (2 products)
-- Has $10,000 available for new investments
-- 60% Fondo Conservador A, 40% ETF Diversificado Global
INSERT INTO client_portfolios (portfolio_id, client_id, product_id, allocation_amount, allocation_percentage, purchase_date)
VALUES
    ('PORT_CLI001_001', 'CLI001', 'PROD001', 9000.00, 60.00, '2025-09-15 10:30:00'),
    ('PORT_CLI001_002', 'CLI001', 'PROD008', 6000.00, 40.00, '2025-09-15 10:30:00');

-- CLI002 (Moderado) - Portfolio: $20,000 invested (2 products)
-- Has $30,000 available for new investments
-- 60% Fondo Equilibrado B, 40% ETF Diversificado Global
INSERT INTO client_portfolios (portfolio_id, client_id, product_id, allocation_amount, allocation_percentage, purchase_date)
VALUES
    ('PORT_CLI002_001', 'CLI002', 'PROD003', 12000.00, 60.00, '2025-10-01 14:20:00'),
    ('PORT_CLI002_002', 'CLI002', 'PROD008', 8000.00, 40.00, '2025-10-01 14:20:00');

-- CLI003 (Agresivo) - Portfolio: $60,000 invested (2 products)
-- Has $40,000 available for new investments
-- 70% Fondo Crecimiento C, 30% ETF Diversificado
INSERT INTO client_portfolios (portfolio_id, client_id, product_id, allocation_amount, allocation_percentage, purchase_date)
VALUES
    ('PORT_CLI003_001', 'CLI003', 'PROD005', 42000.00, 70.00, '2025-08-20 09:15:00'),
    ('PORT_CLI003_002', 'CLI003', 'PROD008', 18000.00, 30.00, '2025-08-20 09:15:00');

-- CLI004 (Conservador) - Portfolio: $5,000 invested (1 product)
-- Has $10,000 available for new investments
-- 100% Fondo Conservador A (only 1 product to test single product scenario)
INSERT INTO client_portfolios (portfolio_id, client_id, product_id, allocation_amount, allocation_percentage, purchase_date)
VALUES
    ('PORT_CLI004_001', 'CLI004', 'PROD001', 5000.00, 100.00, '2025-11-10 16:45:00');

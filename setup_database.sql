-- ============================================================================
-- AI Supply Chain - Santista
-- Script de criação das tabelas no PostgreSQL
-- Execute este script no seu banco antes de rodar o workflow n8n
-- ============================================================================

-- 1) Tabela de dados de vendas (alimentada pelo ERP)
CREATE TABLE IF NOT EXISTS sales_data (
    id          SERIAL PRIMARY KEY,
    sku         VARCHAR(50)    NOT NULL,
    client      VARCHAR(200)   NOT NULL,
    sales       NUMERIC(12,2)  NOT NULL DEFAULT 0,
    stock       NUMERIC(12,2)  NOT NULL DEFAULT 0,
    cost        NUMERIC(10,2)  NOT NULL DEFAULT 0,
    cost_cotton NUMERIC(10,2)  DEFAULT 0,
    cost_labor  NUMERIC(10,2)  DEFAULT 0,
    cost_energy NUMERIC(10,2)  DEFAULT 0,
    date        DATE           NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_sales_data_date ON sales_data(date);
CREATE INDEX IF NOT EXISTS idx_sales_data_sku  ON sales_data(sku);

-- 2) Tabela de resultados do Supply Chain (escrita pelo n8n)
CREATE TABLE IF NOT EXISTS supply_chain_results (
    id               SERIAL PRIMARY KEY,
    sku              VARCHAR(50)   NOT NULL,
    client           VARCHAR(200)  NOT NULL,
    forecast_30d     NUMERIC(12,2) DEFAULT 0,
    days_of_stock    NUMERIC(10,1) DEFAULT 0,
    risk             VARCHAR(20)   DEFAULT 'N/A',
    inventory_status VARCHAR(20)   DEFAULT 'N/A',
    suggested_order  NUMERIC(12,2) DEFAULT 0,
    stock_value_brl  NUMERIC(14,2) DEFAULT 0,
    suggested_price  NUMERIC(10,2) DEFAULT 0,
    margin_pct       NUMERIC(5,1)  DEFAULT 0,
    pricing_action   VARCHAR(20)   DEFAULT 'N/A',
    processed_at     TIMESTAMPTZ   DEFAULT NOW(),

    UNIQUE(sku, client)
);

-- 3) Dados de exemplo para teste
INSERT INTO sales_data (sku, client, sales, stock, cost, cost_cotton, cost_labor, cost_energy, date)
VALUES
    ('SKU-001', 'P&G Brasil',       300,  500,  12.50, 5.00, 4.50, 3.00, CURRENT_DATE),
    ('SKU-002', 'Magazine Luiza',    150, 2000,   8.00, 3.20, 2.80, 2.00, CURRENT_DATE),
    ('SKU-003', 'VF Corporation',    900,   45,  25.00, 10.00, 9.00, 6.00, CURRENT_DATE),
    ('SKU-004', 'Renner',            600,  800,  15.00, 6.00, 5.40, 3.60, CURRENT_DATE),
    ('SKU-005', 'Havan',             100, 3500,   9.50, 3.80, 3.42, 2.28, CURRENT_DATE)
ON CONFLICT DO NOTHING;

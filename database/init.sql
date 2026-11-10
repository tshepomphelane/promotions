
CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS customer_activity (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR NOT NULL REFERENCES customers(id),
    purchase_count INTEGER NOT NULL DEFAULT 0,
    total_spend NUMERIC(12, 2) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_customer_activity_customer
ON customer_activity(customer_id);

CREATE TABLE IF NOT EXISTS promotions (
    id VARCHAR PRIMARY KEY,
    description VARCHAR NOT NULL,
    discount_percent INTEGER NOT NULL,
    minimum_purchases INTEGER NOT NULL,
    minimum_spend NUMERIC(12, 2) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);


INSERT INTO customers (id)
VALUES
    ('CUST-001'),
    ('CUST-002'),
    ('CUST-003')
ON CONFLICT DO NOTHING;


INSERT INTO customer_activity
    (customer_id, purchase_count, total_spend)
VALUES
    ('CUST-001', 5, 1500.00),
    ('CUST-002', 1, 100.00),
    ('CUST-003', 10, 5000.00)
ON CONFLICT DO NOTHING;


INSERT INTO promotions
    (id, description, discount_percent,
     minimum_purchases, minimum_spend, active)
VALUES
    ('WELCOME001', 'Welcome discount', 10, 3, 1500.00, TRUE),
    ('VIP-CUST', 'VIP customer discount', 30, 9, 5000.00, TRUE),
    ('RSPENDER', 'Spend rewards', 5, 2, 600.00, TRUE)
ON CONFLICT DO NOTHING;

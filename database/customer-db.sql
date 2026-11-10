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
    ('CUST-003', 10, 5000.00);

INSERT INTO promotions
    (id, description, discount_percent, minimum_purchase, minimun_spend, active)
VALUES 
    ('WELCOME001', 'Welcome discount', 10, 3, 1500.00, TRUE),
    ('VIP-CUST', 'VIP customer discount', 30, 9, 5000.00, TRUE),
    ('RSPENDER', 'Spend rewards', 5, 2, 600.00, TRUE)
ON CONFLICT DO NOTHING;
-- Development/demo seed data only. No real customer or payment data is used.
-- This file is intentionally safe to re-run.

INSERT INTO role (role_name, permissions) VALUES
    ('customer', '{"transactions": ["read", "create"], "alerts": ["read_own"]}'::jsonb),
    ('investigator', '{"transactions": ["read"], "alerts": ["read", "update"], "investigations": ["read", "update"]}'::jsonb),
    ('administrator', '{"*": ["read", "create", "update", "delete"]}'::jsonb)
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO branch (branch_name, address, ifsc_code) VALUES
    ('Central Demo Branch', '100 Market Street, Demo City', 'DEMO0000001'),
    ('North Demo Branch', '200 North Avenue, Demo City', 'DEMO0000002')
ON CONFLICT (ifsc_code) DO NOTHING;

INSERT INTO customer (full_name, email, phone, address) VALUES
    ('Asha Nair', 'asha.nair@example.test', '+1-555-0101', '1 Example Lane, Demo City'),
    ('Ravi Menon', 'ravi.menon@example.test', '+1-555-0102', '2 Example Lane, Demo City'),
    ('Demo Investigator', 'investigator@example.test', '+1-555-0199', '9 Operations Road, Demo City')
ON CONFLICT DO NOTHING;

INSERT INTO merchant_category (category_name, description) VALUES
    ('Grocery', 'Simulated grocery and household merchants'),
    ('Travel', 'Simulated travel and transportation merchants'),
    ('Digital Services', 'Simulated online and subscription merchants')
ON CONFLICT (category_name) DO NOTHING;

INSERT INTO location (city, state, country, latitude, longitude)
SELECT 'Demo City', 'Demo State', 'US', 40.712800, -74.006000
WHERE NOT EXISTS (
    SELECT 1 FROM location WHERE city = 'Demo City' AND country = 'US'
);

INSERT INTO account (customer_id, branch_id, account_number, account_type, balance, currency_code)
SELECT c.customer_id, b.branch_id, v.account_number, v.account_type, v.balance, 'USD'
FROM (VALUES
    ('asha.nair@example.test', 'DEMO0000001', '100000000001', 'checking', 12500.00::numeric),
    ('ravi.menon@example.test', 'DEMO0000002', '100000000002', 'savings', 8500.00::numeric)
) AS v(email, ifsc_code, account_number, account_type, balance)
JOIN customer c ON c.email = v.email
JOIN branch b ON b.ifsc_code = v.ifsc_code
ON CONFLICT (account_number) DO NOTHING;

INSERT INTO merchant (category_id, location_id, merchant_name)
SELECT mc.category_id, l.location_id, v.merchant_name
FROM (VALUES
    ('Grocery', 'Demo Market'),
    ('Travel', 'Demo Air'),
    ('Digital Services', 'Demo Streaming')
) AS v(category_name, merchant_name)
JOIN merchant_category mc ON mc.category_name = v.category_name
JOIN location l ON l.city = 'Demo City' AND l.country = 'US'
WHERE NOT EXISTS (
    SELECT 1 FROM merchant m WHERE m.merchant_name = v.merchant_name
);

INSERT INTO fraud_rule (rule_name, description, threshold, configuration) VALUES
    ('large_amount', 'Flags transactions above the configured amount threshold', 5000.00, '{"score": 0.75}'::jsonb),
    ('rapid_frequency', 'Flags repeated transactions within a short time window', NULL, '{"window_minutes": 10, "max_transactions": 5, "score": 0.65}'::jsonb),
    ('high_risk_merchant', 'Flags transactions involving a configured high-risk merchant category', NULL, '{"score": 0.55}'::jsonb)
ON CONFLICT (rule_name, version) DO NOTHING;

INSERT INTO ml_model (
    model_name, version, model_path, precision_score, recall_score, f1_score,
    pr_auc_score, roc_auc_score, deployment_status, metadata
) VALUES (
    'paysim-baseline', 'untrained', 'ml/models/paysim-baseline.joblib',
    NULL, NULL, NULL, NULL, NULL, 'offline',
    '{"dataset": "PaySim", "status": "placeholder metadata; train before deployment"}'::jsonb
)
ON CONFLICT (model_name, version) DO NOTHING;

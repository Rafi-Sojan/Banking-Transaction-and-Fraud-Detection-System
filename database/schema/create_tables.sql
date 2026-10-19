-- Core PostgreSQL schema for the simulated banking and fraud-detection system.
-- Run this file before constraints.sql, indexes.sql, triggers, procedures, views,
-- and seed/data.sql. All financial values use NUMERIC; never use floating point
-- for balances or transaction amounts.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS branch (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_name VARCHAR(120) NOT NULL,
    address TEXT NOT NULL,
    ifsc_code VARCHAR(20) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(160) NOT NULL,
    email VARCHAR(320) NOT NULL,
    phone VARCHAR(32),
    address TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role (
    role_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_name VARCHAR(40) NOT NULL UNIQUE,
    permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS merchant_category (
    category_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS location (
    location_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) NOT NULL,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS account (
    account_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customer(customer_id),
    branch_id BIGINT NOT NULL REFERENCES branch(branch_id),
    account_number VARCHAR(34) NOT NULL UNIQUE,
    account_type VARCHAR(30) NOT NULL DEFAULT 'checking',
    balance NUMERIC(19, 4) NOT NULL DEFAULT 0,
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS merchant (
    merchant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id BIGINT NOT NULL REFERENCES merchant_category(category_id),
    location_id BIGINT REFERENCES location(location_id),
    merchant_name VARCHAR(160) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS card (
    card_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES account(account_id),
    card_number_hash TEXT NOT NULL,
    card_type VARCHAR(30) NOT NULL DEFAULT 'debit',
    expiry_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (account_id, card_number_hash)
);

CREATE TABLE IF NOT EXISTS app_user (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT UNIQUE REFERENCES customer(customer_id),
    username VARCHAR(120) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id BIGINT NOT NULL REFERENCES role(role_id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fraud_rule (
    rule_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_name VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    threshold NUMERIC(19, 4),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    version INTEGER NOT NULL DEFAULT 1,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (rule_name, version)
);

CREATE TABLE IF NOT EXISTS ml_model (
    model_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_name VARCHAR(120) NOT NULL,
    version VARCHAR(60) NOT NULL,
    model_path TEXT NOT NULL,
    precision_score NUMERIC(8, 6),
    recall_score NUMERIC(8, 6),
    f1_score NUMERIC(8, 6),
    pr_auc_score NUMERIC(8, 6),
    roc_auc_score NUMERIC(8, 6),
    deployment_status VARCHAR(30) NOT NULL DEFAULT 'offline',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (model_name, version)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_account_id BIGINT NOT NULL REFERENCES account(account_id),
    destination_account_id BIGINT REFERENCES account(account_id),
    card_id BIGINT REFERENCES card(card_id),
    merchant_id BIGINT REFERENCES merchant(merchant_id),
    initiated_by_user_id BIGINT REFERENCES app_user(user_id),
    amount NUMERIC(19, 4) NOT NULL,
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    transaction_type VARCHAR(30) NOT NULL,
    transaction_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    idempotency_key VARCHAR(160),
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_transactions_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS fraud_alert (
    alert_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(transaction_id),
    ml_model_id BIGINT REFERENCES ml_model(model_id),
    rule_score NUMERIC(8, 6),
    ml_probability NUMERIC(8, 6),
    combined_risk_score NUMERIC(8, 6) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    alert_status VARCHAR(20) NOT NULL DEFAULT 'open',
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fraud_rule_result (
    rule_result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id BIGINT NOT NULL REFERENCES fraud_alert(alert_id) ON DELETE CASCADE,
    rule_id BIGINT NOT NULL REFERENCES fraud_rule(rule_id),
    triggered BOOLEAN NOT NULL,
    risk_contribution NUMERIC(8, 6) NOT NULL DEFAULT 0,
    reason TEXT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investigation (
    investigation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id BIGINT NOT NULL REFERENCES fraud_alert(alert_id),
    assigned_user_id BIGINT REFERENCES app_user(user_id),
    investigation_status VARCHAR(20) NOT NULL DEFAULT 'open',
    outcome VARCHAR(30),
    notes TEXT,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investigation_action (
    action_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigation(investigation_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES app_user(user_id),
    action_type VARCHAR(50) NOT NULL,
    notes TEXT,
    action_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES app_user(user_id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id BIGINT,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS transaction_status_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

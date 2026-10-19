-- Query indexes for common API, reporting, and investigation workflows.

CREATE INDEX IF NOT EXISTS idx_account_customer ON account(customer_id);
CREATE INDEX IF NOT EXISTS idx_account_branch ON account(branch_id);
CREATE INDEX IF NOT EXISTS idx_card_account ON card(account_id);
CREATE INDEX IF NOT EXISTS idx_merchant_category ON merchant(category_id);
CREATE INDEX IF NOT EXISTS idx_merchant_location ON merchant(location_id);
CREATE INDEX IF NOT EXISTS idx_app_user_role ON app_user(role_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_app_user_username_lower ON app_user(lower(username));

CREATE INDEX IF NOT EXISTS idx_transactions_source_time
    ON transactions(source_account_id, transaction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_destination_time
    ON transactions(destination_account_id, transaction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_status_time
    ON transactions(status, transaction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_card ON transactions(card_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_fraud_alert_status_risk
    ON fraud_alert(alert_status, combined_risk_score DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fraud_alert_transaction ON fraud_alert(transaction_id);
CREATE INDEX IF NOT EXISTS idx_fraud_rule_result_alert ON fraud_rule_result(alert_id);
CREATE INDEX IF NOT EXISTS idx_investigation_assignee_status
    ON investigation(assigned_user_id, investigation_status);
CREATE INDEX IF NOT EXISTS idx_investigation_action_investigation
    ON investigation_action(investigation_id, action_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_time
    ON audit_log(entity_type, entity_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_history_transaction_time
    ON transaction_status_history(transaction_id, changed_at DESC);

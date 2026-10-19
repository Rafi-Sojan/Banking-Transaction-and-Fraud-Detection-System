-- Domain and cross-column constraints. Foreign keys are declared with tables
-- in create_tables.sql so this file remains safe to run repeatedly.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_customer_status') THEN
        ALTER TABLE customer ADD CONSTRAINT chk_customer_status
            CHECK (status IN ('active', 'inactive', 'blocked', 'closed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_branch_ifsc_format') THEN
        ALTER TABLE branch ADD CONSTRAINT chk_branch_ifsc_format
            CHECK (ifsc_code = UPPER(ifsc_code));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_account_type') THEN
        ALTER TABLE account ADD CONSTRAINT chk_account_type
            CHECK (account_type IN ('checking', 'savings', 'business', 'wallet'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_account_balance') THEN
        ALTER TABLE account ADD CONSTRAINT chk_account_balance
            CHECK (balance >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_account_status') THEN
        ALTER TABLE account ADD CONSTRAINT chk_account_status
            CHECK (status IN ('active', 'frozen', 'closed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_account_currency') THEN
        ALTER TABLE account ADD CONSTRAINT chk_account_currency
            CHECK (currency_code ~ '^[A-Z]{3}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_merchant_status') THEN
        ALTER TABLE merchant ADD CONSTRAINT chk_merchant_status
            CHECK (status IN ('active', 'inactive', 'blocked'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_card_type') THEN
        ALTER TABLE card ADD CONSTRAINT chk_card_type
            CHECK (card_type IN ('debit', 'credit', 'virtual'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_card_status') THEN
        ALTER TABLE card ADD CONSTRAINT chk_card_status
            CHECK (status IN ('active', 'blocked', 'expired', 'cancelled'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_app_user_status') THEN
        ALTER TABLE app_user ADD CONSTRAINT chk_app_user_status
            CHECK (status IN ('active', 'inactive', 'locked'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_app_user_username') THEN
        ALTER TABLE app_user ADD CONSTRAINT chk_app_user_username
            CHECK (username = lower(username));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fraud_rule_version') THEN
        ALTER TABLE fraud_rule ADD CONSTRAINT chk_fraud_rule_version
            CHECK (version > 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fraud_rule_threshold') THEN
        ALTER TABLE fraud_rule ADD CONSTRAINT chk_fraud_rule_threshold
            CHECK (threshold IS NULL OR threshold >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_ml_model_metrics') THEN
        ALTER TABLE ml_model ADD CONSTRAINT chk_ml_model_metrics
            CHECK (
                (precision_score IS NULL OR precision_score BETWEEN 0 AND 1)
                AND (recall_score IS NULL OR recall_score BETWEEN 0 AND 1)
                AND (f1_score IS NULL OR f1_score BETWEEN 0 AND 1)
                AND (pr_auc_score IS NULL OR pr_auc_score BETWEEN 0 AND 1)
                AND (roc_auc_score IS NULL OR roc_auc_score BETWEEN 0 AND 1)
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_ml_model_deployment_status') THEN
        ALTER TABLE ml_model ADD CONSTRAINT chk_ml_model_deployment_status
            CHECK (deployment_status IN ('offline', 'staged', 'deployed', 'retired'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_transactions_amount') THEN
        ALTER TABLE transactions ADD CONSTRAINT chk_transactions_amount
            CHECK (amount > 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_transactions_type') THEN
        ALTER TABLE transactions ADD CONSTRAINT chk_transactions_type
            CHECK (transaction_type IN ('transfer', 'card_purchase', 'cash_withdrawal', 'deposit', 'payment', 'refund'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_transactions_status') THEN
        ALTER TABLE transactions ADD CONSTRAINT chk_transactions_status
            CHECK (status IN ('pending', 'approved', 'completed', 'declined', 'held', 'failed', 'reversed'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_transactions_accounts') THEN
        ALTER TABLE transactions ADD CONSTRAINT chk_transactions_accounts
            CHECK (destination_account_id IS NULL OR destination_account_id <> source_account_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_transactions_currency') THEN
        ALTER TABLE transactions ADD CONSTRAINT chk_transactions_currency
            CHECK (currency_code ~ '^[A-Z]{3}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fraud_alert_scores') THEN
        ALTER TABLE fraud_alert ADD CONSTRAINT chk_fraud_alert_scores
            CHECK (
                (rule_score IS NULL OR rule_score BETWEEN 0 AND 1)
                AND (ml_probability IS NULL OR ml_probability BETWEEN 0 AND 1)
                AND combined_risk_score BETWEEN 0 AND 1
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fraud_alert_risk_level') THEN
        ALTER TABLE fraud_alert ADD CONSTRAINT chk_fraud_alert_risk_level
            CHECK (risk_level IN ('low', 'medium', 'high', 'critical'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fraud_alert_status') THEN
        ALTER TABLE fraud_alert ADD CONSTRAINT chk_fraud_alert_status
            CHECK (alert_status IN ('open', 'under_review', 'confirmed', 'dismissed', 'resolved'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_fraud_rule_result_contribution') THEN
        ALTER TABLE fraud_rule_result ADD CONSTRAINT chk_fraud_rule_result_contribution
            CHECK (risk_contribution BETWEEN 0 AND 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_investigation_status') THEN
        ALTER TABLE investigation ADD CONSTRAINT chk_investigation_status
            CHECK (investigation_status IN ('open', 'in_progress', 'closed', 'escalated'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_investigation_outcome') THEN
        ALTER TABLE investigation ADD CONSTRAINT chk_investigation_outcome
            CHECK (outcome IS NULL OR outcome IN ('confirmed_fraud', 'legitimate', 'inconclusive'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_investigation_dates') THEN
        ALTER TABLE investigation ADD CONSTRAINT chk_investigation_dates
            CHECK (closed_at IS NULL OR closed_at >= opened_at);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_transaction_history_status') THEN
        ALTER TABLE transaction_status_history ADD CONSTRAINT chk_transaction_history_status
            CHECK (new_status IN ('pending', 'approved', 'completed', 'declined', 'held', 'failed', 'reversed'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_investigation_per_alert
    ON investigation(alert_id)
    WHERE investigation_status IN ('open', 'in_progress', 'escalated');

CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_email_lower
    ON customer(lower(email));

CREATE UNIQUE INDEX IF NOT EXISTS uq_deployed_model_name
    ON ml_model(model_name)
    WHERE deployment_status = 'deployed';

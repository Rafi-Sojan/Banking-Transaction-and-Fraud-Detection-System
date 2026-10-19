-- Shared timestamp and transaction-integrity triggers.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_customer_updated_at ON customer;
CREATE TRIGGER trg_customer_updated_at
BEFORE UPDATE ON customer
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_account_updated_at ON account;
CREATE TRIGGER trg_account_updated_at
BEFORE UPDATE ON account
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_app_user_updated_at ON app_user;
CREATE TRIGGER trg_app_user_updated_at
BEFORE UPDATE ON app_user
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_fraud_rule_updated_at ON fraud_rule;
CREATE TRIGGER trg_fraud_rule_updated_at
BEFORE UPDATE ON fraud_rule
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_transactions_updated_at ON transactions;
CREATE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_fraud_alert_updated_at ON fraud_alert;
CREATE TRIGGER trg_fraud_alert_updated_at
BEFORE UPDATE ON fraud_alert
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_investigation_updated_at ON investigation;
CREATE TRIGGER trg_investigation_updated_at
BEFORE UPDATE ON investigation
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION record_transaction_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' OR NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO transaction_status_history (transaction_id, old_status, new_status)
        VALUES (NEW.transaction_id, CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.status END, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_transaction_status_history ON transactions;
CREATE TRIGGER trg_transaction_status_history
AFTER INSERT OR UPDATE OF status ON transactions
FOR EACH ROW EXECUTE FUNCTION record_transaction_status_change();

CREATE OR REPLACE FUNCTION prevent_final_transaction_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('completed', 'declined', 'reversed') AND (
        NEW.source_account_id IS DISTINCT FROM OLD.source_account_id
        OR NEW.destination_account_id IS DISTINCT FROM OLD.destination_account_id
        OR NEW.card_id IS DISTINCT FROM OLD.card_id
        OR NEW.merchant_id IS DISTINCT FROM OLD.merchant_id
        OR NEW.amount IS DISTINCT FROM OLD.amount
        OR NEW.currency_code IS DISTINCT FROM OLD.currency_code
        OR NEW.transaction_type IS DISTINCT FROM OLD.transaction_type
        OR NEW.transaction_timestamp IS DISTINCT FROM OLD.transaction_timestamp
    ) THEN
        RAISE EXCEPTION 'Final transaction % cannot have its financial fields changed', OLD.transaction_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_final_transaction_mutation ON transactions;
CREATE TRIGGER trg_prevent_final_transaction_mutation
BEFORE UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION prevent_final_transaction_mutation();

-- Fraud-alert integrity triggers.

CREATE OR REPLACE FUNCTION prevent_confirmed_alert_reopen()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.alert_status = 'confirmed' AND NEW.alert_status IN ('open', 'under_review', 'dismissed') THEN
        RAISE EXCEPTION 'Confirmed fraud alert % cannot be reopened or dismissed', OLD.alert_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_confirmed_alert_reopen ON fraud_alert;
CREATE TRIGGER trg_prevent_confirmed_alert_reopen
BEFORE UPDATE OF alert_status ON fraud_alert
FOR EACH ROW EXECUTE FUNCTION prevent_confirmed_alert_reopen();

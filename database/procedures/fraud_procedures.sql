-- Database helpers for fraud scoring and investigation workflow.

CREATE OR REPLACE FUNCTION create_fraud_alert(
    p_transaction_id BIGINT,
    p_rule_score NUMERIC(8, 6),
    p_ml_probability NUMERIC(8, 6),
    p_combined_risk_score NUMERIC(8, 6),
    p_risk_level VARCHAR(20),
    p_ml_model_id BIGINT DEFAULT NULL,
    p_reasons JSONB DEFAULT '[]'::jsonb
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_alert_id BIGINT;
BEGIN
    INSERT INTO fraud_alert (
        transaction_id,
        ml_model_id,
        rule_score,
        ml_probability,
        combined_risk_score,
        risk_level,
        reasons
    ) VALUES (
        p_transaction_id,
        p_ml_model_id,
        p_rule_score,
        p_ml_probability,
        p_combined_risk_score,
        p_risk_level,
        COALESCE(p_reasons, '[]'::jsonb)
    )
    RETURNING alert_id INTO v_alert_id;

    UPDATE transactions
    SET status = CASE
        WHEN p_risk_level IN ('high', 'critical') THEN 'held'
        ELSE status
    END
    WHERE transaction_id = p_transaction_id
      AND status = 'pending';

    RETURN v_alert_id;
END;
$$;

CREATE OR REPLACE FUNCTION close_investigation(
    p_investigation_id BIGINT,
    p_user_id BIGINT,
    p_outcome VARCHAR(30),
    p_notes TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_outcome NOT IN ('confirmed_fraud', 'legitimate', 'inconclusive') THEN
        RAISE EXCEPTION 'Unsupported investigation outcome: %', p_outcome;
    END IF;

    UPDATE investigation
    SET investigation_status = 'closed',
        outcome = p_outcome,
        notes = p_notes,
        closed_at = CURRENT_TIMESTAMP
    WHERE investigation_id = p_investigation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Investigation % does not exist', p_investigation_id;
    END IF;

    INSERT INTO investigation_action (investigation_id, user_id, action_type, notes)
    VALUES (p_investigation_id, p_user_id, 'closed', p_notes);

    UPDATE fraud_alert
    SET alert_status = CASE WHEN p_outcome = 'confirmed_fraud' THEN 'confirmed' ELSE 'resolved' END
    WHERE alert_id = (SELECT alert_id FROM investigation WHERE investigation_id = p_investigation_id);
END;
$$;

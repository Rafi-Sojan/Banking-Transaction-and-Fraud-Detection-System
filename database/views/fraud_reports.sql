CREATE OR REPLACE VIEW fraud_reports AS
SELECT
    fa.alert_id,
    fa.transaction_id,
    fa.rule_score,
    fa.ml_probability,
    fa.combined_risk_score,
    fa.risk_level,
    fa.alert_status,
    fa.reasons,
    fa.created_at AS alert_created_at,
    t.transaction_timestamp,
    t.amount,
    t.currency_code,
    t.transaction_type,
    t.source_account_id,
    source_account.account_number AS source_account_number,
    t.merchant_id,
    m.merchant_name,
    latest_investigation.investigation_id,
    latest_investigation.investigation_status,
    latest_investigation.outcome,
    latest_investigation.assigned_user_id
FROM fraud_alert fa
JOIN transactions t ON t.transaction_id = fa.transaction_id
JOIN account source_account ON source_account.account_id = t.source_account_id
LEFT JOIN merchant m ON m.merchant_id = t.merchant_id
LEFT JOIN LATERAL (
    SELECT i.investigation_id, i.investigation_status, i.outcome, i.assigned_user_id
    FROM investigation i
    WHERE i.alert_id = fa.alert_id
    ORDER BY i.opened_at DESC, i.investigation_id DESC
    LIMIT 1
) latest_investigation ON TRUE;

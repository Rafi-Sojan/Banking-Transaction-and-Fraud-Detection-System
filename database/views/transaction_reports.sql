CREATE OR REPLACE VIEW transaction_reports AS
SELECT
    t.transaction_id,
    t.transaction_timestamp,
    t.transaction_type,
    t.status,
    t.amount,
    t.currency_code,
    t.source_account_id,
    source_account.account_number AS source_account_number,
    t.destination_account_id,
    destination_account.account_number AS destination_account_number,
    t.merchant_id,
    m.merchant_name,
    t.idempotency_key,
    latest_alert.alert_id,
    latest_alert.combined_risk_score,
    latest_alert.risk_level,
    latest_alert.alert_status
FROM transactions t
JOIN account source_account ON source_account.account_id = t.source_account_id
LEFT JOIN account destination_account ON destination_account.account_id = t.destination_account_id
LEFT JOIN merchant m ON m.merchant_id = t.merchant_id
LEFT JOIN LATERAL (
    SELECT fa.alert_id, fa.combined_risk_score, fa.risk_level, fa.alert_status
    FROM fraud_alert fa
    WHERE fa.transaction_id = t.transaction_id
    ORDER BY fa.created_at DESC, fa.alert_id DESC
    LIMIT 1
) latest_alert ON TRUE;

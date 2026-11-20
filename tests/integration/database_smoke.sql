-- PostgreSQL integration smoke tests.
-- Run with psql against a database initialized by database/setup.sql.

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_table_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
          'branch', 'customer', 'role', 'merchant_category', 'location',
          'account', 'merchant', 'card', 'app_user', 'fraud_rule', 'ml_model',
          'transactions', 'fraud_alert', 'fraud_rule_result', 'investigation',
          'investigation_action', 'audit_log', 'transaction_status_history'
      );

    IF v_table_count <> 18 THEN
        RAISE EXCEPTION 'Expected 18 core tables, found %', v_table_count;
    END IF;

    IF (SELECT COUNT(*) FROM customer) < 3 THEN
        RAISE EXCEPTION 'Expected seeded customers';
    END IF;

    IF (SELECT COUNT(*) FROM account) < 2 THEN
        RAISE EXCEPTION 'Expected seeded accounts';
    END IF;
END
$$;

DO $$
DECLARE
    v_first_transaction_id BIGINT;
    v_second_transaction_id BIGINT;
    v_transaction_count INTEGER;
    v_source_before NUMERIC(19, 4);
    v_destination_before NUMERIC(19, 4);
    v_source_after NUMERIC(19, 4);
    v_destination_after NUMERIC(19, 4);
BEGIN
    SELECT balance INTO v_source_before
    FROM account WHERE account_number = '100000000001';
    SELECT balance INTO v_destination_before
    FROM account WHERE account_number = '100000000002';

    v_first_transaction_id := process_transfer(
        (SELECT account_id FROM account WHERE account_number = '100000000001'),
        (SELECT account_id FROM account WHERE account_number = '100000000002'),
        10.00,
        'USD',
        'database-integration-test-transfer',
        NULL,
        'Integration test transfer'
    );

    v_second_transaction_id := process_transfer(
        (SELECT account_id FROM account WHERE account_number = '100000000001'),
        (SELECT account_id FROM account WHERE account_number = '100000000002'),
        10.00,
        'USD',
        'database-integration-test-transfer',
        NULL,
        'Integration test transfer'
    );

    IF v_first_transaction_id <> v_second_transaction_id THEN
        RAISE EXCEPTION 'Idempotent retry returned a different transaction ID';
    END IF;

    SELECT COUNT(*) INTO v_transaction_count
    FROM transactions
    WHERE idempotency_key = 'database-integration-test-transfer';

    IF v_transaction_count <> 1 THEN
        RAISE EXCEPTION 'Expected one idempotent transaction, found %', v_transaction_count;
    END IF;

    SELECT balance INTO v_source_after
    FROM account WHERE account_number = '100000000001';
    SELECT balance INTO v_destination_after
    FROM account WHERE account_number = '100000000002';

    IF v_source_after <> v_source_before - 10.00
       OR v_destination_after <> v_destination_before + 10.00 THEN
        RAISE EXCEPTION 'Atomic transfer did not update both balances correctly';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM transaction_status_history
        WHERE transaction_id = v_first_transaction_id
          AND new_status = 'completed'
    ) THEN
        RAISE EXCEPTION 'Transaction status history was not recorded';
    END IF;
END
$$;

DO $$
DECLARE
    v_rejected BOOLEAN := FALSE;
BEGIN
    BEGIN
        INSERT INTO transactions (source_account_id, amount, transaction_type)
        VALUES (
            (SELECT account_id FROM account WHERE account_number = '100000000001'),
            -1,
            'transfer'
        );
    EXCEPTION WHEN check_violation THEN
        v_rejected := TRUE;
    END;

    IF NOT v_rejected THEN
        RAISE EXCEPTION 'Negative transaction amount was accepted';
    END IF;
END
$$;

DO $$
DECLARE
    v_transaction_id BIGINT;
    v_alert_id BIGINT;
    v_status VARCHAR(20);
BEGIN
    INSERT INTO transactions (source_account_id, amount, transaction_type, status)
    VALUES (
        (SELECT account_id FROM account WHERE account_number = '100000000001'),
        25.00,
        'card_purchase',
        'pending'
    )
    RETURNING transaction_id INTO v_transaction_id;

    v_alert_id := create_fraud_alert(
        v_transaction_id,
        0.90,
        0.95,
        0.97,
        'high',
        NULL,
        '[{"code": "integration_test", "reason": "test alert"}]'::jsonb
    );

    SELECT alert_status INTO v_status FROM fraud_alert WHERE alert_id = v_alert_id;
    IF v_status <> 'open' THEN
        RAISE EXCEPTION 'New fraud alert should start open, found %', v_status;
    END IF;

    SELECT status INTO v_status FROM transactions WHERE transaction_id = v_transaction_id;
    IF v_status <> 'held' THEN
        RAISE EXCEPTION 'High-risk pending transaction should be held, found %', v_status;
    END IF;
END
$$;

DO $$
DECLARE
    v_held_id BIGINT;
    v_declined_id BIGINT;
    v_reversal_id BIGINT;
    v_status VARCHAR(20);
    v_source_before NUMERIC(19, 4);
    v_destination_before NUMERIC(19, 4);
    v_source_after NUMERIC(19, 4);
    v_destination_after NUMERIC(19, 4);
BEGIN
    SELECT balance INTO v_source_before FROM account WHERE account_number = '100000000001';
    SELECT balance INTO v_destination_before FROM account WHERE account_number = '100000000002';

    INSERT INTO transactions (source_account_id, destination_account_id, amount, currency_code, transaction_type, status)
    VALUES (
        (SELECT account_id FROM account WHERE account_number = '100000000001'),
        (SELECT account_id FROM account WHERE account_number = '100000000002'),
        15.00, 'USD', 'transfer', 'held'
    ) RETURNING transaction_id INTO v_held_id;

    PERFORM approve_held_transfer(v_held_id, NULL::BIGINT);
    SELECT status INTO STRICT v_status FROM transactions WHERE transaction_id = v_held_id;
    IF v_status <> 'completed' THEN
        RAISE EXCEPTION 'Held approval did not complete transaction';
    END IF;

    v_reversal_id := reverse_completed_transfer(v_held_id, NULL::BIGINT, 'database-integration-reversal', 'smoke reversal');
    IF NOT EXISTS (SELECT 1 FROM transactions WHERE transaction_id = v_reversal_id AND status = 'completed') THEN
        RAISE EXCEPTION 'Reversal transaction was not completed';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM transactions WHERE transaction_id = v_held_id AND status = 'reversed') THEN
        RAISE EXCEPTION 'Original transaction was not marked reversed';
    END IF;

    INSERT INTO transactions (source_account_id, destination_account_id, amount, currency_code, transaction_type, status)
    VALUES (
        (SELECT account_id FROM account WHERE account_number = '100000000001'),
        (SELECT account_id FROM account WHERE account_number = '100000000002'),
        15.00, 'USD', 'transfer', 'held'
    ) RETURNING transaction_id INTO v_declined_id;
    PERFORM decline_held_transfer(v_declined_id, NULL::BIGINT, 'smoke decline');
    IF NOT EXISTS (SELECT 1 FROM transactions WHERE transaction_id = v_declined_id AND status = 'declined') THEN
        RAISE EXCEPTION 'Held decline did not update transaction';
    END IF;

    SELECT balance INTO v_source_after FROM account WHERE account_number = '100000000001';
    SELECT balance INTO v_destination_after FROM account WHERE account_number = '100000000002';
    IF v_source_after <> v_source_before OR v_destination_after <> v_destination_before THEN
        RAISE EXCEPTION 'Approve/reversal did not restore account balances';
    END IF;
END
$$;

ROLLBACK;


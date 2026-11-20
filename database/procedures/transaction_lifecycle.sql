-- Controlled lifecycle operations for held, declined, and reversed transfers.

CREATE OR REPLACE FUNCTION approve_held_transfer(
    p_transaction_id BIGINT,
    p_user_id BIGINT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction transactions%ROWTYPE;
    v_source_balance NUMERIC(19, 4);
BEGIN
    SELECT * INTO v_transaction
    FROM transactions
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction % does not exist', p_transaction_id;
    END IF;
    IF v_transaction.status <> 'held' THEN
        RAISE EXCEPTION 'Only held transactions can be approved';
    END IF;
    IF v_transaction.destination_account_id IS NULL THEN
        RAISE EXCEPTION 'Held transaction % has no destination account', p_transaction_id;
    END IF;

    PERFORM 1
    FROM account
    WHERE account_id IN (v_transaction.source_account_id, v_transaction.destination_account_id)
    ORDER BY account_id
    FOR UPDATE;

    IF (SELECT COUNT(*) FROM account WHERE account_id IN (v_transaction.source_account_id, v_transaction.destination_account_id)) <> 2 THEN
        RAISE EXCEPTION 'Both transaction accounts must exist';
    END IF;
    IF EXISTS (
        SELECT 1 FROM account
        WHERE account_id IN (v_transaction.source_account_id, v_transaction.destination_account_id)
          AND (status <> 'active' OR currency_code <> v_transaction.currency_code)
    ) THEN
        RAISE EXCEPTION 'Both transaction accounts must be active and use the transaction currency';
    END IF;

    SELECT balance INTO v_source_balance
    FROM account WHERE account_id = v_transaction.source_account_id;
    IF v_source_balance < v_transaction.amount THEN
        RAISE EXCEPTION 'Insufficient funds in source account';
    END IF;

    UPDATE account SET balance = balance - v_transaction.amount
    WHERE account_id = v_transaction.source_account_id;
    UPDATE account SET balance = balance + v_transaction.amount
    WHERE account_id = v_transaction.destination_account_id;
    UPDATE transactions SET status = 'completed', initiated_by_user_id = COALESCE(p_user_id, initiated_by_user_id)
    WHERE transaction_id = p_transaction_id;
    RETURN p_transaction_id;
END;
$$;

CREATE OR REPLACE FUNCTION decline_held_transfer(
    p_transaction_id BIGINT,
    p_user_id BIGINT DEFAULT NULL,
    p_reason TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE transactions
    SET status = 'declined',
        initiated_by_user_id = COALESCE(p_user_id, initiated_by_user_id),
        description = COALESCE(p_reason, description)
    WHERE transaction_id = p_transaction_id AND status = 'held';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Only an existing held transaction can be declined';
    END IF;
    RETURN p_transaction_id;
END;
$$;

CREATE OR REPLACE FUNCTION reverse_completed_transfer(
    p_transaction_id BIGINT,
    p_user_id BIGINT DEFAULT NULL,
    p_idempotency_key VARCHAR(160) DEFAULT NULL,
    p_reason TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction transactions%ROWTYPE;
    v_reversal_id BIGINT;
    v_source_balance NUMERIC(19, 4);
BEGIN
    IF p_idempotency_key IS NOT NULL THEN
        SELECT transaction_id INTO v_reversal_id
        FROM transactions WHERE idempotency_key = p_idempotency_key;
        IF FOUND THEN
            IF NOT EXISTS (
                SELECT 1 FROM transactions
                WHERE transaction_id = v_reversal_id
                  AND metadata->>'reverses_transaction_id' = p_transaction_id::TEXT
            ) THEN
                RAISE EXCEPTION 'Reversal idempotency key % was already used for another transaction', p_idempotency_key;
            END IF;
            RETURN v_reversal_id;
        END IF;
    END IF;

    SELECT * INTO v_transaction
    FROM transactions
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction % does not exist', p_transaction_id;
    END IF;
    IF v_transaction.status <> 'completed' OR v_transaction.transaction_type <> 'transfer' THEN
        RAISE EXCEPTION 'Only completed transfers can be reversed';
    END IF;
    IF v_transaction.destination_account_id IS NULL THEN
        RAISE EXCEPTION 'Transaction % has no destination account', p_transaction_id;
    END IF;

    PERFORM 1
    FROM account
    WHERE account_id IN (v_transaction.source_account_id, v_transaction.destination_account_id)
    ORDER BY account_id
    FOR UPDATE;
    IF (SELECT COUNT(*) FROM account WHERE account_id IN (v_transaction.source_account_id, v_transaction.destination_account_id)) <> 2 THEN
        RAISE EXCEPTION 'Both transaction accounts must exist';
    END IF;
    IF EXISTS (
        SELECT 1 FROM account
        WHERE account_id IN (v_transaction.source_account_id, v_transaction.destination_account_id)
          AND (status <> 'active' OR currency_code <> v_transaction.currency_code)
    ) THEN
        RAISE EXCEPTION 'Both transaction accounts must be active and use the transaction currency';
    END IF;
    SELECT balance INTO v_source_balance
    FROM account WHERE account_id = v_transaction.destination_account_id;
    IF v_source_balance < v_transaction.amount THEN
        RAISE EXCEPTION 'Insufficient funds in destination account for reversal';
    END IF;

    INSERT INTO transactions (
        source_account_id, destination_account_id, initiated_by_user_id,
        amount, currency_code, transaction_type, status, idempotency_key,
        description, metadata
    ) VALUES (
        v_transaction.destination_account_id, v_transaction.source_account_id,
        p_user_id, v_transaction.amount, v_transaction.currency_code, 'refund',
        'completed', p_idempotency_key, COALESCE(p_reason, 'Reversal'),
        jsonb_build_object('reverses_transaction_id', p_transaction_id)
    ) RETURNING transaction_id INTO v_reversal_id;

    UPDATE account SET balance = balance - v_transaction.amount
    WHERE account_id = v_transaction.destination_account_id;
    UPDATE account SET balance = balance + v_transaction.amount
    WHERE account_id = v_transaction.source_account_id;
    UPDATE transactions SET status = 'reversed' WHERE transaction_id = p_transaction_id;
    RETURN v_reversal_id;
END;
$$;

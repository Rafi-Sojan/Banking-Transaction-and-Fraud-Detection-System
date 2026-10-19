-- Atomic simulated transfer workflow.
-- The API should call this function instead of updating balances directly.

CREATE OR REPLACE FUNCTION process_transfer(
    p_source_account_id BIGINT,
    p_destination_account_id BIGINT,
    p_amount NUMERIC(19, 4),
    p_currency_code CHAR(3) DEFAULT 'USD',
    p_idempotency_key VARCHAR(160) DEFAULT NULL,
    p_initiated_by_user_id BIGINT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id BIGINT;
    v_source_balance NUMERIC(19, 4);
    v_existing_source BIGINT;
    v_existing_destination BIGINT;
    v_existing_amount NUMERIC(19, 4);
BEGIN
    IF p_source_account_id = p_destination_account_id THEN
        RAISE EXCEPTION 'Source and destination accounts must be different';
    END IF;
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Transfer amount must be greater than zero';
    END IF;
    IF p_currency_code IS NULL OR p_currency_code !~ '^[A-Z]{3}$' THEN
        RAISE EXCEPTION 'Currency code must contain three uppercase letters';
    END IF;

    IF p_idempotency_key IS NOT NULL THEN
        SELECT transaction_id, source_account_id, destination_account_id, amount
        INTO v_transaction_id, v_existing_source, v_existing_destination, v_existing_amount
        FROM transactions
        WHERE idempotency_key = p_idempotency_key;

        IF FOUND THEN
            IF v_existing_source <> p_source_account_id
               OR v_existing_destination <> p_destination_account_id
               OR v_existing_amount <> p_amount THEN
                RAISE EXCEPTION 'Idempotency key % was already used with different transfer details', p_idempotency_key;
            END IF;
            RETURN v_transaction_id;
        END IF;
    END IF;

    -- Lock accounts in a stable order to reduce deadlock risk for concurrent transfers.
    PERFORM 1
    FROM account
    WHERE account_id IN (p_source_account_id, p_destination_account_id)
    ORDER BY account_id
    FOR UPDATE;

    IF (SELECT COUNT(*) FROM account WHERE account_id IN (p_source_account_id, p_destination_account_id)) <> 2 THEN
        RAISE EXCEPTION 'Both source and destination accounts must exist';
    END IF;

    IF EXISTS (SELECT 1 FROM account WHERE account_id IN (p_source_account_id, p_destination_account_id) AND status <> 'active') THEN
        RAISE EXCEPTION 'Both accounts must be active';
    END IF;

    IF EXISTS (SELECT 1 FROM account WHERE account_id IN (p_source_account_id, p_destination_account_id) AND currency_code <> p_currency_code) THEN
        RAISE EXCEPTION 'Both accounts must use currency %', p_currency_code;
    END IF;

    SELECT balance INTO v_source_balance
    FROM account
    WHERE account_id = p_source_account_id;

    IF v_source_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds in source account';
    END IF;

    INSERT INTO transactions (
        source_account_id,
        destination_account_id,
        amount,
        currency_code,
        transaction_type,
        status,
        idempotency_key,
        initiated_by_user_id,
        description,
        metadata
    ) VALUES (
        p_source_account_id,
        p_destination_account_id,
        p_amount,
        p_currency_code,
        'transfer',
        'completed',
        p_idempotency_key,
        p_initiated_by_user_id,
        p_description,
        COALESCE(p_metadata, '{}'::jsonb)
    ) RETURNING transaction_id INTO v_transaction_id;

    UPDATE account
    SET balance = balance - p_amount
    WHERE account_id = p_source_account_id;

    UPDATE account
    SET balance = balance + p_amount
    WHERE account_id = p_destination_account_id;

    RETURN v_transaction_id;
END;
$$;

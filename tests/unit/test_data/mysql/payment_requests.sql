INSERT INTO payment_requests (
    payment_request_id,
    store_id,
    user_id,
    store_wallet_address,
    user_wallet_address,
    amount,
    token_symbol,
    chain_id,
    status,
    transaction_hash,
    expires_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    401,
    101,
    101,
    '0x1111111111111111111111111111111111111111',
    '0x1111111111111111111111111111111111111111',
    1000.500000,
    'JPYC',
    11155111,
    'requested',
    NULL,
    '2026-04-13 12:00:00',
    '2026-04-13 11:00:00',
    '2026-04-13 11:00:00',
    NULL
);

INSERT INTO payment_requests (
    payment_request_id,
    store_id,
    user_id,
    store_wallet_address,
    user_wallet_address,
    amount,
    token_symbol,
    chain_id,
    status,
    transaction_hash,
    expires_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    402,
    104,
    102,
    '0x4444444444444444444444444444444444444444',
    '0x4444444444444444444444444444444444444444',
    250.000000,
    'JPYC',
    11155111,
    'paid',
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    '2026-04-14 12:00:00',
    '2026-04-14 11:00:00',
    '2026-04-14 11:30:00',
    NULL
);

INSERT INTO payment_requests (
    payment_request_id,
    store_id,
    user_id,
    store_wallet_address,
    user_wallet_address,
    amount,
    token_symbol,
    chain_id,
    status,
    transaction_hash,
    expires_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    403,
    102,
    110,
    '0x4444444444444444444444444444444444444444',
    '0x5555555555555555555555555555555555555555',
    500.000000,
    'JPYC',
    11155111,
    'tx_failed',
    NULL,
    '2026-04-15 12:00:00',
    '2026-04-15 11:00:00',
    '2026-04-15 11:30:00',
    '2026-04-16 00:00:00'
);

-- トランザクション検証テスト専用データ
INSERT INTO payment_requests (
    payment_request_id,
    store_id,
    user_id,
    store_wallet_address,
    user_wallet_address,
    amount,
    token_symbol,
    chain_id,
    status,
    transaction_hash,
    expires_at,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (404, 104, 102, '0x4444444444444444444444444444444444444444', '0x4444444444444444444444444444444444444444', 250.000000, 'JPYC', 11155111, 'paid', '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '2026-04-14 12:00:00', '2026-04-14 11:00:00', '2026-04-14 11:30:00', NULL),
    (405, 104, 102, '0x4444444444444444444444444444444444444444', '0x4444444444444444444444444444444444444444', 250.000000, 'JPYC', 11155111, 'paid', '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', '2026-04-14 12:00:00', '2026-04-14 11:00:00', '2026-04-14 11:30:00', NULL);

-- fixture: face_checkout_payment
-- 移行前に送信済みの個別決済。
INSERT INTO payment_requests (
    payment_request_id, checkout_id, idempotency_key_hash, store_id, user_id,
    store_wallet_address, user_wallet_address, amount, token_symbol, chain_id,
    status, checkout_transaction_hash, expires_at
) VALUES (
    916021, 914021, UNHEX(SHA2('verify-dev', 256)), 9201, 107,
    '0x1111111111111111111111111111111111111111', '0x6666666666666666666666666666666666666666',
    100.125000, 'JPYC', 11155111, 'submitted', CONCAT('0x', REPEAT('12', 32)), '2026-11-22 12:00:00'
);

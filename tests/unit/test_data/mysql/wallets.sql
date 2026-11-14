-- テスト用データ
INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    301,
    '0x1111111111111111111111111111111111111111',
    'ETH',
    'sepolia',
    'JPYC',
    11155111,
    NULL,
    1,
    '2024-01-10 12:00:00',
    '2024-01-01 09:00:00',
    '2024-01-11 10:30:00',
    NULL
);

INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    302,
    '0x2222222222222222222222222222222222222222',
    'POLYGON',
    'amoy',
    'USDC',
    80002,
    NULL,
    0,
    NULL,
    '2024-02-01 08:00:00',
    '2024-02-05 18:45:00',
    NULL
);

INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    303,
    '0x3333333333333333333333333333333333333333',
    'ETH',
    'sepolia',
    'JPYC',
    11155111,
    NULL,
    1,
    '2024-03-01 00:00:00',
    '2024-03-01 00:00:00',
    '2024-03-02 00:00:00',
    '2024-03-03 00:00:00'
);

INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    304,
    '0x4444444444444444444444444444444444444444',
    'ETH',
    'sepolia',
    'JPYC',
    11155111,
    NULL,
    1,
    '2024-04-01 00:00:00',
    '2024-04-01 00:00:00',
    '2024-04-02 00:00:00',
    NULL
);

INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    305,
    '0x5555555555555555555555555555555555555555',
    'ETH',
    'sepolia',
    'JPYC',
    11155111,
    NULL,
    1,
    '2024-05-01 00:00:00',
    '2024-05-01 00:00:00',
    '2024-05-02 00:00:00',
    NULL
);

INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    306,
    '0x6666666666666666666666666666666666666666',
    'ETH',
    'sepolia',
    'JPYC',
    11155111,
    NULL,
    1,
    '2024-06-01 00:00:00',
    '2024-06-01 00:00:00',
    '2024-06-02 00:00:00',
    NULL
);

-- 更新・削除系テスト専用データ
INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    is_permitted,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (311, '0x3110000000000000000000000000000000000000', 'ETH', 'sepolia', 'JPYC', 11155111, NULL, TRUE, TRUE, '2024-07-01 00:00:00', '2024-07-01 00:00:00', '2024-07-01 00:00:00', NULL),
    (312, '0x3120000000000000000000000000000000000000', 'ETH', 'sepolia', 'JPYC', 11155111, NULL, TRUE, TRUE, '2024-07-02 00:00:00', '2024-07-02 00:00:00', '2024-07-02 00:00:00', NULL),
    (313, '0x3130000000000000000000000000000000000000', 'ETH', 'sepolia', 'JPYC', 11155111, NULL, TRUE, TRUE, '2024-07-03 00:00:00', '2024-07-03 00:00:00', '2024-07-03 00:00:00', NULL),
    (314, '0x3140000000000000000000000000000000000000', 'ETH', 'sepolia', 'JPYC', 11155111, NULL, TRUE, FALSE, '2024-07-04 00:00:00', '2024-07-04 00:00:00', '2024-07-04 00:00:00', NULL),
    (315, '0x3150000000000000000000000000000000000000', 'ETH', 'sepolia', 'JPYC', 11155111, NULL, TRUE, TRUE, '2024-07-05 00:00:00', '2024-07-05 00:00:00', '2024-07-05 00:00:00', NULL);

-- API動作確認用データ
INSERT INTO wallets (
    wallet_id,
    wallet_address,
    chain_type,
    network_name,
    token_symbol,
    chain_id,
    wallet_name,
    is_active,
    is_permitted,
    verified_at,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    9001,
    '0x9001000000000000000000000000000000000001',
    'ethereum',
    'sepolia',
    'JPYC',
    11155111,
    'API Demo Store Wallet',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
);
